from celery import Task
from app.workers.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.config import settings
from app.services.email_service import EmailService
from app.services.invoice_service import InvoiceService
from app.services.email_list_service import EmailListService
from app.services.logging_service import logging_service
from app.models.email_config import EmailConfig
from app.models.system_log import SystemLog
import logging
import redis
import time
from datetime import datetime
from app.core.metrics import FILES_PROCESSED, EMAILS_INVOICES_FOUND, EMAIL_DUPLICATES

logger = logging.getLogger(__name__)


def get_email_scan_lock_key(user_id: int, config_id: int = None) -> str:
    """生成邮箱扫描锁的Redis key"""
    if config_id:
        return f"email_scan_lock:user:{user_id}:config:{config_id}"
    else:
        return f"email_scan_lock:user:{user_id}:all"


def acquire_email_scan_lock(user_id: int, config_id: int = None, timeout: int = 3600) -> bool:
    """获取邮箱扫描锁"""
    try:
        redis_client = redis.from_url(settings.REDIS_URL)
        lock_key = get_email_scan_lock_key(user_id, config_id)
        
        # 设置锁，过期时间为1小时
        result = redis_client.set(lock_key, f"task_started_{datetime.now().isoformat()}", ex=timeout, nx=True)
        
        if result:
            logger.info(f"获取邮箱扫描锁成功: {lock_key}")
            return True
        else:
            logger.warning(f"获取邮箱扫描锁失败，锁已存在: {lock_key}")
            return False
            
    except Exception as e:
        logger.error(f"获取邮箱扫描锁异常: {e}")
        return False


def release_email_scan_lock(user_id: int, config_id: int = None):
    """释放邮箱扫描锁"""
    try:
        redis_client = redis.from_url(settings.REDIS_URL)
        lock_key = get_email_scan_lock_key(user_id, config_id)
        
        redis_client.delete(lock_key)
        logger.info(f"释放邮箱扫描锁: {lock_key}")
        
    except Exception as e:
        logger.error(f"释放邮箱扫描锁异常: {e}")


class EmailScanLockMixin:
    """邮箱扫描锁混入类"""
    
    def acquire_scan_lock(self, user_id: int, config_id: int = None) -> bool:
        """获取扫描锁"""
        return acquire_email_scan_lock(user_id, config_id)
    
    def release_scan_lock(self, user_id: int, config_id: int = None):
        """释放扫描锁"""
        release_email_scan_lock(user_id, config_id)


def is_email_scan_running(user_id: int, config_id: int = None) -> bool:
    """检查是否有正在运行的邮箱扫描任务（基于Redis锁）"""
    try:
        redis_client = redis.from_url(settings.REDIS_URL)
        # 优先检查指定配置锁
        if config_id:
            if redis_client.exists(get_email_scan_lock_key(user_id, config_id)):
                return True
        # 检查用户全局锁
        if redis_client.exists(get_email_scan_lock_key(user_id, None)):
            return True
        return False
    except Exception as e:
        logger.warning(f"检查邮箱扫描锁失败: {e}")
        return False


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


