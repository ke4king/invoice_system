"""
系统监控和统计服务
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, text

from app.models.invoice import Invoice
from app.models.system_log import SystemLog
from app.models.user import User
from app.models.email_config import EmailConfig


class MonitoringService:
    """系统监控服务类"""
    
    def __init__(self):
        self.logger = logging.getLogger("app.monitoring_service")
    
    def get_dashboard_statistics(
        self,
        db: Session,
        user_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """获取仪表板统计信息"""
        try:
            date_from = datetime.now() - timedelta(days=days)
            
            # 发票统计
            invoice_stats = self._get_invoice_statistics(db, user_id, date_from)
            
            # OCR处理统计
            ocr_stats = self._get_ocr_statistics(db, user_id, date_from)
            
            # 邮箱扫描统计
            email_stats = self._get_email_statistics(db, user_id, date_from)
            
            # 系统活动统计
            activity_stats = self._get_activity_statistics(db, user_id, date_from)
            
            # 错误统计
            error_stats = self._get_error_statistics(db, user_id, date_from)
            
            return {
                "period_days": days,
                "invoice_stats": invoice_stats,
                "ocr_stats": ocr_stats,
                "email_stats": email_stats,
                "activity_stats": activity_stats,
                "error_stats": error_stats,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"获取仪表板统计失败: {str(e)}")
            raise
    
    def _get_invoice_statistics(self, db: Session, user_id: int, date_from: datetime) -> Dict[str, Any]:
        """获取发票相关统计"""
        base_query = db.query(Invoice).filter(Invoice.user_id == user_id)
        
        # 总数统计
        total_invoices = base_query.count()
        recent_invoices = base_query.filter(Invoice.created_at >= date_from).count()
        
        # 按状态统计
        status_stats = db.query(
            Invoice.status,
            func.count(Invoice.id).label('count')
        ).filter(
            and_(Invoice.user_id == user_id, Invoice.created_at >= date_from)
        ).group_by(Invoice.status).all()
        
        # 按日期统计（最近7天）
        recent_date = datetime.now() - timedelta(days=7)
        daily_stats = db.query(
            func.date(Invoice.created_at).label('date'),
            func.count(Invoice.id).label('count')
        ).filter(
            and_(
                Invoice.user_id == user_id,
                Invoice.created_at >= recent_date
            )
        ).group_by(func.date(Invoice.created_at)).all()
        
        # 金额统计
        amount_stats = db.query(
            func.sum(Invoice.total_amount).label('total'),
            func.avg(Invoice.total_amount).label('average'),
            func.max(Invoice.total_amount).label('maximum')
        ).filter(
            and_(Invoice.user_id == user_id, Invoice.created_at >= date_from)
        ).first()
        
        return {
            "total_invoices": total_invoices,
            "recent_invoices": recent_invoices,
            "by_status": [{"status": s[0], "count": s[1]} for s in status_stats],
            "daily_counts": [{"date": str(d[0]), "count": d[1]} for d in daily_stats],
            "amount_stats": {
                "total": float(amount_stats.total or 0),
                "average": float(amount_stats.average or 0),
                "maximum": float(amount_stats.maximum or 0)
            }
        }
    
    def _get_ocr_statistics(self, db: Session, user_id: int, date_from: datetime) -> Dict[str, Any]:
        """获取OCR处理统计"""
        base_query = db.query(Invoice).filter(
            and_(Invoice.user_id == user_id, Invoice.created_at >= date_from)
        )
        
        # OCR状态统计
        ocr_status_stats = db.query(
            Invoice.ocr_status,
            func.count(Invoice.id).label('count')
        ).filter(
            and_(Invoice.user_id == user_id, Invoice.created_at >= date_from)
        ).group_by(Invoice.ocr_status).all()
        
        # 计算成功率
        total_processed = base_query.filter(Invoice.ocr_status.in_(['success', 'failed'])).count()
        successful_ocr = base_query.filter(Invoice.ocr_status == 'success').count()
        success_rate = round(successful_ocr / total_processed * 100, 2) if total_processed > 0 else 0
        
        # OCR相关日志统计
        ocr_logs = db.query(func.count(SystemLog.id)).filter(
            and_(
                SystemLog.user_id == user_id,
                SystemLog.log_type == 'ocr',
                SystemLog.created_at >= date_from
            )
        ).scalar()
        
        return {
            "total_processed": total_processed,
            "successful_ocr": successful_ocr,
            "success_rate": success_rate,
            "by_status": [{"status": s[0], "count": s[1]} for s in ocr_status_stats],
            "ocr_logs_count": ocr_logs
        }
    
    def _get_email_statistics(self, db: Session, user_id: int, date_from: datetime) -> Dict[str, Any]:
        """获取邮箱扫描统计"""
        # 邮箱配置状态
        email_configs = db.query(EmailConfig).filter(EmailConfig.user_id == user_id).all()
        active_configs = [config for config in email_configs if config.is_active]
        
        # 邮箱相关日志统计
        email_logs = db.query(
            SystemLog
        ).filter(
            and_(
                SystemLog.user_id == user_id,
                SystemLog.log_type == 'email',
                SystemLog.created_at >= date_from
            )
        ).all()
        
        # 分析邮箱扫描活动
        scan_activities = [log for log in email_logs if 'scan' in log.message.lower()]
        processed_emails = [log for log in email_logs if 'processed' in log.message.lower()]
        
        # 最后扫描时间
        last_scan = None
        if scan_activities:
            last_scan = max(log.created_at for log in scan_activities).isoformat()
        
        return {
            "configured_accounts": len(email_configs),
            "active_accounts": len(active_configs),
            "scan_activities": len(scan_activities),
            "processed_emails": len(processed_emails),
            "last_scan_time": last_scan,
            "email_logs_count": len(email_logs)
        }
    
    def _get_activity_statistics(self, db: Session, user_id: int, date_from: datetime) -> Dict[str, Any]:
        """获取系统活动统计"""
        # 按类型统计活动
        activity_stats = db.query(
            SystemLog.log_type,
            func.count(SystemLog.id).label('count')
        ).filter(
            and_(
                SystemLog.user_id == user_id,
                SystemLog.created_at >= date_from
            )
        ).group_by(SystemLog.log_type).all()
        
        # 按日统计活动
        daily_activity = db.query(
            func.date(SystemLog.created_at).label('date'),
            func.count(SystemLog.id).label('count')
        ).filter(
            and_(
                SystemLog.user_id == user_id,
                SystemLog.created_at >= date_from
            )
        ).group_by(func.date(SystemLog.created_at)).all()
        
        # 最近活动
        recent_activities = db.query(SystemLog).filter(
            SystemLog.user_id == user_id
        ).order_by(desc(SystemLog.created_at)).limit(10).all()
        
        return {
            "by_type": [{"type": a[0], "count": a[1]} for a in activity_stats],
            "daily_activity": [{"date": str(d[0]), "count": d[1]} for d in daily_activity],
            "recent_activities": [
                {
                    "id": activity.id,
                    "type": activity.log_type,
                    "message": activity.message,
                    "level": activity.log_level,
                    "created_at": activity.created_at.isoformat()
                }
                for activity in recent_activities
            ]
        }
    
    def _get_error_statistics(self, db: Session, user_id: int, date_from: datetime) -> Dict[str, Any]:
        """获取错误统计"""
        # 错误日志统计
        error_logs = db.query(SystemLog).filter(
            and_(
                SystemLog.user_id == user_id,
                SystemLog.log_level.in_(['ERROR', 'CRITICAL']),
                SystemLog.created_at >= date_from
            )
        ).all()
        
        # 按类型统计错误
        error_by_type = {}
        for log in error_logs:
            error_by_type[log.log_type] = error_by_type.get(log.log_type, 0) + 1
        
        # 最近错误
        recent_errors = db.query(SystemLog).filter(
            and_(
                SystemLog.user_id == user_id,
                SystemLog.log_level.in_(['ERROR', 'CRITICAL'])
            )
        ).order_by(desc(SystemLog.created_at)).limit(5).all()
        
        return {
            "total_errors": len(error_logs),
            "by_type": [{"type": k, "count": v} for k, v in error_by_type.items()],
            "recent_errors": [
                {
                    "id": error.id,
                    "type": error.log_type,
                    "message": error.message,
                    "level": error.log_level,
                    "created_at": error.created_at.isoformat()
                }
                for error in recent_errors
            ]
        }
    
    def get_system_health(self, db: Session) -> Dict[str, Any]:
        """获取系统健康状态"""
        try:
            # 检查数据库连接（SQLAlchemy 2.0 需使用 text()）
            db.execute(text("SELECT 1"))
            db_healthy = True
            db_error = None
        except Exception as e:
            db_healthy = False
            db_error = str(e)
        
        # 获取最近的错误日志
        recent_errors = db.query(SystemLog).filter(
            and_(
                SystemLog.log_level.in_(['ERROR', 'CRITICAL']),
                SystemLog.created_at >= datetime.now() - timedelta(hours=1)
            )
        ).count()
        
        # 系统状态
        status = "healthy"
        if recent_errors > 10:
            status = "degraded"
        if recent_errors > 50 or not db_healthy:
            status = "unhealthy"
        
        return {
            "status": status,
            "database": {
                "healthy": db_healthy,
                "error": db_error
            },
            "recent_errors": recent_errors,
            "check_time": datetime.now().isoformat()
        }
    
    def get_performance_metrics(
        self,
        db: Session,
        user_id: Optional[int] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """获取性能指标"""
        try:
            date_from = datetime.now() - timedelta(hours=hours)
            
            base_filter = [SystemLog.created_at >= date_from]
            if user_id:
                base_filter.append(SystemLog.user_id == user_id)
            
            # 响应时间相关日志（如果有记录的话）
            performance_logs = db.query(SystemLog).filter(
                and_(
                    *base_filter,
                    SystemLog.details.isnot(None)
                )
            ).all()
            
            # 分析性能数据
            response_times = []
            for log in performance_logs:
                if log.details and isinstance(log.details, dict):
                    if 'response_time' in log.details:
                        response_times.append(log.details['response_time'])
            
            # 计算统计指标
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            max_response_time = max(response_times) if response_times else 0
            
            # 请求统计
            total_requests = db.query(SystemLog).filter(
                and_(*base_filter, SystemLog.log_type == 'auth')
            ).count()
            
            return {
                "period_hours": hours,
                "performance": {
                    "avg_response_time": round(avg_response_time, 3),
                    "max_response_time": round(max_response_time, 3),
                    "total_requests": total_requests,
                    "requests_per_hour": round(total_requests / hours, 2) if hours > 0 else 0
                },
                "check_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"获取性能指标失败: {str(e)}")
            raise


# 全局监控服务实例
monitoring_service = MonitoringService()