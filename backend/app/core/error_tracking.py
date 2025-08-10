"""
全局错误处理和堆栈跟踪中间件
"""
import logging
import traceback
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.logging_service import logging_service


class ErrorTrackingMiddleware(BaseHTTPMiddleware):
    """错误跟踪中间件"""
    
    def __init__(self, app, db_session_factory=None):
        super().__init__(app)
        self.db_session_factory = db_session_factory
        self.logger = logging.getLogger("app.error_tracking")
    
    async def dispatch(self, request: Request, call_next):
        start_time = datetime.now()
        
        try:
            response = await call_next(request)
            
            # 记录成功请求的性能指标
            if response.status_code < 400:
                processing_time = (datetime.now() - start_time).total_seconds()
                
                if processing_time > 2.0:  # 超过2秒的慢请求
                    await self._log_slow_request(request, processing_time)
            
            return response
            
        except HTTPException as http_exc:
            # 记录HTTP异常
            processing_time = (datetime.now() - start_time).total_seconds()
            await self._log_http_error(request, http_exc, processing_time)
            
            return JSONResponse(
                status_code=http_exc.status_code,
                content={
                    "error": "HTTP_ERROR",
                    "message": http_exc.detail,
                    "status_code": http_exc.status_code
                }
            )
            
        except Exception as exc:
            # 记录未捕获的异常
            processing_time = (datetime.now() - start_time).total_seconds()
            error_id = await self._log_unhandled_error(request, exc, processing_time)
            
            self.logger.error(
                f"Unhandled error in request {request.method} {request.url}: {str(exc)}",
                exc_info=True
            )
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": "INTERNAL_SERVER_ERROR",
                    "message": "服务器内部错误",
                    "error_id": error_id,
                    "timestamp": datetime.now().isoformat()
                }
            )
    
    async def _log_slow_request(self, request: Request, processing_time: float):
        """记录慢请求"""
        if not self.db_session_factory:
            return
        
        try:
            db = self.db_session_factory()
            
            ip_address = self._get_client_ip(request)
            user_agent = request.headers.get("user-agent", "")
            
            logging_service.log_system_event(
                db=db,
                event_type="slow_request",
                message=f"慢请求检测: {request.method} {request.url.path} 耗时 {processing_time:.2f}s",
                details={
                    "method": request.method,
                    "url": str(request.url),
                    "processing_time": processing_time,
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                    "query_params": dict(request.query_params),
                    "path_params": dict(request.path_params)
                },
                log_level="WARNING"
            )
            
            db.close()
            
        except Exception as e:
            self.logger.error(f"Failed to log slow request: {str(e)}")
    
    async def _log_http_error(self, request: Request, exc: HTTPException, processing_time: float):
        """记录HTTP错误"""
        if not self.db_session_factory:
            return
        
        try:
            db = self.db_session_factory()
            
            ip_address = self._get_client_ip(request)
            user_agent = request.headers.get("user-agent", "")
            
            logging_service.log_system_event(
                db=db,
                event_type="http_error",
                message=f"HTTP错误 {exc.status_code}: {request.method} {request.url.path} - {exc.detail}",
                details={
                    "method": request.method,
                    "url": str(request.url),
                    "status_code": exc.status_code,
                    "error_detail": exc.detail,
                    "processing_time": processing_time,
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                    "query_params": dict(request.query_params),
                    "path_params": dict(request.path_params)
                },
                log_level="WARNING" if exc.status_code < 500 else "ERROR"
            )
            
            db.close()
            
        except Exception as e:
            self.logger.error(f"Failed to log HTTP error: {str(e)}")
    
    async def _log_unhandled_error(self, request: Request, exc: Exception, processing_time: float) -> str:
        """记录未处理的错误"""
        error_id = f"ERR_{int(datetime.now().timestamp())}"
        
        if not self.db_session_factory:
            return error_id
        
        try:
            db = self.db_session_factory()
            
            ip_address = self._get_client_ip(request)
            user_agent = request.headers.get("user-agent", "")
            
            # 获取详细的堆栈跟踪
            exc_type, exc_value, exc_traceback = sys.exc_info()
            stack_trace = traceback.format_exception(exc_type, exc_value, exc_traceback)
            
            # 获取最近的几个调用栈帧
            recent_frames = []
            if exc_traceback:
                tb = exc_traceback
                while tb:
                    frame = tb.tb_frame
                    recent_frames.append({
                        "filename": frame.f_code.co_filename,
                        "function": frame.f_code.co_name,
                        "lineno": tb.tb_lineno,
                        "locals": {k: str(v)[:100] for k, v in frame.f_locals.items() 
                                 if not k.startswith('_') and isinstance(v, (str, int, float, bool))}
                    })
                    tb = tb.tb_next
            
            logging_service.log_system_event(
                db=db,
                event_type="unhandled_error",
                message=f"未处理异常: {exc.__class__.__name__}: {str(exc)}",
                details={
                    "error_id": error_id,
                    "error_type": exc.__class__.__name__,
                    "error_message": str(exc),
                    "method": request.method,
                    "url": str(request.url),
                    "processing_time": processing_time,
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                    "query_params": dict(request.query_params),
                    "path_params": dict(request.path_params),
                    "stack_trace": stack_trace,
                    "recent_frames": recent_frames[-5:],  # 只保留最近5个栈帧
                    "timestamp": datetime.now().isoformat()
                },
                log_level="CRITICAL"
            )
            
            db.close()
            
        except Exception as e:
            self.logger.error(f"Failed to log unhandled error: {str(e)}")
        
        return error_id
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端真实IP地址"""
        # 检查代理头
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"


class ErrorAnalyzer:
    """错误分析器"""
    
    def __init__(self, db):
        self.db = db
        self.logger = logging.getLogger("app.error_analyzer")
    
    def analyze_error_patterns(self, hours: int = 24) -> Dict[str, Any]:
        """分析错误模式"""
        try:
            from datetime import timedelta
            from sqlalchemy import func, and_
            from app.models.system_log import SystemLog
            
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            
            # 查询错误日志
            error_logs = self.db.query(SystemLog).filter(
                and_(
                    SystemLog.log_level.in_(['ERROR', 'CRITICAL']),
                    SystemLog.created_at >= start_time,
                    SystemLog.created_at <= end_time
                )
            ).all()
            
            if not error_logs:
                return {
                    "total_errors": 0,
                    "error_rate": 0,
                    "patterns": [],
                    "recommendations": []
                }
            
            # 分析错误类型
            error_types = {}
            error_sources = {}
            error_frequencies = {}
            
            for log in error_logs:
                # 错误类型统计
                log_type = log.log_type
                error_types[log_type] = error_types.get(log_type, 0) + 1
                
                # 错误来源统计
                if log.details and isinstance(log.details, dict):
                    error_type = log.details.get('error_type', 'unknown')
                    error_sources[error_type] = error_sources.get(error_type, 0) + 1
                
                # 错误频率分析（按小时）
                hour_key = log.created_at.strftime('%Y-%m-%d %H:00')
                error_frequencies[hour_key] = error_frequencies.get(hour_key, 0) + 1
            
            # 识别错误模式
            patterns = []
            
            # 高频错误
            if error_types:
                max_type = max(error_types, key=error_types.get)
                max_count = error_types[max_type]
                if max_count > len(error_logs) * 0.3:  # 超过30%
                    patterns.append({
                        "type": "high_frequency_error",
                        "description": f"{max_type} 错误频率过高",
                        "count": max_count,
                        "percentage": round(max_count / len(error_logs) * 100, 1)
                    })
            
            # 错误激增
            if len(error_frequencies) > 1:
                freq_values = list(error_frequencies.values())
                avg_freq = sum(freq_values) / len(freq_values)
                max_freq = max(freq_values)
                
                if max_freq > avg_freq * 2:  # 某小时错误数超过平均值2倍
                    max_hour = max(error_frequencies, key=error_frequencies.get)
                    patterns.append({
                        "type": "error_spike",
                        "description": f"错误激增时段: {max_hour}",
                        "count": max_freq,
                        "average": round(avg_freq, 1)
                    })
            
            # 生成建议
            recommendations = self._generate_recommendations(error_types, error_sources, patterns)
            
            return {
                "analysis_period": f"{hours} hours",
                "total_errors": len(error_logs),
                "error_rate": round(len(error_logs) / hours, 2),
                "error_types": error_types,
                "error_sources": error_sources,
                "error_frequencies": error_frequencies,
                "patterns": patterns,
                "recommendations": recommendations,
                "analysis_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"错误分析失败: {str(e)}")
            return {
                "error": str(e),
                "analysis_time": datetime.now().isoformat()
            }
    
    def _generate_recommendations(self, error_types: Dict, error_sources: Dict, patterns: list) -> list:
        """生成错误处理建议"""
        recommendations = []
        
        # 基于错误类型的建议
        if 'ocr' in error_types and error_types['ocr'] > 5:
            recommendations.append({
                "type": "ocr_optimization",
                "priority": "high",
                "description": "OCR错误频率较高，建议检查文件质量和网络连接",
                "actions": [
                    "检查上传文件的清晰度和格式",
                    "验证百度OCR API配额和网络连接",
                    "考虑增加重试机制"
                ]
            })
        
        if 'email' in error_types and error_types['email'] > 3:
            recommendations.append({
                "type": "email_optimization",
                "priority": "medium",
                "description": "邮箱扫描错误较多，建议检查邮箱配置",
                "actions": [
                    "验证邮箱服务器连接配置",
                    "检查邮箱认证信息",
                    "确认邮箱服务器稳定性"
                ]
            })
        
        # 基于错误模式的建议
        for pattern in patterns:
            if pattern["type"] == "high_frequency_error":
                recommendations.append({
                    "type": "high_frequency_fix",
                    "priority": "critical",
                    "description": f"需要紧急处理高频错误: {pattern['description']}",
                    "actions": [
                        "立即调查根本原因",
                        "实施临时缓解措施",
                        "增加监控和告警"
                    ]
                })
            
            elif pattern["type"] == "error_spike":
                recommendations.append({
                    "type": "spike_investigation",
                    "priority": "high",
                    "description": f"调查错误激增原因: {pattern['description']}",
                    "actions": [
                        "检查系统负载和资源使用情况",
                        "查看同时段的系统变更",
                        "分析用户行为模式"
                    ]
                })
        
        return recommendations


def setup_error_tracking(app, db_session_factory):
    """设置错误跟踪"""
    # 添加错误跟踪中间件
    app.add_middleware(ErrorTrackingMiddleware, db_session_factory=db_session_factory)
    
    # 设置全局异常处理器
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """全局异常处理器"""
        error_id = f"GLOBAL_ERR_{int(datetime.now().timestamp())}"
        
        logging.getLogger("app.global_error").error(
            f"Global exception caught [{error_id}]: {str(exc)}",
            exc_info=True
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "服务器内部错误",
                "error_id": error_id,
                "timestamp": datetime.now().isoformat()
            }
        )