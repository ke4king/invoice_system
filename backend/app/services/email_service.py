import imaplib
import email
import re
import requests
from email.header import decode_header
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlparse
import base64
import os
import tempfile
import logging
import traceback

from app.core.config import settings
from app.models.email_config import EmailConfig
from app.models.invoice import Invoice
from app.services.invoice_service import InvoiceService
from app.services.email_list_service import EmailListService
from app.services.logging_service import logging_service
from sqlalchemy.orm import Session
from sqlalchemy import and_

logger = logging.getLogger(__name__)


class EmailService:
    """邮箱服务类"""
    
    def __init__(self, db: Session):
        self.db = db
        self.invoice_service = InvoiceService(db)
        self.email_list_service = EmailListService(db)
        
    def encrypt_password(self, password: str) -> str:
        """加密密码（改进：若提供密钥则使用AES-GCM，否则回退Base64）"""
        key = settings.EMAIL_ENCRYPTION_KEY
        if key and len(key) in (16, 24, 32):
            try:
                from Crypto.Cipher import AES  # pycryptodome
                from Crypto.Random import get_random_bytes
                key_bytes = key.encode()
                iv = get_random_bytes(12)
                cipher = AES.new(key_bytes, AES.MODE_GCM, nonce=iv)
                ciphertext, tag = cipher.encrypt_and_digest(password.encode())
                blob = base64.b64encode(iv + tag + ciphertext).decode()
                return f"aesgcm:{blob}"
            except Exception:
                pass
        # fallback
        return f"b64:{base64.b64encode(password.encode()).decode()}"
    
    def decrypt_password(self, encrypted_password: str) -> str:
        """解密密码（支持AES-GCM与Base64回退）"""
        try:
            if encrypted_password.startswith("aesgcm:"):
                blob = base64.b64decode(encrypted_password.split(":", 1)[1])
                key = settings.EMAIL_ENCRYPTION_KEY
                if not key or len(key) not in (16, 24, 32):
                    return encrypted_password  # 无法解密，返回原始
                from Crypto.Cipher import AES
                key_bytes = key.encode()
                iv, tag, ciphertext = blob[:12], blob[12:28], blob[28:]
                cipher = AES.new(key_bytes, AES.MODE_GCM, nonce=iv)
                plaintext = cipher.decrypt_and_verify(ciphertext, tag)
                return plaintext.decode()
            if encrypted_password.startswith("b64:"):
                return base64.b64decode(encrypted_password.split(":", 1)[1]).decode()
            # 兼容旧格式（纯b64或明文）
            try:
                return base64.b64decode(encrypted_password.encode()).decode()
            except Exception:
                return encrypted_password
        except Exception:
            return encrypted_password
    
    def create_email_config(
        self, 
        user_id: int, 
        email_address: str, 
        imap_server: str, 
        imap_port: int,
        username: str, 
        password: str,
        scan_days: int = 7
    ) -> EmailConfig:
        """创建邮箱配置"""
        encrypted_password = self.encrypt_password(password)
        
        # 检查是否已存在配置
        existing_config = self.db.query(EmailConfig).filter(
            EmailConfig.user_id == user_id,
            EmailConfig.email_address == email_address
        ).first()
        
        if existing_config:
            # 更新现有配置
            existing_config.imap_server = imap_server
            existing_config.imap_port = imap_port
            existing_config.username = username
            existing_config.password_encrypted = encrypted_password
            existing_config.scan_days = scan_days
            existing_config.is_active = True
            self.db.commit()
            return existing_config
        else:
            # 创建新配置
            config = EmailConfig(
                user_id=user_id,
                email_address=email_address,
                imap_server=imap_server,
                imap_port=imap_port,
                username=username,
                password_encrypted=encrypted_password,
                scan_days=scan_days,
                is_active=True
            )
            self.db.add(config)
            self.db.commit()
            self.db.refresh(config)
            return config
    
    def test_email_connection(self, config: EmailConfig) -> bool:
        """测试邮箱连接"""
        try:
            password = self.decrypt_password(config.password_encrypted)
            
            # 连接IMAP服务器
            mail = imaplib.IMAP4_SSL(config.imap_server, config.imap_port)
            mail.login(config.username, password)
            status_select, mailbox_data = mail.select('inbox')
            # 读取 UIDVALIDITY 以判断 UID 是否可延续
            mailbox_status, mailbox_info = mail.status('inbox', '(UIDVALIDITY)')
            current_uid_validity = None
            try:
                if mailbox_status == 'OK' and mailbox_info and mailbox_info[0]:
                    import re as _re
                    m = _re.search(rb'UIDVALIDITY\s+(\d+)', mailbox_info[0])
                    if m:
                        current_uid_validity = int(m.group(1))
            except Exception:
                current_uid_validity = None
            mail.close()
            mail.logout()
            
            return True
        except Exception as e:
            logger.error(f"邮箱连接测试失败: {str(e)}")
            return False
    
    def scan_emails(self, config: EmailConfig, days: int = 7, with_stats: bool = False) -> List[Dict]:
        """扫描邮箱中的发票"""
        scan_start_time = datetime.now()
        total_emails = 0
        processed_emails = 0
        found_invoices = 0
        errors = []
        
        try:
            # 记录扫描开始
            logging_service.log_email_event(
                db=self.db,
                event_type="scan_started",
                message=f"开始扫描邮箱: {config.email_address}",
                user_id=config.user_id,
                details={
                    "email_address": config.email_address,
                    "scan_days": days,
                    "start_time": scan_start_time.isoformat()
                }
            )
            
            password = self.decrypt_password(config.password_encrypted)
            results = []
            
            # 连接IMAP服务器
            mail = imaplib.IMAP4_SSL(config.imap_server, config.imap_port)
            login_time = datetime.now()
            mail.login(config.username, password)
            status_select, _ = mail.select('inbox')
            # 读取 UIDVALIDITY
            current_uid_validity = None
            try:
                mailbox_status, mailbox_info = mail.status('inbox', '(UIDVALIDITY)')
                if mailbox_status == 'OK' and mailbox_info and mailbox_info[0]:
                    import re as _re
                    m = _re.search(rb'UIDVALIDITY\s+(\d+)', mailbox_info[0])
                    if m:
                        current_uid_validity = int(m.group(1))
            except Exception:
                current_uid_validity = None
            
            # 降噪：登录成功不再单条记录，仅计入完成统计
            
            # 始终使用基于 UID 的扫描（首次全量 ALL，之后增量 from last_seen_uid+1）
            email_ids = []
            try:
                # 若 UIDVALIDITY 改变，重置 last_seen_uid 并更新 uid_validity
                if current_uid_validity and getattr(config, 'uid_validity', None) and config.uid_validity != current_uid_validity:
                    config.last_seen_uid = None
                if current_uid_validity and getattr(config, 'uid_validity', None) != current_uid_validity:
                    config.uid_validity = current_uid_validity

                if getattr(config, 'last_seen_uid', None):
                    # 增量扫描：抓取 last_seen_uid 之后的所有 UID
                    status, messages = mail.uid('search', None, f'(UID {config.last_seen_uid + 1}:*)')
                else:
                    # 首次全量：ALL（可能很大）
                    status, messages = mail.uid('search', None, 'ALL')

                if status == 'OK' and messages and messages[0]:
                    email_ids = messages[0].split()
                
                if email_ids:
                    total_emails = len(email_ids)
            except Exception as e:
                errors.append(f"UID 搜索失败: {str(e)}")
            
            # 降噪：中间态信息不再单条记录，仅计入完成统计
            
            if email_ids:
                # 仅使用 UID FETCH 抓取
                use_uid = True

                max_uid_seen = config.last_seen_uid or 0
                batch_size = 50
                ids_to_process = email_ids  # 按需求收集所有邮件，不再限制 200 封
                for idx, eid in enumerate(ids_to_process):
                    try:
                        # UID FETCH 并校验结果结构
                        status, msg_data = mail.uid('fetch', eid, '(RFC822)')

                        valid = False
                        email_body = None
                        if status == 'OK' and msg_data and isinstance(msg_data, (list, tuple)) and len(msg_data) > 0:
                            first = msg_data[0]
                            if isinstance(first, (list, tuple)) and len(first) > 1 and isinstance(first[1], (bytes, bytearray)):
                                email_body = first[1]
                                valid = True

                        if not valid:
                            eid_str = eid.decode() if isinstance(eid, (bytes, bytearray)) else str(eid)
                            error_msg = f"处理邮件失败 [UID: {eid_str}]: 无法获取RFC822正文（uid fetch）"
                            logger.error(error_msg)
                            errors.append(error_msg)
                            continue

                        email_message = email.message_from_bytes(email_body)

                        # 处理邮件
                        eid_str = eid.decode() if isinstance(eid, (bytes, bytearray)) else str(eid)
                        result = self._process_email(
                            config.user_id,
                            email_message,
                            eid_str,
                            uid_validity=current_uid_validity
                        )
                        processed_emails += 1

                        # 更新最大 UID
                        try:
                            uid_int = int(eid)
                            if uid_int > max_uid_seen:
                                max_uid_seen = uid_int
                        except Exception:
                            pass

                        if result:
                            results.extend(result)
                            found_invoices += len(result)
                                
                    except Exception as e:
                        eid_str = eid.decode() if isinstance(eid, (bytes, bytearray)) else str(eid)
                        error_msg = f"处理邮件失败 [ID: {eid_str}]: {str(e)}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        continue
                    
                    # 分批提交，降低单次事务压力
                    if (idx + 1) % batch_size == 0:
                        try:
                            self.db.commit()
                        except Exception:
                            self.db.rollback()
            
            mail.close()
            mail.logout()
            
            # 更新最后扫描时间与last_seen_uid（若有）
            config.last_scan_time = datetime.now()
            try:
                if 'max_uid_seen' in locals() and max_uid_seen and (not getattr(config, 'last_seen_uid', None) or max_uid_seen > config.last_seen_uid):
                    config.last_seen_uid = max_uid_seen
            except Exception:
                pass
            self.db.commit()
            
            # 记录扫描完成
            scan_duration = (datetime.now() - scan_start_time).total_seconds()
            logging_service.log_email_event(
                db=self.db,
                event_type="scan_completed",
                message=f"邮箱扫描完成",
                user_id=config.user_id,
                details={
                    "email_address": config.email_address,
                    "total_emails": total_emails,
                    "processed_emails": processed_emails,
                    "found_invoices": found_invoices,
                    "scan_duration": scan_duration,
                    "success_rate": round(processed_emails / total_emails * 100, 2) if total_emails > 0 else 100,
                    "errors_count": len(errors)
                }
            )
            
            # 确保日志提交到数据库
            self.db.commit()
            
            if with_stats:
                return results, {
                    "total_emails": total_emails,
                    "processed_emails": processed_emails,
                    "found_invoices": found_invoices,
                    "errors_count": len(errors),
                }
            return results
            
        except Exception as e:
            error_msg = f"邮箱扫描失败: {str(e)}"
            logger.error(error_msg)
            
            # 记录扫描失败
            logging_service.log_email_event(
                db=self.db,
                event_type="scan_failed",
                message=error_msg,
                user_id=config.user_id,
                details={
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "scan_duration": (datetime.now() - scan_start_time).total_seconds(),
                    "total_emails": total_emails,
                    "processed_emails": processed_emails
                },
                log_level="ERROR"
            )
            
            # 确保错误日志提交到数据库
            try:
                self.db.commit()
            except Exception as commit_error:
                logger.error(f"提交错误日志失败: {str(commit_error)}")
            
            return []
    
    def _process_email(self, user_id: int, email_message, email_id: str = None, uid_validity: int = None) -> List[Dict]:
        """处理单封邮件"""
        results = []
        
        try:
            # 获取邮件基本信息
            subject = self._decode_mime_words(email_message.get('Subject', ''))
            sender = email_message.get('From', '')
            recipient = email_message.get('To', '')
            date_str = email_message.get('Date', '')
            
            # 解析邮件日期
            date_sent = None
            if date_str:
                try:
                    from email.utils import parsedate_to_datetime
                    date_sent = parsedate_to_datetime(date_str)
                except Exception:
                    pass
            
            # 获取邮件正文
            email_body_text = self._get_email_body(email_message, content_type='text')
            email_body_html = self._get_email_body(email_message, content_type='html')
            
            # 处理附件信息
            pdf_attachments = self._extract_pdf_attachments(email_message)
            all_attachments = self._get_all_attachments_info(email_message)
            
            # 构建邮件数据
            email_data = {
                'subject': subject,
                'sender': sender,
                'recipient': recipient,
                'date_sent': date_sent,
                'date_received': datetime.now(),
                'body_text': email_body_text[:5000] if email_body_text else None,  # 限制长度
                'body_html': email_body_html[:10000] if email_body_html else None,  # 限制长度
                'has_attachments': len(all_attachments) > 0,
                'attachment_count': len(all_attachments),
                'attachment_info': all_attachments[:10] if all_attachments else None,  # 只保存前10个附件信息
                'processing_status': 'processing'
            }
            
            # 创建或更新邮件记录
            # 优先使用 Message-ID；缺失时使用稳定的 UIDVALIDITY:UID 作为回退键，避免重复记录
            message_id = email_message.get('Message-ID')
            if not message_id:
                if uid_validity:
                    message_id = f"uid:{uid_validity}:{email_id}"
                else:
                    message_id = f"uid:{email_id}"
            email_record = self.email_list_service.create_or_update_email(
                user_id=user_id,
                message_id=message_id,
                email_data=email_data
            )
            
            # 如果是已存在的邮件记录且已处理过，直接跳过处理
            if email_record.invoice_scan_status in ['has_invoice', 'no_invoice'] and email_record.scanned_at:
                # 降噪：已处理跳过不再单条记录
                return results  # 返回空结果，不进行重复处理
            
            # 标记处理中
            try:
                email_record.processing_status = 'processing'
                self.db.commit()
            except Exception:
                self.db.rollback()
            
            # 检查是否可能包含发票
            if not self._is_invoice_email(subject):
                # 更新邮件状态为无发票
                self.email_list_service.update_scan_status(
                    email_id=email_record.id,
                    user_id=user_id,
                    scan_status="no_invoice",
                    invoice_count=0,
                    scan_result={
                        "reason": "no_invoice_keywords",
                        "subject_checked": True,
                        "attachments_checked": False
                    }
                )
                
                # 降噪：无发票跳过不再单条记录
                return results
            
            # 处理附件
            for attachment in pdf_attachments:
                result = self._process_pdf_attachment(user_id, attachment, email_id)
                if result:
                    results.append(result)
            
            # 处理邮件正文中的下载链接
            pdf_links = self._extract_pdf_links(email_body_text or email_body_html or '')
            for link in pdf_links:
                result = self._download_and_process_pdf(user_id, link, email_id)
                if result:
                    results.append(result)
            
            # 更新邮件扫描状态
            scan_status = "has_invoice" if results else "no_invoice"
            scan_result = {
                "attachments_processed": len(pdf_attachments),
                "links_processed": len(pdf_links),
                "invoices_found": len(results),
                "scan_completed": True,
                "scan_time": datetime.now().isoformat()
            }
            
            self.email_list_service.update_scan_status(
                email_id=email_record.id,
                user_id=user_id,
                scan_status=scan_status,
                invoice_count=len(results),
                scan_result=scan_result
            )
            
            # 处理完成
            try:
                email_record.processing_status = 'completed'
                self.db.commit()
            except Exception:
                self.db.rollback()
            
        except Exception as e:
            error_msg = f"处理邮件内容失败: {str(e)}"
            logger.error(error_msg)
            
            # 尝试创建或更新邮件记录为失败状态（仅更新 processing_status，不改变 invoice_scan_status）
            try:
                message_id = email_message.get('Message-ID', f"email_{email_id}_{int(datetime.now().timestamp())}")
                email_record = self.email_list_service.create_or_update_email(
                    user_id=user_id,
                    message_id=message_id,
                    email_data={
                        'subject': self._decode_mime_words(email_message.get('Subject', '')),
                        'sender': email_message.get('From', ''),
                        'processing_status': 'failed',
                        'error_message': str(e)
                    }
                )

                try:
                    email_record.processing_status = 'failed'
                    email_record.updated_at = datetime.now()
                    self.db.commit()
                except Exception:
                    self.db.rollback()
            except Exception as update_error:
                logger.error(f"更新邮件处理失败状态时出错: {str(update_error)}")
            
            logging_service.log_email_event(
                db=self.db,
                event_type="email_process_failed",
                message=error_msg,
                user_id=user_id,
                details={
                    "email_id": email_id,
                    "error": str(e),
                    "traceback": traceback.format_exc()
                },
                log_level="ERROR"
            )
        
        # 确保单邮件处理的日志被提交
        try:
            self.db.commit()
        except Exception as commit_error:
            logger.error(f"提交邮件处理日志失败: {str(commit_error)}")
        
        return results
    
    def _decode_mime_words(self, s: str) -> str:
        """解码MIME编码的文本"""
        if not s:
            return ''
        
        decoded_words = []
        for word, encoding in decode_header(s):
            if isinstance(word, bytes):
                word = word.decode(encoding or 'utf-8')
            decoded_words.append(word)
        
        return ''.join(decoded_words)
    
    def _is_invoice_email(self, subject: str) -> bool:
        """判断邮件是否可能包含发票"""
        invoice_keywords = [
            '发票', '票据', 'invoice', '开票', '电子发票', 
            '增值税发票', '专用发票', '普通发票', '税务'
        ]
        
        subject_lower = subject.lower()
        return any(keyword.lower() in subject_lower for keyword in invoice_keywords)
    
    def _extract_pdf_attachments(self, email_message) -> List[Dict]:
        """提取PDF附件"""
        attachments = []
        
        for part in email_message.walk():
            if part.get_content_disposition() == 'attachment':
                filename = part.get_filename()
                content_type = part.get_content_type()
                
                # 检查是否为PDF文件（通过文件名或Content-Type）
                is_pdf = False
                if filename:
                    decoded_filename = self._decode_mime_words(filename)
                    is_pdf = decoded_filename.lower().endswith('.pdf')
                
                if not is_pdf and content_type:
                    is_pdf = content_type.lower() == 'application/pdf'
                
                if is_pdf:
                    if not filename:
                        decoded_filename = f"invoice_{len(attachments) + 1}.pdf"
                    else:
                        decoded_filename = self._decode_mime_words(filename)
                    
                    content = part.get_payload(decode=True)
                    
                    # 验证文件内容确实是PDF
                    if content and content.startswith(b'%PDF'):
                        attachments.append({
                            'filename': decoded_filename,
                            'content': content
                        })
        
        return attachments
    
    def _get_all_attachments_info(self, email_message) -> List[Dict]:
        """获取所有附件信息"""
        attachments = []
        
        try:
            for part in email_message.walk():
                if part.get_content_disposition() == 'attachment':
                    filename = part.get_filename()
                    if filename:
                        filename = self._decode_mime_words(filename)
                        content_type = part.get_content_type()
                        content_size = len(part.get_payload(decode=True) or b'')
                        
                        attachments.append({
                            'filename': filename,
                            'content_type': content_type,
                            'size': content_size,
                            'is_pdf': filename.lower().endswith('.pdf')
                        })
        except Exception as e:
            logger.error(f"获取附件信息失败: {str(e)}")
        
        return attachments
    
    def _get_email_body(self, email_message, content_type='text') -> Optional[str]:
        """获取邮件正文"""
        try:
            body = ""
            
            if email_message.is_multipart():
                for part in email_message.walk():
                    if content_type == 'text' and part.get_content_type() == "text/plain":
                        charset = part.get_content_charset() or 'utf-8'
                        body = part.get_payload(decode=True).decode(charset, errors='ignore')
                        break
                    elif content_type == 'html' and part.get_content_type() == "text/html":
                        charset = part.get_content_charset() or 'utf-8'
                        body = part.get_payload(decode=True).decode(charset, errors='ignore')
                        break
            else:
                if (content_type == 'text' and email_message.get_content_type() == "text/plain") or \
                   (content_type == 'html' and email_message.get_content_type() == "text/html"):
                    charset = email_message.get_content_charset() or 'utf-8'
                    body = email_message.get_payload(decode=True).decode(charset, errors='ignore')
            
            return body if body else None
            
        except Exception as e:
            logger.error(f"获取邮件正文失败: {str(e)}")
            return None
    
    def _extract_pdf_links(self, email_body: str) -> List[str]:
        """从邮件正文中提取PDF下载链接"""
        # 匹配可能的PDF下载链接
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+\.pdf(?:\?[^\s<>"{}|\\^`\[\]]*)?'
        pdf_links = re.findall(url_pattern, email_body, re.IGNORECASE)
        
        # 也匹配通用下载链接
        download_pattern = r'https?://[^\s<>"{}|\\^`\[\]]*(?:download|attachment|file)[^\s<>"{}|\\^`\[\]]*'
        download_links = re.findall(download_pattern, email_body, re.IGNORECASE)
        
        return list(set(pdf_links + download_links))
    
    def _process_pdf_attachment(self, user_id: int, attachment: Dict, email_id: str = None) -> Optional[Dict]:
        """处理PDF附件"""
        try:
            # 保存临时文件，并在一次IO中计算哈希
            content_bytes = attachment['content']
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            temp_file.write(content_bytes)
            temp_file.close()
            try:
                import hashlib as _hashlib
                file_md5_hash = _hashlib.md5(content_bytes).hexdigest()
                file_sha256_hash = _hashlib.sha256(content_bytes).hexdigest()
                file_size = len(content_bytes)
            except Exception:
                file_md5_hash = None
                file_sha256_hash = None
                file_size = len(content_bytes)
            # 上游预判重复（基于 (user_id, md5, size)），命中则跳过下游处理
            try:
                if file_md5_hash and file_size:
                    existing = (
                        self.db.query(Invoice)
                        .filter(
                            and_(
                                Invoice.user_id == user_id,
                                Invoice.file_md5_hash == file_md5_hash,
                                Invoice.file_size == file_size,
                            )
                        )
                        .first()
                    )
                    if existing:
                        try:
                            os.unlink(temp_file.name)
                        except Exception:
                            pass
                        return {
                            'type': 'attachment',
                            'filename': attachment['filename'],
                            'status': 'duplicate',
                            'file_size': file_size,
                            'file_md5_hash': file_md5_hash,
                            'file_sha256_hash': file_sha256_hash,
                            'existing_invoice_id': existing.id,
                        }
            except Exception:
                # 预判失败不影响后续流程
                pass
            
            # 创建发票记录
            invoice_data = {
                'original_filename': attachment['filename'],
                'file_path': temp_file.name,
                'file_size': len(attachment['content'])
            }
            
            return {
                'type': 'attachment',
                'filename': attachment['filename'],
                'status': 'processed',
                'file_path': temp_file.name,
                'file_size': file_size,
                'file_md5_hash': file_md5_hash,
                'file_sha256_hash': file_sha256_hash
            }
            
        except Exception as e:
            logger.error(f"处理PDF附件失败: {str(e)}")
            return None
    
    def _download_and_process_pdf(self, user_id: int, url: str, email_id: str = None) -> Optional[Dict]:
        """下载并处理PDF链接"""
        try:
            # 下载文件
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
            response.raise_for_status()
            
            # 检查内容类型
            content_type = response.headers.get('content-type', '').lower()
            is_pdf_ct = ('pdf' in content_type) or ('application/octet-stream' in content_type)
            if (not is_pdf_ct) and (not url.lower().endswith('.pdf')):
                return None
            
            # 获取文件名
            filename = self._extract_filename_from_url(url, response)
            
            # 保存临时文件，并在一次IO中计算哈希
            content_bytes = response.content
            # 验证PDF魔数
            if not content_bytes or not content_bytes.startswith(b'%PDF'):
                return None
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            temp_file.write(content_bytes)
            temp_file.close()
            try:
                import hashlib as _hashlib
                file_md5_hash = _hashlib.md5(content_bytes).hexdigest()
                file_sha256_hash = _hashlib.sha256(content_bytes).hexdigest()
                file_size = len(content_bytes)
            except Exception:
                file_md5_hash = None
                file_sha256_hash = None
                file_size = len(content_bytes)

            # 上游预判重复（基于 (user_id, md5, size)），命中则跳过下游处理
            try:
                if file_md5_hash and file_size:
                    existing = (
                        self.db.query(Invoice)
                        .filter(
                            and_(
                                Invoice.user_id == user_id,
                                Invoice.file_md5_hash == file_md5_hash,
                                Invoice.file_size == file_size,
                            )
                        )
                        .first()
                    )
                    if existing:
                        try:
                            os.unlink(temp_file.name)
                        except Exception:
                            pass
                        return {
                            'type': 'download',
                            'filename': filename,
                            'status': 'duplicate',
                            'url': url,
                            'file_size': file_size,
                            'file_md5_hash': file_md5_hash,
                            'file_sha256_hash': file_sha256_hash,
                            'existing_invoice_id': existing.id,
                        }
            except Exception:
                # 预判失败不影响后续流程
                pass
            
            return {
                'type': 'download',
                'filename': filename,
                'status': 'processed',
                'url': url,
                'file_path': temp_file.name,
                'file_size': file_size,
                'file_md5_hash': file_md5_hash,
                'file_sha256_hash': file_sha256_hash
            }
            
        except Exception as e:
            logger.error(f"下载PDF失败: {url}, 错误: {str(e)}")
            return None
    
    def _extract_filename_from_url(self, url: str, response) -> str:
        """从URL或响应头中提取文件名"""
        # 尝试从Content-Disposition头获取
        content_disposition = response.headers.get('content-disposition', '')
        if content_disposition:
            filename_match = re.search(r'filename[*]?=([^;]+)', content_disposition)
            if filename_match:
                filename = filename_match.group(1).strip('"')
                return filename
        
        # 从URL路径获取
        parsed_url = urlparse(url)
        path = parsed_url.path
        if path:
            filename = os.path.basename(path)
            if filename and '.' in filename:
                return filename
        
        # 默认文件名
        return f"download_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    def get_user_email_configs(self, user_id: int) -> List[EmailConfig]:
        """获取用户的邮箱配置"""
        return self.db.query(EmailConfig).filter(
            EmailConfig.user_id == user_id,
            EmailConfig.is_active == True
        ).all()
    
    def delete_email_config(self, config_id: int, user_id: int) -> bool:
        """删除邮箱配置"""
        config = self.db.query(EmailConfig).filter(
            EmailConfig.id == config_id,
            EmailConfig.user_id == user_id
        ).first()
        
        if config:
            self.db.delete(config)
            self.db.commit()
            return True
        
        return False