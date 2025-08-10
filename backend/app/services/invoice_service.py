from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from sqlalchemy.exc import IntegrityError
from typing import List, Optional, Tuple
from datetime import datetime
import uuid
import os
import logging
import hashlib

from app.models.invoice import Invoice
from app.models.attachment import Attachment
from app.schemas.invoice import InvoiceCreate, InvoiceUpdate, InvoiceFilter, PaginationParams
from app.core.config import settings, get_absolute_file_path
from app.services.logging_service import logging_service
 # 精简：不再依赖复杂的重复检测服务

logger = logging.getLogger(__name__)


class InvoiceService:
    """发票服务类"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_invoice(self, user_id: int, invoice_data: InvoiceCreate, skip_duplicate_check: bool = False) -> Invoice:
        """创建发票记录"""
        try:
            # 统一采用数据库哈希+大小去重（高效、幂等）
            # 优先使用上游传入的哈希与大小，缺失则在后续计算
            
            # 计算/复用文件哈希值（优先使用上游传入的哈希，避免二次IO）
            file_md5_hash = invoice_data.file_md5_hash
            file_sha256_hash = invoice_data.file_sha256_hash
            if not (file_md5_hash and file_sha256_hash and invoice_data.file_size):
                file_path = invoice_data.file_path
                if not os.path.isabs(file_path):
                    file_path = get_absolute_file_path(file_path)
                try:
                    with open(file_path, 'rb') as f:
                        file_content = f.read()
                    file_md5_hash = hashlib.md5(file_content).hexdigest()
                    file_sha256_hash = hashlib.sha256(file_content).hexdigest()
                    invoice_data.file_size = len(file_content)
                except FileNotFoundError:
                    logging_service.log_invoice_event(
                        db=self.db,
                        event_type="invoice_hash_calculation_file_not_found",
                        message=f"无法计算哈希值，文件不存在: {invoice_data.file_path}",
                        user_id=user_id,
                        details={
                            "filename": invoice_data.original_filename,
                            "file_path": invoice_data.file_path
                        },
                        log_level="WARNING"
                    )
                except Exception as hash_error:
                    logging_service.log_invoice_event(
                        db=self.db,
                        event_type="invoice_hash_calculation_failed",
                        message=f"计算哈希值失败: {str(hash_error)}",
                        user_id=user_id,
                        details={
                            "filename": invoice_data.original_filename,
                            "error": str(hash_error),
                            "exception_type": hash_error.__class__.__name__
                        },
                        log_level="ERROR"
                    )

            # DB 级快速去重：优先使用 sha256；否则回退 (md5,size)
            if not skip_duplicate_check:
                existing = None
                if file_sha256_hash:
                    existing = self.db.query(Invoice).filter(
                        and_(
                            Invoice.user_id == user_id,
                            Invoice.file_sha256_hash == file_sha256_hash,
                        )
                    ).first()
                if (existing is None) and file_md5_hash and invoice_data.file_size:
                    existing = self.db.query(Invoice).filter(
                        and_(
                            Invoice.user_id == user_id,
                            Invoice.file_md5_hash == file_md5_hash,
                            Invoice.file_size == invoice_data.file_size,
                        )
                    ).first()
                if existing:
                    raise ValueError(
                        f"发票文件重复，已存在相同文件: {existing.original_filename} (existing_invoice_id={existing.id})"
                    )
                
            db_invoice = Invoice(
                user_id=user_id,
                original_filename=invoice_data.original_filename,
                file_path=invoice_data.file_path,
                file_size=invoice_data.file_size,
                file_md5_hash=file_md5_hash,
                file_sha256_hash=file_sha256_hash,
                source=getattr(invoice_data, 'source', None) or 'manual',
                status="processing",
                ocr_status="pending"
            )
            
            # 设置其他字段
            for field, value in invoice_data.dict(exclude_unset=True).items():
                if hasattr(db_invoice, field):
                    setattr(db_invoice, field, value)
            
            self.db.add(db_invoice)
            self.db.commit()
            self.db.refresh(db_invoice)
            
            # 降噪：发票创建成功不再记录入库日志
            
            return db_invoice
            
        except Exception as e:
            # 回滚事务
            self.db.rollback()
            
            # 记录创建失败日志
            logging_service.log_invoice_event(
                db=self.db,
                event_type="invoice_create_failed",
                message=f"发票创建失败: {str(e)}",
                user_id=user_id,
                details={
                    "filename": invoice_data.original_filename,
                    "error": str(e),
                    "exception_type": e.__class__.__name__
                },
                log_level="ERROR"
            )
            raise
    
    def get_invoice(self, invoice_id: str, user_id: int) -> Optional[Invoice]:
        """获取发票详情"""
        return self.db.query(Invoice).filter(
            and_(Invoice.id == invoice_id, Invoice.user_id == user_id)
        ).first()
    
    def get_invoices(
        self, 
        user_id: int, 
        filters: InvoiceFilter,
        pagination: PaginationParams,
        include_duplicates: bool = False,
    ) -> Tuple[List[Invoice], int]:
        """获取发票列表"""
        query = self.db.query(Invoice).filter(Invoice.user_id == user_id)
        # 全局去重：默认不展示重复发票，除非显式请求包含
        if not include_duplicates:
            query = query.filter(Invoice.status != 'duplicate')
        
        # 应用筛选条件
        if filters.status:
            query = query.filter(Invoice.status == filters.status)
        
        if filters.ocr_status:
            query = query.filter(Invoice.ocr_status == filters.ocr_status)
        
        if filters.seller_name:
            query = query.filter(Invoice.seller_name.ilike(f"%{filters.seller_name}%"))
        # Excel 风格多选：销售方
        if getattr(filters, 'seller_names', None):
            query = query.filter(Invoice.seller_name.in_(filters.seller_names))
        
        if filters.purchaser_name:
            query = query.filter(Invoice.purchaser_name.ilike(f"%{filters.purchaser_name}%"))
        # Excel 风格多选：购方
        if getattr(filters, 'purchaser_names', None):
            query = query.filter(Invoice.purchaser_name.in_(filters.purchaser_names))
        
        if filters.service_type:
            query = query.filter(Invoice.service_type == filters.service_type)
        # Excel 风格多选：发票类型（对应 service_type）
        if getattr(filters, 'service_types', None):
            query = query.filter(Invoice.service_type.in_(filters.service_types))
        
        if filters.date_from:
            query = query.filter(Invoice.invoice_date >= filters.date_from)
        
        if filters.date_to:
            query = query.filter(Invoice.invoice_date <= filters.date_to)
        
        if filters.amount_min:
            query = query.filter(Invoice.total_amount >= filters.amount_min)
        
        if filters.amount_max:
            query = query.filter(Invoice.total_amount <= filters.amount_max)
        
        # 计算总数
        total = query.count()
        
        # 应用分页和排序
        invoices = query.order_by(desc(Invoice.created_at)).offset(
            (pagination.page - 1) * pagination.size
        ).limit(pagination.size).all()
        
        return invoices, total
    
    def update_invoice(self, invoice_id: str, user_id: int, invoice_update: InvoiceUpdate) -> Optional[Invoice]:
        """更新发票信息"""
        invoice = self.get_invoice(invoice_id, user_id)
        if not invoice:
            return None
        
        # 记录更新前的状态
        old_status = invoice.status
        old_ocr_status = invoice.ocr_status
        
        update_data = invoice_update.dict(exclude_unset=True)
        updated_fields = []
        
        for field, value in update_data.items():
            old_value = getattr(invoice, field, None)
            if old_value != value:
                setattr(invoice, field, value)
                updated_fields.append({
                    "field": field,
                    "old_value": old_value,
                    "new_value": value
                })
        
        if updated_fields:
            invoice.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(invoice)
        
        # 降噪：发票常规字段更新不再记录入库日志
        
        # 如果状态发生变化，特别记录状态变更
        new_status = invoice.status
        new_ocr_status = invoice.ocr_status
        
        if old_status != new_status:
            logging_service.log_invoice_event(
                db=self.db,
                event_type="status_changed",
                message=f"发票状态变更: {old_status} -> {new_status}",
                user_id=user_id,
                invoice_id=invoice_id,
                details={
                    "old_status": old_status,
                    "new_status": new_status,
                    "change_reason": "manual_update",
                    "change_time": datetime.now().isoformat()
                }
            )
        
        if old_ocr_status != new_ocr_status:
            # 降噪：OCR状态手动更新不再记录入库日志
            pass
        
        return invoice
    
    def update_ocr_result(self, invoice_id: str, ocr_data: dict, status: str = "success") -> bool:
        """更新OCR识别结果（先判重后赋值；重复样本不占用 invoice_num）"""
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            return False

        old_status = invoice.status
        old_ocr_status = invoice.ocr_status

        invoice.ocr_status = status
        invoice.ocr_raw_data = ocr_data
        invoice.processed_at = datetime.now()

        if status == "success" and ocr_data:
            # 从 ocr_data 中先解析发票号码，但暂不写回，避免唯一约束冲突
            extracted_invoice_num = None
            try:
                words_result = ocr_data.get("words_result", {}) if isinstance(ocr_data, dict) else {}
                if isinstance(words_result, dict):
                    candidate = words_result.get("InvoiceNum")
                    # 兼容多种结构：str 或 dict{word|words}
                    if isinstance(candidate, dict):
                        candidate = candidate.get("words") or candidate.get("word") or ""
                    if isinstance(candidate, list) and candidate:
                        # 取第一项的可读值
                        first = candidate[0]
                        candidate = (first.get("words") or first.get("word") if isinstance(first, dict) else str(first))
                    if isinstance(candidate, str):
                        candidate = candidate.strip()
                    extracted_invoice_num = candidate or None
            except Exception:
                extracted_invoice_num = None

            try:
                existing_invoice = None
                if extracted_invoice_num:
                    existing_invoice = self.db.query(Invoice).filter(
                        and_(
                            Invoice.user_id == invoice.user_id,
                            Invoice.invoice_num == extracted_invoice_num,
                            Invoice.id != invoice_id,
                        )
                    ).first()

                if existing_invoice:
                    # 重复样本：允许写入其它OCR字段，但不占用 invoice_num
                    try:
                        self._extract_ocr_fields(invoice, ocr_data)
                    finally:
                        invoice.invoice_num = None
                    invoice.status = "duplicate"
                    invoice.ocr_error_message = (
                        f"发票重复: 与发票 {existing_invoice.id} ({existing_invoice.original_filename}) 重复"
                    )
                    logging_service.log_invoice_event(
                        db=self.db,
                        event_type="ocr_duplicate_detected",
                        message=f"OCR完成后检测到重复发票: {invoice.original_filename}",
                        user_id=invoice.user_id,
                        invoice_id=invoice_id,
                        details={
                            "filename": invoice.original_filename,
                            "invoice_num": extracted_invoice_num,
                            "duplicate_invoice_id": existing_invoice.id,
                            "duplicate_filename": existing_invoice.original_filename,
                            "status_changed_to": "duplicate",
                            "extracted_fields": self._get_extracted_fields_summary(ocr_data),
                        },
                        log_level="WARNING",
                    )
                else:
                    # 无重复：再写入结构化字段（其中包含 invoice_num）并完成
                    self._extract_ocr_fields(invoice, ocr_data)
                    invoice.status = "completed"
            except Exception as dup_error:
                # 去重检测异常：保守完成，记录错误
                invoice.status = "completed"
                logging_service.log_invoice_event(
                    db=self.db,
                    event_type="ocr_duplicate_check_failed",
                    message=f"OCR完成后去重检测失败: {str(dup_error)}",
                    user_id=invoice.user_id,
                    invoice_id=invoice_id,
                    details={
                        "filename": invoice.original_filename,
                        "invoice_num": extracted_invoice_num,
                        "error": str(dup_error),
                        "exception_type": dup_error.__class__.__name__,
                        "extracted_fields": self._get_extracted_fields_summary(ocr_data),
                    },
                    log_level="ERROR",
                )

        elif status == "failed":
            invoice.ocr_error_message = ocr_data.get("error_message", "OCR识别失败")
            invoice.status = "failed"
            logging_service.log_invoice_event(
                db=self.db,
                event_type="ocr_failed",
                message=f"OCR识别失败: {invoice.original_filename}",
                user_id=invoice.user_id,
                invoice_id=invoice_id,
                details={
                    "old_status": old_status,
                    "new_status": "failed",
                    "old_ocr_status": old_ocr_status,
                    "new_ocr_status": status,
                    "change_reason": "ocr_failed",
                    "error_message": invoice.ocr_error_message,
                    "processed_at": invoice.processed_at.isoformat(),
                },
                log_level="ERROR",
            )

        # 提交并对唯一约束做兜底处理
        try:
            self.db.commit()
        except IntegrityError as ie:
            self.db.rollback()
            # 命中 (user_id, invoice_num) 唯一键冲突时，回退为 duplicate 并释放占用
            if "uq_invoice_user_invoicenum" in str(ie.orig) or "1062" in str(ie.orig):
                invoice.status = "duplicate"
                invoice.ocr_status = "success"
                invoice.ocr_error_message = "发票重复: 唯一票号已被占用"
                invoice.invoice_num = None
                try:
                    self.db.commit()
                except Exception:
                    self.db.rollback()
                    raise
            else:
                raise
        return True
    
    def delete_invoice(self, invoice_id: str, user_id: int) -> bool:
        """删除发票"""
        invoice = self.get_invoice(invoice_id, user_id)
        if not invoice:
            return False
        
        # 删除关联文件（处理相对路径）
        invoice_file_path = invoice.file_path
        if not os.path.isabs(invoice_file_path):
            invoice_file_path = get_absolute_file_path(invoice_file_path)
        if os.path.exists(invoice_file_path):
            os.remove(invoice_file_path)
        
        # 删除附件文件（处理相对路径）
        for attachment in invoice.attachments:
            attachment_file_path = attachment.file_path
            if not os.path.isabs(attachment_file_path):
                attachment_file_path = get_absolute_file_path(attachment_file_path)
            if os.path.exists(attachment_file_path):
                os.remove(attachment_file_path)
        
        self.db.delete(invoice)
        self.db.commit()
        return True
    
    def add_attachment(self, invoice_id: str, user_id: int, filename: str, file_path: str, file_size: int, mime_type: str) -> Optional[Attachment]:
        """为发票添加附件"""
        invoice = self.get_invoice(invoice_id, user_id)
        if not invoice:
            return None
        
        attachment = Attachment(
            invoice_id=invoice_id,
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type
        )
        
        self.db.add(attachment)
        self.db.commit()
        self.db.refresh(attachment)
        return attachment
    
    
    def _extract_ocr_fields(self, invoice: Invoice, ocr_data: dict):
        """从OCR数据中提取结构化字段"""
        if not isinstance(ocr_data, dict):
            raise ValueError(f"Invalid OCR data format: expected dict, got {type(ocr_data)}")
        
        words_result = ocr_data.get("words_result", {})
        if not isinstance(words_result, dict):
            raise ValueError(f"Invalid words_result format: expected dict, got {type(words_result)}")
        
        # 提取发票代码
        invoice.invoice_code = words_result.get("InvoiceCode", "").strip() or None
        
        # 提取发票号码 - 必须字段，为空时报错
        invoice_num = words_result.get("InvoiceNum", "").strip()
        if not invoice_num:
            raise ValueError(f"发票号码为空，OCR识别失败。文件: {invoice.original_filename}")
        invoice.invoice_num = invoice_num
        
        # 提取发票日期
        date_str = words_result.get("InvoiceDate", "").strip()
        if date_str:
            for date_format in ["%Y年%m月%d日", "%Y%m%d", "%Y-%m-%d"]:
                try:
                    invoice.invoice_date = datetime.strptime(date_str, date_format)
                    break
                except ValueError:
                    continue
        
        # 提取金额信息：
        # - TotalAmount: 合计金额（不含税）
        # - TotalTax: 税额
        # - AmountInFiguers/AmountInFigures: 价税合计（小写）
        def _parse_float(value: str) -> Optional[float]:
            try:
                s = str(value).strip()
                return float(s) if s else None
            except (ValueError, TypeError):
                return None

        net_amount = _parse_float(words_result.get("TotalAmount", ""))
        tax_amount = _parse_float(words_result.get("TotalTax", ""))
        gross_amount = _parse_float(
            words_result.get("AmountInFiguers") or words_result.get("AmountInFigures") or ""
        )

        # 先直接写入已提供的数值
        if net_amount is not None:
            invoice.total_amount = net_amount
        if tax_amount is not None:
            invoice.total_tax = tax_amount
        if gross_amount is not None:
            invoice.amount_in_figures = gross_amount

        # 缺失时进行推导补全
        if invoice.amount_in_figures is None and (invoice.total_amount is not None and invoice.total_tax is not None):
            invoice.amount_in_figures = invoice.total_amount + invoice.total_tax
        if invoice.total_amount is None and (invoice.amount_in_figures is not None and invoice.total_tax is not None):
            # 防守：不出现负数
            diff = invoice.amount_in_figures - invoice.total_tax
            invoice.total_amount = diff if diff >= 0 else None
        if invoice.total_tax is None and (invoice.amount_in_figures is not None and invoice.total_amount is not None):
            diff = invoice.amount_in_figures - invoice.total_amount
            invoice.total_tax = diff if diff >= 0 else None
        
        # 提取文本信息
        invoice.amount_in_words = words_result.get("AmountInWords", "").strip() or None
        # 小写金额已在上面统一处理与推导，这里不再重复覆盖
        
        # 提取购买方信息
        invoice.purchaser_name = words_result.get("PurchaserName", "").strip() or None
        invoice.purchaser_register_num = words_result.get("PurchaserRegisterNum", "").strip() or None
        invoice.purchaser_address = words_result.get("PurchaserAddress", "").strip() or None
        invoice.purchaser_bank = words_result.get("PurchaserBank", "").strip() or None
        
        # 提取销售方信息
        invoice.seller_name = words_result.get("SellerName", "").strip() or None
        invoice.seller_register_num = words_result.get("SellerRegisterNum", "").strip() or None
        invoice.seller_address = words_result.get("SellerAddress", "").strip() or None
        invoice.seller_bank = words_result.get("SellerBank", "").strip() or None
        
        # 提取发票类型和服务类型
        invoice.invoice_type = words_result.get("InvoiceType", "").strip() or None
        invoice.service_type = words_result.get("ServiceType", "").strip() or None
        
        # 提取商品明细
        commodity_names = words_result.get("CommodityName", [])
        if isinstance(commodity_names, list) and commodity_names:
            commodity_amounts = words_result.get("CommodityAmount", [])
            commodity_tax_rates = words_result.get("CommodityTaxRate", [])
            commodity_taxes = words_result.get("CommodityTax", [])
            
            commodity_details = []
            for i, name_item in enumerate(commodity_names):
                detail = {
                    "row": str(i + 1),
                    "name": name_item.get("word", "") if isinstance(name_item, dict) else str(name_item),
                    "amount": "",
                    "tax_rate": "",
                    "tax": ""
                }
                
                if i < len(commodity_amounts) and isinstance(commodity_amounts[i], dict):
                    detail["amount"] = commodity_amounts[i].get("word", "")
                if i < len(commodity_tax_rates) and isinstance(commodity_tax_rates[i], dict):
                    detail["tax_rate"] = commodity_tax_rates[i].get("word", "")
                if i < len(commodity_taxes) and isinstance(commodity_taxes[i], dict):
                    detail["tax"] = commodity_taxes[i].get("word", "")
                
                commodity_details.append(detail)
            
            invoice.commodity_details = commodity_details
    
    def _get_extracted_fields_summary(self, ocr_data: dict) -> dict:
        """获取提取字段的摘要信息"""
        words_result = ocr_data.get("words_result", {})
        
        # 统计识别的字段
        recognized_fields = []
        for key, value in words_result.items():
            if isinstance(value, str) and value.strip():
                recognized_fields.append(key)
            elif isinstance(value, list) and value:
                recognized_fields.append(key)
            elif value:  # 其他非空值
                recognized_fields.append(key)
        
        # 检查关键字段
        key_fields = ["InvoiceCode", "InvoiceNum", "InvoiceDate", "SellerName", "PurchaserName", "TotalAmount"]
        key_fields_found = [field for field in key_fields if field in recognized_fields]
        
        return {
            "total_fields": len(recognized_fields),
            "recognized_fields": recognized_fields[:10],  # 只记录前10个字段
            "key_fields_found": key_fields_found,
            "key_fields_count": len(key_fields_found),
            "recognition_rate": round(len(key_fields_found) / len(key_fields) * 100, 2)
        }