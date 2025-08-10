from celery import Task
from app.workers.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.invoice_service import InvoiceService
import os
from app.services.ocr_service import OCRService
from app.services.logging_service import logging_service
from app.models.invoice import Invoice
import logging
import traceback
from datetime import datetime
# 指标在服务层统一记录，这里不再导入指标

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """带数据库会话的Celery任务基类"""
    _db = None
    
    @property
    def db(self):
        if self._db is None:
            self._db = SessionLocal()
        return self._db
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        if self._db is not None:
            self._db.close()


@celery_app.task(base=DatabaseTask, bind=True, max_retries=3, rate_limit="2/s")
def process_invoice_ocr(self, invoice_id: str, file_path: str, user_id: int = None):
    """处理发票OCR识别任务"""
    start_time = datetime.now()
    
    try:
        # 降低噪音
        logger.debug(f"开始处理发票OCR识别: {invoice_id}")
        
        # 获取服务实例
        invoice_service = InvoiceService(self.db)
        ocr_service = OCRService(self.db)
        
        # 检查发票是否存在
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            error_msg = f"发票不存在: {invoice_id}"
            logger.error(error_msg)
            
            # 记录错误日志
            logging_service.log_ocr_event(
                db=self.db,
                event_type="ocr_error",
                message=error_msg,
                user_id=user_id or invoice.user_id if invoice else None,
                invoice_id=invoice_id,
                details={
                    "file_path": file_path,
                    "duration": 0,
                    "error_type": "invoice_not_found"
                },
                log_level="ERROR"
            )
            
            return {"status": "error", "message": "发票不存在"}
        
        # 如果没有提供user_id，从发票中获取
        if not user_id:
            user_id = invoice.user_id
        
        # 直接使用发票来源字段判断是否来自邮件
        is_from_email = (getattr(invoice, 'source', None) == 'email')
        
        # 记录OCR开始
        ocr_details = {
            "file_path": file_path,
            "task_id": self.request.id, 
            "retry_count": self.request.retries,
            "original_filename": invoice.original_filename,
            "is_from_email": is_from_email
        }
        
        
        # 更新状态为处理中
        invoice.ocr_status = "processing"
        self.db.commit()
        
        # 执行OCR识别
        ocr_result = ocr_service.recognize_invoice(file_path, user_id=user_id, invoice_id=invoice_id)
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # 判断OCR是否成功：有words_result且没有error_code，或者error_code为0
        is_success = False
        if "words_result" in ocr_result and "error_code" not in ocr_result:
            # 检查words_result是否为空
            words_result = ocr_result.get("words_result", {})
            if words_result:  # words_result不为空才算成功
                is_success = True
        elif ocr_result.get("error_code") == 0:
            # 有error_code但为0也表示成功
            is_success = True
        
        if is_success:
            # OCR成功
            invoice_service.update_ocr_result(invoice_id, ocr_result, "success")
            # 成功不打入库日志，这里仅调试输出
            logger.debug(f"发票OCR识别成功: {invoice_id}")
            
            # 记录成功日志
            success_details = {
                "file_path": file_path,
                "task_id": self.request.id,
                "retry_count": self.request.retries,
                "words_count": len(ocr_result.get("words_result", {})),
                "processing_time": processing_time,
                "duration": processing_time,
                "original_filename": invoice.original_filename,
                "is_from_email": is_from_email
            }
            
            
            return {"status": "success", "invoice_id": invoice_id}
        else:
            # OCR失败
            error_msg = ocr_result.get("error_msg", "OCR识别失败")
            error_code = ocr_result.get("error_code")
            # 当服务商返回QPS超限（例如 error_code=18）时，采用指数退避重试
            try:
                if int(error_code) == 18 and self.request.retries < self.max_retries:
                    backoff_seconds = min(60, (2 ** self.request.retries))  # 1, 2, 4, ... 上限60
                    logger.warning(f"OCR QPS超限，{backoff_seconds}s后重试: {invoice_id}")
                    # 记录重试日志
                    try:
                        logging_service.log_ocr_event(
                            db=self.db,
                            event_type="ocr_rate_limited_retry",
                            message=f"OCR QPS超限，{backoff_seconds}s后重试",
                            user_id=user_id,
                            invoice_id=invoice_id,
                            details={
                                "error_code": error_code,
                                "retry_in_seconds": backoff_seconds,
                                "retry_count": self.request.retries + 1,
                                "max_retries": self.max_retries,
                            },
                            log_level="WARNING",
                        )
                    except Exception:
                        pass
                    raise self.retry(countdown=backoff_seconds)
            except Exception:
                pass
            invoice_service.update_ocr_result(
                invoice_id, 
                {"error_message": error_msg}, 
                "failed"
            )
            logger.error(f"发票OCR识别失败: {invoice_id}, 错误: {error_msg}")
            
            # 记录失败日志
            failed_details = {
                "file_path": file_path,
                "task_id": self.request.id,
                "retry_count": self.request.retries,
                "error_code": ocr_result.get("error_code"),
                "error_message": error_msg,
                "processing_time": processing_time,
                "duration": processing_time,
                "original_filename": invoice.original_filename,
                "ocr_response": ocr_result,
                "is_from_email": is_from_email
            }
            
            # 如果来自邮件，同时记录到邮件日志
            if is_from_email:
                logging_service.log_email_event(
                    db=self.db,
                    event_type="email_invoice_ocr_failed",
                    message=f"邮件发票OCR识别失败: {invoice.original_filename} - {error_msg}",
                    user_id=user_id,
                    details={
                        "invoice_id": invoice_id,
                        "filename": invoice.original_filename,
                        "error_code": ocr_result.get("error_code"),
                        "error_message": error_msg,
                        "processing_time": processing_time,
                        "task_id": self.request.id,
                        "transition": "email_to_ocr_failed"
                    },
                    log_level="ERROR"
                )
            
            logging_service.log_ocr_event(
                db=self.db,
                event_type="ocr_failed",
                message=f"OCR识别失败: {invoice.original_filename} - {error_msg}",
                user_id=user_id,
                invoice_id=invoice_id,
                details=failed_details,
                log_level="ERROR"
            )
            
            # 确保失败日志提交到数据库
            try:
                self.db.commit()
            except Exception as commit_error:
                logger.error(f"提交OCR失败日志失败: {str(commit_error)}")
            
            return {"status": "failed", "message": error_msg}
            
    except Exception as exc:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"发票OCR识别异常: {invoice_id}, 错误: {str(exc)}")
        # 指标在服务层统一记录
        
        # 记录异常日志
        try:
            logging_service.log_ocr_event(
                db=self.db,
                event_type="ocr_exception",
                message=f"OCR处理异常: {str(exc)}",
                user_id=user_id,
                invoice_id=invoice_id,
                details={
                    "file_path": file_path,
                    "task_id": self.request.id,
                    "retry_count": self.request.retries,
                    "exception_type": exc.__class__.__name__,
                    "error_message": str(exc),
                    "processing_time": processing_time,
                    "duration": processing_time,
                    "traceback": traceback.format_exc()
                },
                log_level="ERROR"
            )
            
            # 确保异常日志提交到数据库
            try:
                self.db.commit()
            except Exception as commit_error:
                logger.error(f"提交OCR异常日志失败: {str(commit_error)}")
        except:
            pass
        
        # 重试机制
        if self.request.retries < self.max_retries:
            logger.warning(f"重试发票OCR识别: {invoice_id}, 第{self.request.retries + 1}次")
            
            # 记录重试日志（按正确签名）
            try:
                logging_service.log_ocr_event(
                    db=self.db,
                    event_type="ocr_retrying",
                    message=f"OCR任务即将重试，第{self.request.retries + 1}次",
                    user_id=user_id,
                    invoice_id=invoice_id,
                    details={
                        "task_id": self.request.id,
                        "file_path": file_path,
                        "retry_count": self.request.retries + 1,
                        "max_retries": self.max_retries,
                        "retry_countdown": 60 * (self.request.retries + 1)
                    }
                )
            except Exception:
                pass
            
            raise self.retry(countdown=60 * (self.request.retries + 1))
        
        # 标记为失败
        try:
            invoice_service = InvoiceService(self.db)
            invoice_service.update_ocr_result(
                invoice_id,
                {"error_message": f"OCR处理异常: {str(exc)}"},
                "failed"
            )
            
            # 记录最终失败日志
            logging_service.log_ocr_event(
                db=self.db,
                event_type="ocr_failed_final",
                message=f"OCR处理最终失败: OCR处理异常: {str(exc)}",
                user_id=user_id,
                invoice_id=invoice_id,
                details={
                    "file_path": file_path,
                    "task_id": self.request.id,
                    "retry_count": self.request.retries,
                    "max_retries_reached": True,
                    "exception_type": exc.__class__.__name__,
                    "error_message": f"OCR处理异常: {str(exc)}",
                    "processing_time": processing_time,
                    "duration": processing_time
                },
                log_level="CRITICAL"
            )
            
            # 确保最终失败日志提交到数据库
            try:
                self.db.commit()
            except Exception as commit_error:
                logger.error(f"提交OCR最终失败日志失败: {str(commit_error)}")
        except:
            pass
        
        return {"status": "error", "message": str(exc)}