@celery_app.task(base=DatabaseTask, bind=True)
def scan_emails_task(self, config_id: int = None, days: int = 7):
    """邮箱扫描定时任务"""
    start_time = datetime.now()
    task_id = self.request.id
    
    # 检查是否有邮箱扫描任务正在运行
    if config_id:
        # 单个邮箱配置扫描，检查该配置的锁
        config = self.db.query(EmailConfig).filter(EmailConfig.id == config_id).first()
        if config:
            if is_email_scan_running(config.user_id, config_id):
                logger.info(f"邮箱扫描任务已在运行中: config_id={config_id}")
                return {
                    "status": "skipped", 
                    "message": "扫描任务已在运行中",
                    "duration": 0
                }
    else:
        # 全局扫描，检查是否有任何用户的全局扫描在运行
        configs = self.db.query(EmailConfig).filter(EmailConfig.is_active == True).all()
        running_configs = []
        for config in configs:
            if is_email_scan_running(config.user_id):
                running_configs.append(config.id)
        
        if running_configs:
            logger.info(f"以下邮箱配置的扫描任务已在运行中: {running_configs}")
            return {
                "status": "skipped",
                "message": f"扫描任务已在运行中: {running_configs}",
                "duration": 0
            }
    
    try:
        logger.info(f"开始执行邮箱扫描任务: task_id={task_id}")
        
        # 记录任务开始
        logging_service.log_system_event(
            db=self.db,
            event_type="email_scan_started",
            message=f"开始执行定时邮箱扫描任务",
            details={
                "task_id": task_id,
                "config_id": config_id,
                "days": days,
                "start_time": start_time.isoformat()
            }
        )
        
        email_service = EmailService(self.db)
        invoice_service = InvoiceService(self.db)
        
        # 获取要扫描的邮箱配置
        if config_id:
            configs = [self.db.query(EmailConfig).filter(
                EmailConfig.id == config_id,
                EmailConfig.is_active == True
            ).first()]
        else:
            configs = self.db.query(EmailConfig).filter(
                EmailConfig.is_active == True
            ).all()
        
        if not configs or configs == [None]:
            logger.info("没有找到活跃的邮箱配置")
            
            # 记录结果
            logging_service.log_system_event(
                db=self.db,
                event_type="email_scan_no_config",
                message="没有找到活跃的邮箱配置",
                details={"task_id": task_id},
                log_level="WARNING"
            )
            
            return {"status": "no_configs", "message": "没有活跃的邮箱配置"}
        
        total_processed = 0
        total_success = 0
        total_errors = 0
        total_duplicates = 0
        config_results = []
        
        for config in configs:
            config_start_time = datetime.now()
            
            try:
                logger.info(f"开始扫描邮箱: {config.email_address}")
                
                # 记录开始扫描日志
                logging_service.log_email_event(
                    db=self.db,
                    event_type="scan_started",
                    message=f"开始扫描邮箱: {config.email_address}",
                    user_id=config.user_id,
                    details={"task_id": task_id, "days": days, "config_id": config.id}
                )
                
                # 执行邮箱扫描
                scan_results = email_service.scan_emails(config, days)
                
                processed_count = len(scan_results)
                FILES_PROCESSED.inc(processed_count)
                success_count = 0
                error_count = 0
                duplicate_count = 0
                processed_files = []
                errors = []
                
                # 处理扫描结果
                for result in scan_results:
                    try:
                        # 将临时文件移动到正式位置并创建发票记录
                        # 如果上游或下游已经标记重复，计数后跳过
                        if result.get("status") == "duplicate":
                            duplicate_count += 1
                            EMAIL_DUPLICATES.labels(type="attachment").inc()
                            continue

                        invoice_result = _process_scanned_file(
                            config.user_id,
                            result,
                            invoice_service
                        )
                        
                        if invoice_result == "DUPLICATE":
                            duplicate_count += 1
                            EMAIL_DUPLICATES.labels(type="create_invoice").inc()
                        elif invoice_result:
                            success_count += 1
                            processed_files.append({
                                "filename": result.get("filename"),
                                "invoice_id": invoice_result,
                                "status": "success"
                            })
                            EMAILS_INVOICES_FOUND.inc()
                        else:
                            error_count += 1
                            error_msg = f"处理文件失败: {result.get('filename')}"
                            errors.append(error_msg)
                            
                            # 记录失败
                            logging_service.log_email_event(
                                db=self.db,
                                event_type="file_processing_failed",
                                message=error_msg,
                                user_id=config.user_id,
                                details={
                                    "filename": result.get("filename"),
                                    "task_id": task_id,
                                    "config_id": config.id
                                },
                                log_level="ERROR"
                            )
                            
                    except Exception as e:
                        logger.error(f"处理扫描文件失败: {str(e)}")
                        error_count += 1
                        error_msg = f"处理文件异常: {result.get('filename')}, {str(e)}"
                        errors.append(error_msg)
                        
                        # 记录异常
                        logging_service.log_email_event(
                            db=self.db,
                            event_type="file_processing_error",
                            message=error_msg,
                            user_id=config.user_id,
                            details={
                                "filename": result.get("filename"),
                                "error": str(e),
                                "task_id": task_id,
                                "config_id": config.id
                            },
                            log_level="ERROR"
                        )
                
                total_processed += processed_count
                total_success += success_count
                total_errors += error_count
                total_duplicates += duplicate_count
                
                config_duration = (datetime.now() - config_start_time).total_seconds()
                
                # 记录扫描结果日志（统计聚合）
                logging_service.log_email_event(
                    db=self.db,
                    event_type="scan_completed",
                    message=(
                        f"邮箱扫描完成: {config.email_address} - 共处理{processed_count}张，其中"
                        f"{duplicate_count}张重复，{success_count}张成功，{error_count}张失败"
                    ),
                    user_id=config.user_id,
                    details={
                        "task_id": task_id,
                        "processed": processed_count,
                        "success": success_count,
                        "duplicates": duplicate_count,
                        "errors": error_count,
                        "duration": config_duration,
                        "files": processed_files[:5],  # 只记录前5个文件
                        "config_id": config.id
                    }
                )
                
                config_results.append({
                    "config_id": config.id,
                    "email_address": config.email_address,
                    "processed": processed_count,
                    "success": success_count,
                    "duplicates": duplicate_count,
                    "errors": error_count,
                    "duration": config_duration
                })
                
                logger.info(f"邮箱扫描完成: {config.email_address}, 处理{processed_count}个文件")
                
            except Exception as e:
                logger.error(f"扫描邮箱失败: {config.email_address}, 错误: {str(e)}")
                total_errors += 1
                
                # 记录错误日志
                logging_service.log_email_event(
                    db=self.db,
                    event_type="scan_failed",
                    message=f"邮箱扫描失败: {config.email_address}",
                    user_id=config.user_id,
                    details={"task_id": task_id, "error": str(e), "config_id": config.id},
                    log_level="ERROR"
                )
                
                config_results.append({
                    "config_id": config.id,
                    "email_address": config.email_address,
                    "processed": 0,
                    "success": 0,
                    "errors": 1,
                    "error": str(e)
                })
        
        total_duration = (datetime.now() - start_time).total_seconds()
        
        result_summary = {
            "status": "completed",
            "total_processed": total_processed,
            "total_success": total_success,
            "total_errors": total_errors,
            "total_duplicates": total_duplicates,
            "scanned_configs": len([c for c in configs if c is not None]),
            "duration": total_duration,
            "config_results": config_results
        }
        
        # 记录任务完成（统计聚合）
        logging_service.log_system_event(
            db=self.db,
            event_type="email_scan_completed",
            message=(
                f"定时邮箱扫描任务完成 - 共处理{total_processed}张，其中{total_duplicates}张重复，"
                f"{total_success}张成功，{total_errors}张失败"
            ),
            details={
                "task_id": task_id,
                "total_processed": total_processed,
                "total_success": total_success,
                "total_errors": total_errors,
                "total_duplicates": total_duplicates,
                "duration": total_duration,
                "scanned_configs": len([c for c in configs if c is not None])
            }
        )
        
        # 确保所有日志提交到数据库
        try:
            self.db.commit()
        except Exception as commit_error:
            logger.error(f"提交邮箱扫描任务日志失败: {str(commit_error)}")
        
        logger.info(f"邮箱扫描任务完成: {result_summary}")
        return result_summary
        
    except Exception as exc:
        total_duration = (datetime.now() - start_time).total_seconds()
        logger.error(f"邮箱扫描任务异常: {str(exc)}")
        
        # 记录任务异常
        try:
            logging_service.log_system_event(
                db=self.db,
                event_type="email_scan_error",
                message=f"定时邮箱扫描任务异常",
                details={
                    "task_id": task_id,
                    "error": str(exc),
                    "duration": total_duration,
                    "exception_type": exc.__class__.__name__
                },
                log_level="ERROR"
            )
            
            # 确保错误日志提交到数据库
            self.db.commit()
        except Exception as commit_error:
            logger.error(f"提交邮箱扫描任务错误日志失败: {str(commit_error)}")
            pass
        
        return {
            "status": "error",
            "message": str(exc),
            "duration": total_duration
        }


