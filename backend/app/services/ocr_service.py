import requests
import json
import base64
import traceback
import os
import time
from collections import deque
from typing import Dict, Any, Optional
from datetime import datetime
from app.core.config import settings, get_absolute_file_path
import redis
from app.core.metrics import OCR_REQUESTS_TOTAL, OCR_DURATION_SECONDS
from app.services.logging_service import logging_service
from sqlalchemy.orm import Session
from app.models.ocr_cache import OCRCache
import logging

logger = logging.getLogger(__name__)


class OCRService:
    """百度OCR服务类"""
    
    def __init__(self, db: Session = None):
        self.api_key = settings.BAIDU_OCR_API_KEY
        self.secret_key = settings.BAIDU_OCR_SECRET_KEY
        self.access_token = None
        self.db = db
        # 进程内QPS限流（2次/秒，OCR配额QPS=2）
        self._qps_recent_calls = deque()
    
    def _wait_for_qps_limit(self):
        """进程内限流：确保QPS不超过2（每秒最多2次）。"""
        now = time.monotonic()
        # 清理1秒窗口之外的时间戳
        while self._qps_recent_calls and (now - self._qps_recent_calls[0]) > 1.0:
            self._qps_recent_calls.popleft()

        if len(self._qps_recent_calls) >= 2:
            # 需要等待到最早一次调用超过1秒
            wait_seconds = 1.0 - (now - self._qps_recent_calls[0]) + 0.01
            if wait_seconds > 0:
                logger.debug(f"OCR QPS限制：等待 {wait_seconds:.2f} 秒")
                time.sleep(wait_seconds)
            # 再次清理并记录
            now = time.monotonic()
            while self._qps_recent_calls and (now - self._qps_recent_calls[0]) > 1.0:
                self._qps_recent_calls.popleft()

        self._qps_recent_calls.append(time.monotonic())

    def _acquire_distributed_qps_token(self, limit_per_sec: int = None) -> None:
        """分布式全局1秒窗口限流，基于Redis计数。
        超过限制时，短暂sleep并重试，带抖动以减少惊群。
        """
        try:
            limit = limit_per_sec or settings.OCR_QPS_LIMIT or 2
            if limit <= 0:
                return
            r = redis.from_url(settings.REDIS_URL)
            epoch = int(time.time())
            key = f"rate:ocr:baidu:{epoch}"
            pipe = r.pipeline()
            pipe.incr(key, 1)
            pipe.expire(key, 2)
            cnt, _ = pipe.execute()
            if cnt and int(cnt) > int(limit):
                # 计算需要等待到下一秒的时间，加 10-60ms 抖动
                now = time.time()
                wait = (epoch + 1) - now
                if wait < 0:
                    wait = 0.05
                jitter = 0.01 + (now % 0.05)  # 10-60ms 之间
                time.sleep(max(0.0, wait + jitter))
        except Exception:
            # Redis 不可用时，回退到仅进程内限流
            return
    
    def get_access_token(self) -> Optional[str]:
        """获取百度OCR访问令牌"""
        if not self.api_key or not self.secret_key:
            error_msg = f"百度OCR API密钥未配置 - API_KEY: {'已设置' if self.api_key else '未设置'}, SECRET_KEY: {'已设置' if self.secret_key else '未设置'}"
            logger.error(error_msg)
            return None
        
        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.secret_key
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if "access_token" in result:
                self.access_token = result["access_token"]
                return self.access_token
            else:
                logger.error(f"获取访问令牌失败: {result}")
                return None
                
        except Exception as e:
            logger.error(f"获取百度OCR访问令牌异常: {str(e)}")
            return None
    
    def recognize_invoice(self, file_path: str, user_id: int = None, invoice_id: str = None) -> Dict[str, Any]:
        """识别PDF格式的增值税发票"""
        ocr_start_time = datetime.now()
        
        # 先不记录开始日志（降噪），接下来将尝试OCR缓存
        
        if not self.access_token:
            if not self.get_access_token():
                error_result = {"error_code": -1, "error_msg": "无法获取访问令牌"}
                
                if self.db and user_id:
                    logging_service.log_ocr_event(
                        db=self.db,
                        event_type="ocr_failed",
                        message="OCR识别失败: 无法获取百度API访问令牌",
                        user_id=user_id,
                        invoice_id=invoice_id,
                        details={
                            "error": "access_token_failed",
                            "file_path": file_path
                        },
                        log_level="ERROR"
                    )
                
                return error_result
        
        try:
            # 确保路径转换为当前环境的绝对路径
            if not os.path.isabs(file_path):
                # 相对路径，根据当前环境的UPLOAD_DIR转换
                file_path = get_absolute_file_path(file_path)
                logger.debug(f"相对路径转换为绝对路径: {file_path}")
            else:
                # 已经是绝对路径
                logger.debug(f"接收到绝对路径: {file_path}")
            logger.debug(f"最终OCR文件路径: {file_path}")
            logger.debug(f"当前环境UPLOAD_DIR: {os.getenv('UPLOAD_DIR', 'not set')}")
            # 检查文件是否存在
            if not os.path.exists(file_path):
                error_msg = f"OCR文件不存在: {file_path}"
                logger.error(error_msg)
                
                error_result = {"error_code": -2, "error_msg": error_msg}
                
                if self.db and user_id:
                    logging_service.log_ocr_event(
                        db=self.db,
                        event_type="ocr_file_not_found",
                        message=error_msg,
                        user_id=user_id,
                        invoice_id=invoice_id,
                        details={
                            "file_path": file_path,
                            "error": "file_not_found"
                        },
                        log_level="ERROR"
                    )
                
                return error_result
            
            # 读取PDF文件并转换为base64，同时计算哈希（供OCR缓存）
            # 如果传入相对路径，转换为绝对路径
            file_path_to_read = file_path
            try:
                import os as _os
                if not _os.path.isabs(file_path_to_read):
                    file_path_to_read = get_absolute_file_path(file_path_to_read)
            except Exception:
                pass
            with open(file_path_to_read, "rb") as f:
                file_data = f.read()
            try:
                import hashlib as _hashlib
                file_sha256 = _hashlib.sha256(file_data).hexdigest()
            except Exception:
                file_sha256 = None
            
            file_size = len(file_data)
            file_base64 = base64.b64encode(file_data).decode('utf-8')
            

            # OCR 结果复用优先级：1) invoices 表中已有同 sha256 的成功结果 2) OCR 缓存表
            if self.db and file_sha256:
                try:
                    from app.models.invoice import Invoice
                    existing_invoice = (
                        self.db.query(Invoice)
                        .filter(Invoice.file_sha256_hash == file_sha256, Invoice.ocr_status == 'success')
                        .first()
                    )
                    if existing_invoice and isinstance(existing_invoice.ocr_raw_data, dict):
                        OCR_REQUESTS_TOTAL.labels(result="reused_invoice").inc()
                        OCR_DURATION_SECONDS.labels(result="reused_invoice").observe((datetime.now() - ocr_start_time).total_seconds())
                        return existing_invoice.ocr_raw_data
                except Exception:
                    pass
                try:
                    cache = self.db.query(OCRCache).filter(OCRCache.sha256 == file_sha256).first()
                    if cache and cache.status == 'success' and cache.ocr_json:
                        OCR_REQUESTS_TOTAL.labels(result="cache_hit").inc()
                        OCR_DURATION_SECONDS.labels(result="cache_hit").observe((datetime.now() - ocr_start_time).total_seconds())
                        return cache.ocr_json
                except Exception:
                    pass

            # 调用百度OCR增值税发票识别API
            url = "https://aip.baidubce.com/rest/2.0/ocr/v1/vat_invoice"
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            params = {
                "access_token": self.access_token
            }
            
            # 处理PDF文件参数
            data = {
                "pdf_file": file_base64
            }
            
            # QPS限制：分布式全局 + 本地双限流
            self._acquire_distributed_qps_token(settings.OCR_QPS_LIMIT)
            self._wait_for_qps_limit()
            
            api_call_time = datetime.now()
            response = requests.post(
                url, 
                headers=headers, 
                params=params, 
                data=data,
                timeout=settings.OCR_TIMEOUT
            )
            response.raise_for_status()
            
            api_response_time = datetime.now()
            response_time = (api_response_time - api_call_time).total_seconds()
            
            result = response.json()
            
            # 检查OCR响应
            if "error_code" in result:
                error_msg = f"OCR API错误: {result.get('error_msg', 'Unknown error')}"
                try:
                    # 明确记录服务商限流错误码（如 18）
                    if int(result.get("error_code", -1)) == 18:
                        logger.warning("检测到OCR服务商QPS超限(error_code=18)")
                except Exception:
                    pass
                
                if self.db and user_id:
                    logging_service.log_ocr_event(
                        db=self.db,
                        event_type="ocr_api_error",
                        message=error_msg,
                        user_id=user_id,
                        invoice_id=invoice_id,
                        details={
                            "error_code": result.get("error_code"),
                            "error_msg": result.get("error_msg"),
                            "file_path": file_path,
                            "response_time": response_time,
                            "api_response": result
                        },
                        log_level="ERROR"
                    )
                
                return result
            
            # 验证OCR响应格式
            words_result = result.get("words_result", {})
            
            # 检查是否有有效的识别结果
            if not words_result:
                error_msg = "OCR识别结果为空"
                
                if self.db and user_id:
                    logging_service.log_ocr_event(
                        db=self.db,
                        event_type="ocr_empty_result",
                        message=error_msg,
                        user_id=user_id,
                        invoice_id=invoice_id,
                        details={
                            "file_path": file_path,
                            "api_response": result,
                            "response_time": response_time
                        },
                        log_level="WARNING"
                    )
                
                return {
                    "error_code": -6,
                    "error_msg": error_msg
                }
            
            # OCR成功
            total_duration = (datetime.now() - ocr_start_time).total_seconds()
            
            if self.db and user_id:
                # 解析识别结果统计：兼容多种值结构
                recognized_fields = []
                for key, value in words_result.items():
                    v = value
                    try:
                        if isinstance(v, dict):
                            if v.get("words") or v.get("word"):
                                recognized_fields.append(key)
                        elif isinstance(v, list):
                            if len(v) > 0:
                                recognized_fields.append(key)
                        elif isinstance(v, str):
                            if v.strip():
                                recognized_fields.append(key)
                        elif v:
                            recognized_fields.append(key)
                    except Exception:
                        pass
                
                logging_service.log_ocr_event(
                    db=self.db,
                    event_type="ocr_success",
                    message=f"OCR识别成功，识别出 {len(recognized_fields)} 个字段",
                    user_id=user_id,
                    invoice_id=invoice_id,
                    details={
                        "file_path": file_path,
                        "file_size": file_size,
                        "response_time": response_time,
                        "total_duration": total_duration,
                        "recognized_fields": recognized_fields,
                        "fields_count": len(recognized_fields),
                        "api_response": result
                    }
                )
            # 写入 OCR 缓存
            if self.db and file_sha256 and isinstance(result, dict):
                try:
                    cache = self.db.query(OCRCache).filter(OCRCache.sha256 == file_sha256).first()
                    if cache:
                        cache.status = 'success'
                        cache.ocr_json = result
                        cache.updated_at = datetime.now()
                    else:
                        cache = OCRCache(sha256=file_sha256, status='success', ocr_json=result)
                        self.db.add(cache)
                    self.db.commit()
                except Exception:
                    self.db.rollback()
                    pass
            try:
                OCR_REQUESTS_TOTAL.labels(result="success").inc()
                OCR_DURATION_SECONDS.labels(result="success").observe(total_duration)
            except Exception:
                pass

            return result
            
        except requests.exceptions.Timeout:
            error_msg = f"OCR请求超时: {file_path}"
            logger.error(error_msg)
            
            if self.db and user_id:
                logging_service.log_ocr_event(
                    db=self.db,
                    event_type="ocr_timeout",
                    message=error_msg,
                    user_id=user_id,
                    invoice_id=invoice_id,
                    details={
                        "file_path": file_path,
                        "timeout": settings.OCR_TIMEOUT,
                        "duration": (datetime.now() - ocr_start_time).total_seconds()
                    },
                    log_level="ERROR"
                )
            
            return {"error_code": -2, "error_msg": "请求超时"}
            
        except requests.exceptions.RequestException as e:
            error_msg = f"OCR网络请求失败: {str(e)}"
            logger.error(error_msg)
            
            if self.db and user_id:
                logging_service.log_ocr_event(
                    db=self.db,
                    event_type="ocr_network_error",
                    message=error_msg,
                    user_id=user_id,
                    invoice_id=invoice_id,
                    details={
                        "file_path": file_path,
                        "error": str(e),
                        "traceback": traceback.format_exc(),
                        "duration": (datetime.now() - ocr_start_time).total_seconds()
                    },
                    log_level="ERROR"
                )
            
            return {"error_code": -3, "error_msg": f"网络请求失败: {str(e)}"}
            
        except FileNotFoundError:
            error_msg = f"OCR文件不存在: {file_path}"
            logger.error(error_msg)
            
            if self.db and user_id:
                logging_service.log_ocr_event(
                    db=self.db,
                    event_type="ocr_file_not_found",
                    message=error_msg,
                    user_id=user_id,
                    invoice_id=invoice_id,
                    details={
                        "file_path": file_path
                    },
                    log_level="ERROR"
                )
            
            return {"error_code": -4, "error_msg": "文件不存在"}
            
        except Exception as e:
            error_msg = f"OCR识别异常: {str(e)}"
            logger.error(error_msg)
            
            if self.db and user_id:
                logging_service.log_ocr_event(
                    db=self.db,
                    event_type="ocr_exception",
                    message=error_msg,
                    user_id=user_id,
                    invoice_id=invoice_id,
                    details={
                        "file_path": file_path,
                        "error": str(e),
                        "traceback": traceback.format_exc(),
                        "duration": (datetime.now() - ocr_start_time).total_seconds()
                    },
                    log_level="ERROR"
                )
            
            return {"error_code": -5, "error_msg": f"识别异常: {str(e)}"}
