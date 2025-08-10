"""
日志服务 - 负责系统日志的记录和查询
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_, func
from fastapi import Request

from app.models.system_log import SystemLog
from app.models.user import User
from app.core.database import get_db


class LoggingService:
    """日志服务类"""
    
    def __init__(self):
        self.logger = logging.getLogger("app.logging_service")
        # 精简：源头已降噪。此处不再维护白名单，仅保留统一的 create_log 能力。
        self._email_info_whitelist = set()
        self._ocr_info_whitelist = set()
        self._invoice_info_whitelist = set()
    
    def create_log(
        self,
        db: Session,
        log_type: str,
        message: str,
        log_level: str = "INFO",
        user_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> SystemLog:
        """创建系统日志记录"""
        try:
            log_entry = SystemLog(
                user_id=user_id,
                log_type=log_type,
                log_level=log_level,
                message=message,
                details=details,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                created_at=datetime.now()
            )
            
            db.add(log_entry)
            db.commit()
            db.refresh(log_entry)
            
            # 记录到标准日志
            log_func = getattr(self.logger, log_level.lower(), self.logger.info)
            log_func(f"[{log_type}] {message} - User: {user_id}, Resource: {resource_type}:{resource_id}")
            
            return log_entry
            
        except Exception as e:
            self.logger.error(f"创建日志记录失败: {str(e)}")
            db.rollback()
            raise
    
    def log_auth_event(
        self,
        db: Session,
        event_type: str,
        message: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True
    ):
        """记录认证相关事件"""
        log_level = "INFO" if success else "WARNING"
        details = {
            "event_type": event_type,
            "success": success,
            "username": username
        }
        
        return self.create_log(
            db=db,
            log_type="auth",
            message=message,
            log_level=log_level,
            user_id=user_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def log_invoice_event(
        self,
        db: Session,
        event_type: str,
        message: str,
        user_id: int,
        invoice_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        log_level: str = "INFO"
    ):
        """记录发票相关事件"""
        # 精简：默认入库；若未来需降噪，请在调用源头控制
        return self.create_log(
            db=db,
            log_type="invoice",
            message=message,
            log_level=log_level,
            user_id=user_id,
            details=details,
            resource_type="invoice",
            resource_id=invoice_id
        )
    
    def log_email_event(
        self,
        db: Session,
        event_type: str,
        message: str,
        user_id: int,
        details: Optional[Dict[str, Any]] = None,
        log_level: str = "INFO"
    ):
        """记录邮箱扫描相关事件"""
        # 精简：默认入库；若未来需降噪，请在调用源头控制
        return self.create_log(
            db=db,
            log_type="email",
            message=message,
            log_level=log_level,
            user_id=user_id,
            details=details,
            resource_type="email"
        )
    
    def log_ocr_event(
        self,
        db: Session,
        event_type: str,
        message: str,
        user_id: int,
        invoice_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        log_level: str = "INFO"
    ):
        """记录OCR处理相关事件"""
        # 精简：默认入库；若未来需降噪，请在调用源头控制
        return self.create_log(
            db=db,
            log_type="ocr",
            message=message,
            log_level=log_level,
            user_id=user_id,
            details=details,
            resource_type="invoice",
            resource_id=invoice_id
        )
    
    def log_print_event(
        self,
        db: Session,
        event_type: str,
        message: str,
        user_id: int,
        details: Optional[Dict[str, Any]] = None,
        log_level: str = "INFO"
    ):
        """记录打印相关事件"""
        return self.create_log(
            db=db,
            log_type="print",
            message=message,
            log_level=log_level,
            user_id=user_id,
            details=details,
            resource_type="print"
        )
    
    def log_system_event(
        self,
        db: Session,
        event_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        log_level: str = "INFO",
        user_id: Optional[int] = None
    ):
        """记录系统级事件"""
        return self.create_log(
            db=db,
            log_type="system",
            message=message,
            log_level=log_level,
            user_id=user_id,
            details=details,
            resource_type="system"
        )
    
    def get_logs(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        log_type: Optional[str] = None,
        log_level: Optional[str] = None,
        user_id: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        search: Optional[str] = None
    ) -> tuple[List[SystemLog], int]:
        """查询系统日志"""
        try:
            query = db.query(SystemLog)
            count_query = db.query(func.count(SystemLog.id))
            
            # 构建筛选条件
            filters = []
            
            if log_type:
                filters.append(SystemLog.log_type == log_type)
            
            if log_level:
                filters.append(SystemLog.log_level == log_level)
            
            if user_id:
                # 包含用户相关的日志和系统级日志（user_id为None）
                filters.append(
                    or_(
                        SystemLog.user_id == user_id,
                        SystemLog.user_id.is_(None)
                    )
                )
            
            if date_from:
                filters.append(SystemLog.created_at >= date_from)
            
            if date_to:
                filters.append(SystemLog.created_at <= date_to)
            
            if search:
                filters.append(
                    or_(
                        SystemLog.message.contains(search),
                        SystemLog.resource_id.contains(search) if SystemLog.resource_id else False
                    )
                )
            
            # 应用筛选条件
            if filters:
                query = query.filter(and_(*filters))
                count_query = count_query.filter(and_(*filters))
            
            # 计算总数
            total = count_query.scalar()
            
            # 分页和排序
            logs = query.order_by(desc(SystemLog.id)).offset(skip).limit(limit).all()
            
            return logs, total
            
        except Exception as e:
            self.logger.error(f"查询日志失败: {str(e)}")
            raise
    
    def get_log_statistics(
        self,
        db: Session,
        days: int = 7,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """获取日志统计信息"""
        try:
            date_from = datetime.now() - timedelta(days=days)
            
            base_query = db.query(SystemLog).filter(SystemLog.created_at >= date_from)
            
            if user_id:
                base_query = base_query.filter(SystemLog.user_id == user_id)
            
            # 按日志类型统计
            type_stats = db.query(
                SystemLog.log_type,
                func.count(SystemLog.id).label('count')
            ).filter(
                SystemLog.created_at >= date_from
            )
            
            if user_id:
                type_stats = type_stats.filter(SystemLog.user_id == user_id)
            
            type_stats = type_stats.group_by(SystemLog.log_type).all()
            
            # 按日志级别统计
            level_stats = db.query(
                SystemLog.log_level,
                func.count(SystemLog.id).label('count')
            ).filter(
                SystemLog.created_at >= date_from
            )
            
            if user_id:
                level_stats = level_stats.filter(SystemLog.user_id == user_id)
            
            level_stats = level_stats.group_by(SystemLog.log_level).all()
            
            # 按日期统计
            date_stats = db.query(
                func.date(SystemLog.created_at).label('date'),
                func.count(SystemLog.id).label('count')
            ).filter(
                SystemLog.created_at >= date_from
            )
            
            if user_id:
                date_stats = date_stats.filter(SystemLog.user_id == user_id)
            
            date_stats = date_stats.group_by(func.date(SystemLog.created_at)).all()
            
            # 总计
            total_logs = base_query.count()
            error_logs = base_query.filter(SystemLog.log_level.in_(['ERROR', 'CRITICAL'])).count()
            
            return {
                "total_logs": total_logs,
                "error_logs": error_logs,
                "success_rate": round((total_logs - error_logs) / total_logs * 100, 2) if total_logs > 0 else 100,
                "by_type": [{"type": t[0], "count": t[1]} for t in type_stats],
                "by_level": [{"level": l[0], "count": l[1]} for l in level_stats],
                "by_date": [{"date": str(d[0]), "count": d[1]} for d in date_stats],
                "period_days": days
            }
            
        except Exception as e:
            self.logger.error(f"获取日志统计失败: {str(e)}")
            raise
    
    def cleanup_old_logs(self, db: Session, days_to_keep: int = 90) -> int:
        """清理旧日志记录"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            deleted_count = db.query(SystemLog).filter(
                SystemLog.created_at < cutoff_date
            ).delete()
            
            db.commit()
            
            if deleted_count > 0:
                self.log_system_event(
                    db=db,
                    event_type="cleanup",
                    message=f"清理了 {deleted_count} 条超过 {days_to_keep} 天的日志记录",
                    details={"deleted_count": deleted_count, "cutoff_date": cutoff_date.isoformat()}
                )
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"清理旧日志失败: {str(e)}")
            db.rollback()
            raise


# 全局日志服务实例
logging_service = LoggingService()


def get_client_info(request: Request) -> tuple[str, str]:
    """从请求中提取客户端信息"""
    # 获取真实IP地址（考虑代理）
    ip_address = request.headers.get("X-Forwarded-For")
    if ip_address:
        ip_address = ip_address.split(",")[0].strip()
    else:
        ip_address = request.headers.get("X-Real-IP") or request.client.host
    
    # 获取用户代理
    user_agent = request.headers.get("User-Agent", "")
    
    return ip_address, user_agent