@celery_app.task(base=DatabaseTask, bind=True)
def manual_email_scan_task(self, user_id: int, config_id: int = None, days: int = 7):
    """手动邮箱扫描任务"""
    start_time = datetime.now()
    task_id = self.request.id
    
    # 获取分布式锁
    if not acquire_email_scan_lock(user_id, config_id):
        logger.warning(f"邮箱扫描任务已在运行中: user_id={user_id}, config_id={config_id}")
        return {
            "success": False,
            "message": "扫描进行中，请稍候再试",
            "scanned_count": 0,
            "processed_count": 0,
            "error_count": 0
        }
    
    try:
        logger.info(f"开始手动邮箱扫描: user_id={user_id}, config_id={config_id}")
        
        # 记录任务开始
        logging_service.log_email_event(
                    db=self.db,
                    event_type="manual_scan_started",
                    message=f"开始手动邮箱扫描",
                    user_id=user_id,
                    details={
                "task_id": task_id,
                "config_id": config_id,
                "days": days,
                "start_time": start_time.isoformat()
            }
                )
        
        email_service = EmailService(self.db)
        invoice_service = InvoiceService(self.db)
        
        # 获取用户的邮箱配置
        if config_id:
            configs = [self.db.query(EmailConfig).filter(
                EmailConfig.id == config_id,
                EmailConfig.user_id == user_id,
                EmailConfig.is_active == True
            ).first()]
        else:
            configs = email_service.get_user_email_configs(user_id)
        
        if not configs or configs == [None]:
            # 记录没有配置
            logging_service.log_email_event(
                    db=self.db,
                    event_type="manual_scan_no_config",
                    message="没有找到邮箱配置",
                    user_id=user_id,
                    details={"task_id": task_id, "config_id": config_id},
                    log_level="WARNING"
                )
            
            return {
                "status": "no_configs",
                "message": "没有找到邮箱配置"
            }
        
        results = []
        
        for config in configs:
            if config is None:
                continue
            
            config_start_time = datetime.now()
                
            try:
                # 执行扫描
                scan_results = email_service.scan_emails(config, days)
                
                processed_files = []
                success_count = 0
                error_count = 0
                duplicate_count = 0
                errors = []
                
                for result in scan_results:
                    try:
                        # 如果上游或下游已经标记重复，计数后跳过
                        if result.get("status") == "duplicate":
                            duplicate_count += 1
                            continue

                        invoice_result = _process_scanned_file(
                            user_id, result, invoice_service
                        )
                        
                        if invoice_result == "DUPLICATE":
                            duplicate_count += 1
                        elif invoice_result:
                            success_count += 1
                            processed_files.append({
                                "filename": result.get("filename"),
                                "type": result.get("type"),
                                "status": "success",
                                "invoice_id": invoice_result
                            })
                            
                        else:
                            error_count += 1
                            error_msg = f"处理文件失败: {result.get('filename')}"
                            errors.append(error_msg)
                            
                            # 记录失败
                            logging_service.log_email_event(
                                db=self.db,
                                event_type="manual_file_processing_failed",
                                message=error_msg,
                                user_id=user_id,
                                details={
                                    "filename": result.get("filename"),
                                    "task_id": task_id,
                                    "config_id": config.id
                                },
                                log_level="ERROR"
                            )
                            
                    except Exception as e:
                        error_count += 1
                        error_msg = f"处理文件异常: {result.get('filename')}, {str(e)}"
                        errors.append(error_msg)
                        
                        # 记录异常
                        logging_service.log_email_event(
                    db=self.db,
                    event_type="manual_file_processing_error",
                    message=error_msg,
                    user_id=user_id,
                    details={
                                "filename": result.get("filename"),
                                "error": str(e),
                                "task_id": task_id
, "config_id": config.id},
                    log_level="ERROR"
                )
                
                config_duration = (datetime.now() - config_start_time).total_seconds()
                
                # 记录配置的扫描结果（统计聚合）
                logging_service.log_email_event(
                    db=self.db,
                    event_type="manual_scan_config_completed",
                    message=(
                        f"手动扫描完成: {config.email_address} - 共处理{len(scan_results)}张，其中"
                        f"{duplicate_count}张重复，{success_count}张成功，{error_count}张失败"
                    ),
                    user_id=user_id,
                    details={
                        "task_id": task_id,
                        "processed_count": len(scan_results),
                        "success_count": success_count,
                        "duplicate_count": duplicate_count,
                        "error_count": error_count,
                        "duration": config_duration,
                        "files": processed_files[:5],  # 只记录前5个文件
                        "config_id": config.id
                    }
                )
                
                results.append({
                    "config_id": config.id,
                    "email_address": config.email_address,
                    "processed_count": len(scan_results),
                    "success_count": success_count,
                    "duplicate_count": duplicate_count,
                    "error_count": error_count,
                    "errors": errors,
                    "processed_files": processed_files,
                    "duration": config_duration
                })
                
            except Exception as e:
                error_msg = str(e)
                results.append({
                    "config_id": config.id,
                    "email_address": config.email_address,
                    "processed_count": 0,
                    "success_count": 0,
                    "error_count": 1,
                    "errors": [error_msg],
                    "processed_files": []
                })
                
                # 记录配置错误
                logging_service.log_email_event(
                    db=self.db,
                    event_type="manual_scan_config_error",
                    message=f"手动扫描错误: {config.email_address}",
                    user_id=user_id,
                    details={"task_id": task_id, "error": error_msg, "config_id": config.id},
                    log_level="ERROR"
                )
        
        total_duration = (datetime.now() - start_time).total_seconds()
        total_processed = sum(r["processed_count"] for r in results)
        total_success = sum(r["success_count"] for r in results)
        total_errors = sum(r["error_count"] for r in results)
        total_duplicates = sum(r.get("duplicate_count", 0) for r in results)
        
        # 记录任务完成（统计聚合）
        logging_service.log_email_event(
            db=self.db,
            event_type="manual_scan_completed",
            message=(
                f"手动邮箱扫描任务完成 - 共处理{total_processed}张，其中{total_duplicates}张重复，"
                f"{total_success}张成功，{total_errors}张失败"
            ),
            user_id=user_id,
            details={
                "task_id": task_id,
                "total_processed": total_processed,
                "total_success": total_success,
                "total_errors": total_errors,
                "total_duplicates": total_duplicates,
                "duration": total_duration,
                "scanned_configs": len(results),
                "config_id": config_id
            }
        )
        
        # 确保所有日志提交到数据库
        try:
            self.db.commit()
        except Exception as commit_error:
            logger.error(f"提交手动邮箱扫描任务日志失败: {str(commit_error)}")
        
        return {
            "status": "completed",
            "results": results,
            "summary": {
                "total_processed": total_processed,
                "total_success": total_success,
                "total_errors": total_errors,
                "total_duplicates": total_duplicates,
                "duration": total_duration
            }
        }
        
    except Exception as exc:
        total_duration = (datetime.now() - start_time).total_seconds()
        logger.error(f"手动邮箱扫描任务异常: {str(exc)}")
        
        # 记录任务异常
        try:
            logging_service.log_email_event(
                db=self.db,
                event_type="manual_scan_error",
                message=f"手动邮箱扫描任务异常",
                user_id=user_id,
                details={
                    "task_id": task_id,
                    "error": str(exc),
                    "duration": total_duration,
                    "exception_type": exc.__class__.__name__,
                    "config_id": config_id
                },
                log_level="ERROR"
            )
            
            # 确保错误日志提交到数据库
            self.db.commit()
        except Exception as commit_error:
            logger.error(f"提交手动邮箱扫描任务错误日志失败: {str(commit_error)}")
            pass
        
        return {
            "status": "error",
            "message": str(exc),
            "duration": total_duration
        }
    finally:
        # 在finally块中释放锁，确保无论成功还是异常都会释放
        release_email_scan_lock(user_id, config_id)


def _process_scanned_file(user_id: int, scan_result: dict, invoice_service: InvoiceService) -> str:
    """处理扫描到的文件"""
    import shutil
    import uuid
    import os
    from pathlib import Path
    from app.core.config import settings, get_absolute_file_path, get_relative_file_path
    from app.workers.ocr_tasks import process_invoice_ocr
    from app.services.logging_service import logging_service
    from datetime import datetime
    
    process_start_time = datetime.now()
    
    try:
        temp_path = scan_result.get("file_path")
        filename = scan_result.get("filename", "unknown.pdf")
        
        # 记录开始处理扫描文件
        db = SessionLocal()
        try:
            logging_service.log_email_event(
                db=db,
                event_type="scanned_file_processing_started",
                message=f"开始处理邮件扫描文件: {filename}",
                user_id=user_id,
                details={
                    "filename": filename,
                    "temp_path": temp_path,
                    "scan_type": scan_result.get("type", "attachment"),
                    "file_size": scan_result.get("file_size", 0)
                }
            )
            db.commit()
        except Exception as log_error:
            logger.error(f"记录扫描文件处理开始日志失败: {str(log_error)}")
        finally:
            db.close()
        
        if not temp_path or not os.path.exists(temp_path):
            # 记录文件不存在错误
            db = SessionLocal()
            try:
                logging_service.log_email_event(
                    db=db,
                    event_type="scanned_file_not_found",
                    message=f"扫描文件不存在: {filename}",
                    user_id=user_id,
                    details={
                        "filename": filename,
                        "temp_path": temp_path,
                        "error": "file_not_found"
                    },
                    log_level="ERROR"
                )
                db.commit()
            except Exception as log_error:
                logger.error(f"记录扫描文件不存在日志失败: {str(log_error)}")
            finally:
                db.close()
            return None
        
        # 内容寻址存储：以 sha256 作为文件名，避免重复落盘
        relative_upload_dir = os.path.join("storage", "invoices", str(user_id))
        absolute_upload_dir = get_absolute_file_path(relative_upload_dir)
        upload_dir = Path(absolute_upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)

        filename = scan_result.get("filename", "email_scan.pdf")
        file_extension = Path(filename).suffix or ".pdf"

        upstream_sha256 = scan_result.get("file_sha256_hash")
        if not upstream_sha256:
            # 回退计算一次（仅在缺失时）
            with open(temp_path, 'rb') as _f:
                import hashlib as _hashlib
                upstream_sha256 = _hashlib.sha256(_f.read()).hexdigest()
        new_filename = f"{upstream_sha256}{file_extension}"

        # 最终路径
        absolute_final_path = upload_dir / new_filename
        relative_file_path = os.path.join(relative_upload_dir, new_filename)

        # 若目标已存在则删除临时文件，否则移动
        if absolute_final_path.exists():
            os.unlink(temp_path)
            try:
                EMAIL_DUPLICATES.labels(type="file_store_skip").inc()
            except Exception:
                pass
        else:
            shutil.move(temp_path, str(absolute_final_path))
        
        
        # 创建发票记录（启用去重检测，使用相对路径）
        from app.schemas.invoice import InvoiceCreate
        # 复用上游已计算的哈希，避免创建阶段二次读取
        upstream_md5 = scan_result.get("file_md5_hash")
        upstream_sha256 = scan_result.get("file_sha256_hash")
        upstream_size = scan_result.get("file_size") or os.path.getsize(absolute_final_path)
        invoice_data = InvoiceCreate(
            original_filename=filename,
            file_path=relative_file_path,
            file_size=upstream_size,
            file_md5_hash=upstream_md5,
            file_sha256_hash=upstream_sha256,
            source="email"
        )
        
        try:
            # 创建发票时启用去重检测
            invoice = invoice_service.create_invoice(user_id, invoice_data, skip_duplicate_check=False)
        except ValueError as e:
            # 如果是重复文件错误，记录并返回None
            if "重复" in str(e):
                db = SessionLocal()
                try:
                    logging_service.log_email_event(
                        db=db,
                        event_type="email_scan_duplicate_rejected",
                        message=f"邮件扫描文件被拒绝 - 重复: {filename}",
                        user_id=user_id,
                        details={
                            "filename": filename,
                            "relative_path": relative_file_path,
                            "error": str(e),
                            "scan_type": scan_result.get("type", "attachment")
                        },
                        log_level="WARNING"
                    )
                    db.commit()
                except Exception as log_error:
                    logger.error(f"记录重复文件拒绝日志失败: {str(log_error)}")
                finally:
                    db.close()
                # 返回标记值用于上层统计
                return "DUPLICATE"
            else:
                # 其他错误，重新抛出
                raise
        
        
        # 启动OCR识别任务（传递相对路径，让OCR任务根据运行环境转换）
        process_invoice_ocr.delay(invoice.id, relative_file_path, user_id)
        
        return invoice.id
        
    except Exception as e:
        # 记录处理失败
        db = SessionLocal()
        try:
            logging_service.log_email_event(
                db=db,
                event_type="scanned_file_processing_failed",
                message=f"处理邮件扫描文件失败: {scan_result.get('filename', 'unknown.pdf')} - {str(e)}",
                user_id=user_id,
                details={
                    "filename": scan_result.get("filename", "unknown.pdf"),
                    "error": str(e),
                    "exception_type": e.__class__.__name__,
                    "scan_type": scan_result.get("type", "attachment"),
                    "processing_duration": (datetime.now() - process_start_time).total_seconds(),
                    "temp_path": scan_result.get("file_path")
                },
                log_level="ERROR"
            )
            db.commit()
        except Exception as log_error:
            logger.error(f"记录扫描文件处理失败日志失败: {str(log_error)}")
        finally:
            db.close()
            
        logger.error(f"处理扫描文件失败: {str(e)}")
        return None


def _log_system_event(user_id: int, log_type: str, log_level: str, message: str, details: dict):
    """记录系统事件日志 - 兼容性函数，优先使用logging_service"""
    try:
        db = SessionLocal()
        
        # 优先使用logging_service
        if log_type == "email":
            logging_service.log_email_event(
                db=db,
                event_type=details.get("event_type", "legacy_log"),
                message=message,
                user_id=user_id,
                details=details,
                log_level=log_level
            )
        else:
            logging_service.log_system_event(
                db=db,
                event_type=log_type,
                message=message,
                details=details,
                log_level=log_level,
                user_id=user_id
            )
        
        db.close()
    except Exception as e:
        logger.error(f"记录系统日志失败: {str(e)}")
        
        # fallback 到原有方式
        try:
            db = SessionLocal()
            log_entry = SystemLog(
                user_id=user_id,
                log_type=log_type,
                log_level=log_level,
                message=message,
                details=details,
                resource_type="email_scan",
                created_at=datetime.now()
            )
            db.add(log_entry)
            db.commit()
            db.close()
        except Exception as e2:
            logger.error(f"记录系统日志fallback也失败: {str(e2)}")

