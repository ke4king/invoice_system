"""
Celery任务监控和性能分析
"""
from celery import Task
from app.workers.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.logging_service import logging_service
from app.services.monitoring_service import monitoring_service
from app.models.system_log import SystemLog
import logging
import os
from datetime import datetime, timedelta
from sqlalchemy import func, and_

# Initialize logger before it's used
logger = logging.getLogger(__name__)

# 可选导入psutil，避免在容器中缺少时阻塞整个worker
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not available, system monitoring features will be limited")


class MonitoringTask(Task):
    """监控任务基类"""
    _db = None
    
    @property
    def db(self):
        if self._db is None:
            self._db = SessionLocal()
        return self._db
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        if self._db is not None:
            self._db.close()


@celery_app.task(base=MonitoringTask, bind=True)
def collect_system_metrics(self):
    """收集系统性能指标"""
    try:
        logger.info("开始收集系统性能指标")
        
        from app.services.performance_monitoring_service import PerformanceMonitoringService
        
        performance_service = PerformanceMonitoringService(self.db)
        metrics = performance_service.collect_system_metrics()
        
        logger.info(f"系统性能指标收集完成: CPU {metrics['system']['cpu_percent']}%, 内存 {metrics['system']['memory_percent']}%")
        return metrics
        
    except Exception as exc:
        logger.error(f"收集系统性能指标失败: {str(exc)}")
        
        # 记录错误
        try:
            logging_service.log_system_event(
                db=self.db,
                event_type="system_metrics_error",
                message=f"系统性能指标收集失败: {str(exc)}",
                details={"error": str(exc)},
                log_level="ERROR"
            )
        except:
            pass
        
        return {"status": "error", "message": str(exc)}


@celery_app.task(base=MonitoringTask, bind=True)
def check_performance_alerts(self):
    """检查性能预警"""
    try:
        logger.info("开始检查性能预警")
        
        from app.services.performance_monitoring_service import PerformanceMonitoringService
        
        performance_service = PerformanceMonitoringService(self.db)
        
        # 收集当前指标
        metrics = performance_service.collect_system_metrics()
        
        # 检查预警
        alerts = performance_service.check_and_send_alerts(metrics)
        
        logger.info(f"性能预警检查完成: 触发{len(alerts)}个预警")
        return {
            "timestamp": datetime.now().isoformat(),
            "alerts_count": len(alerts),
            "alerts": alerts
        }
        
    except Exception as exc:
        logger.error(f"检查性能预警失败: {str(exc)}")
        
        # 记录错误
        try:
            logging_service.log_system_event(
                db=self.db,
                event_type="performance_alert_check_error",
                message=f"性能预警检查失败: {str(exc)}",
                details={"error": str(exc)},
                log_level="ERROR"
            )
        except:
            pass
        
        return {"status": "error", "message": str(exc)}


@celery_app.task(base=MonitoringTask, bind=True)
def generate_performance_summary(self, hours: int = 24):
    """生成性能摘要报告"""
    try:
        logger.info(f"开始生成{hours}小时性能摘要")
        
        from app.services.performance_monitoring_service import PerformanceMonitoringService
        
        performance_service = PerformanceMonitoringService(self.db)
        summary = performance_service.get_performance_summary(hours)
        
        logger.info(f"性能摘要生成完成: 性能得分 {summary['performance_score']}")
        return summary
        
    except Exception as exc:
        logger.error(f"生成性能摘要失败: {str(exc)}")
        
        # 记录错误
        try:
            logging_service.log_system_event(
                db=self.db,
                event_type="performance_summary_error",
                message=f"性能摘要生成失败: {str(exc)}",
                details={"error": str(exc), "hours": hours},
                log_level="ERROR"
            )
        except:
            pass
        
        return {"status": "error", "message": str(exc)}


@celery_app.task(base=MonitoringTask, bind=True)
def analyze_task_performance(self, hours: int = 24):
    """分析任务性能"""
    try:
        logger.info(f"开始分析最近{hours}小时的任务性能")
        
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        # 查询任务相关的日志
        task_logs = self.db.query(SystemLog).filter(
            and_(
                SystemLog.log_type.in_(['ocr', 'email', 'print']),
                SystemLog.created_at >= start_time,
                SystemLog.created_at <= end_time,
                SystemLog.details.isnot(None)
            )
        ).all()
        
        analysis = {
            "analysis_period": f"{hours} hours",
            "total_tasks": len(task_logs),
            "by_type": {},
            "performance_stats": {},
            "error_analysis": {},
            "recommendations": []
        }
        
        # 按类型分析
        type_stats = {}
        performance_data = {}
        
        for log in task_logs:
            log_type = log.log_type
            details = log.details or {}
            
            if log_type not in type_stats:
                type_stats[log_type] = {
                    "total": 0,
                    "success": 0,
                    "failed": 0,
                    "error": 0,
                    "durations": []
                }
            
            type_stats[log_type]["total"] += 1
            
            # 统计状态
            status = details.get("status", "unknown")
            if status in ["success", "completed"]:
                type_stats[log_type]["success"] += 1
            elif status in ["failed", "error"]:
                type_stats[log_type]["failed"] += 1
                if "error" in status:
                    type_stats[log_type]["error"] += 1
            
            # 收集耗时数据
            duration = details.get("duration")
            if duration and isinstance(duration, (int, float)):
                type_stats[log_type]["durations"].append(duration)
        
        # 计算性能统计
        for log_type, stats in type_stats.items():
            durations = stats["durations"]
            
            performance_stats = {
                "total_tasks": stats["total"],
                "success_rate": (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0,
                "error_rate": (stats["error"] / stats["total"] * 100) if stats["total"] > 0 else 0,
                "avg_duration": sum(durations) / len(durations) if durations else 0,
                "max_duration": max(durations) if durations else 0,
                "min_duration": min(durations) if durations else 0
            }
            
            analysis["by_type"][log_type] = performance_stats
            
            # 性能问题检测
            if performance_stats["avg_duration"] > 30:  # 平均耗时超过30秒
                analysis["recommendations"].append({
                    "type": "performance",
                    "priority": "high",
                    "message": f"{log_type}任务平均耗时过长 ({performance_stats['avg_duration']:.1f}s)",
                    "suggestions": [
                        "检查网络连接稳定性",
                        "优化处理逻辑",
                        "考虑增加超时设置"
                    ]
                })
            
            if performance_stats["error_rate"] > 10:  # 错误率超过10%
                analysis["recommendations"].append({
                    "type": "reliability",
                    "priority": "critical",
                    "message": f"{log_type}任务错误率过高 ({performance_stats['error_rate']:.1f}%)",
                    "suggestions": [
                        "检查错误原因",
                        "增加重试机制",
                        "改进错误处理"
                    ]
                })
        
        # 记录分析结果
        logging_service.log_system_event(
            db=self.db,
            event_type="task_performance_analysis",
            message=f"任务性能分析完成 - 分析了{analysis['total_tasks']}个任务",
            details=analysis
        )
        
        logger.info(f"任务性能分析完成: 分析了{analysis['total_tasks']}个任务")
        return analysis
        
    except Exception as exc:
        logger.error(f"任务性能分析失败: {str(exc)}")
        
        # 记录错误
        try:
            logging_service.log_system_event(
                db=self.db,
                event_type="task_performance_analysis_error",
                message=f"任务性能分析失败: {str(exc)}",
                details={"error": str(exc), "hours": hours},
                log_level="ERROR"
            )
        except:
            pass
        
        return {"status": "error", "message": str(exc)}


@celery_app.task(base=MonitoringTask, bind=True)
def cleanup_old_logs(self, days: int = 30):
    """清理旧日志"""
    try:
        logger.info(f"开始清理{days}天前的旧日志")
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # 查询要删除的日志数量
        old_logs_count = self.db.query(SystemLog).filter(
            SystemLog.created_at < cutoff_date
        ).count()
        
        if old_logs_count == 0:
            logger.info("没有需要清理的旧日志")
            return {"status": "completed", "deleted_count": 0}
        
        # 批量删除旧日志
        batch_size = 1000
        total_deleted = 0
        
        while True:
            batch = self.db.query(SystemLog).filter(
                SystemLog.created_at < cutoff_date
            ).limit(batch_size).all()
            
            if not batch:
                break
            
            for log in batch:
                self.db.delete(log)
            
            self.db.commit()
            total_deleted += len(batch)
            
            logger.info(f"已删除 {total_deleted}/{old_logs_count} 条旧日志")
            
            # 避免长时间占用数据库
            if len(batch) < batch_size:
                break
        
        # 记录清理结果
        logging_service.log_system_event(
            db=self.db,
            event_type="log_cleanup",
            message=f"旧日志清理完成 - 删除了{total_deleted}条记录",
            details={
                "cutoff_date": cutoff_date.isoformat(),
                "days": days,
                "deleted_count": total_deleted,
                "batch_size": batch_size
            }
        )
        
        logger.info(f"旧日志清理完成: 删除了{total_deleted}条记录")
        return {
            "status": "completed",
            "deleted_count": total_deleted,
            "cutoff_date": cutoff_date.isoformat()
        }
        
    except Exception as exc:
        logger.error(f"清理旧日志失败: {str(exc)}")
        
        # 记录错误
        try:
            logging_service.log_system_event(
                db=self.db,
                event_type="log_cleanup_error",
                message=f"旧日志清理失败: {str(exc)}",
                details={"error": str(exc), "days": days},
                log_level="ERROR"
            )
        except:
            pass
        
        return {"status": "error", "message": str(exc)}


@celery_app.task(base=MonitoringTask, bind=True)
def generate_health_report(self):
    """生成系统健康报告"""
    try:
        logger.info("开始生成系统健康报告")
        
        # 收集各种统计信息
        stats = monitoring_service.get_dashboard_stats(self.db)
        
        # 系统资源使用情况
        if PSUTIL_AVAILABLE:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
        else:
            # psutil不可用时的默认值
            cpu_percent = 0
            memory = type('obj', (object,), {'percent': 0})()
            disk = type('obj', (object,), {'used': 0, 'total': 1})()
        
        # 最近24小时的错误统计
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)
        
        recent_errors = self.db.query(SystemLog).filter(
            and_(
                SystemLog.log_level.in_(['ERROR', 'CRITICAL']),
                SystemLog.created_at >= start_time
            )
        ).count()
        
        # 生成健康评分
        health_score = 100
        issues = []
        
        # CPU使用率检查（仅在psutil可用时）
        if PSUTIL_AVAILABLE:
            if cpu_percent > 80:
                health_score -= 20
                issues.append(f"CPU使用率过高: {cpu_percent}%")
            elif cpu_percent > 60:
                health_score -= 10
                issues.append(f"CPU使用率较高: {cpu_percent}%")
        
        # 内存使用率检查（仅在psutil可用时）
        if PSUTIL_AVAILABLE:
            if memory.percent > 85:
                health_score -= 20
                issues.append(f"内存使用率过高: {memory.percent}%")
            elif memory.percent > 70:
                health_score -= 10
                issues.append(f"内存使用率较高: {memory.percent}%")
        
        # 磁盘使用率检查（仅在psutil可用时）
        if PSUTIL_AVAILABLE:
            disk_percent = (disk.used / disk.total) * 100
            if disk_percent > 90:
                health_score -= 15
                issues.append(f"磁盘使用率过高: {disk_percent:.1f}%")
            elif disk_percent > 80:
                health_score -= 8
                issues.append(f"磁盘使用率较高: {disk_percent:.1f}%")
        
        # 错误率检查
        if recent_errors > 50:
            health_score -= 25
            issues.append(f"24小时内错误过多: {recent_errors}个")
        elif recent_errors > 20:
            health_score -= 10
            issues.append(f"24小时内错误较多: {recent_errors}个")
        
        # 确定健康状态
        if health_score >= 90:
            health_status = "healthy"
        elif health_score >= 70:
            health_status = "degraded"
        else:
            health_status = "unhealthy"
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "health_score": max(0, health_score),
            "health_status": health_status,
            "system_resources": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk_percent,
                "memory_available": memory.available,
                "disk_free": disk.free
            },
            "recent_activity": {
                "recent_errors_24h": recent_errors,
                "total_logs": stats.get("activity_stats", {}).get("total_activities", 0)
            },
            "issues": issues,
            "recommendations": []
        }
        
        # 生成建议
        if health_score < 80:
            report["recommendations"].append("建议进行系统维护和优化")
        
        if cpu_percent > 70:
            report["recommendations"].append("考虑增加CPU资源或优化处理逻辑")
        
        if memory.percent > 75:
            report["recommendations"].append("考虑增加内存或检查内存泄漏")
        
        if recent_errors > 10:
            report["recommendations"].append("检查并修复导致错误的问题")
        
        # 记录健康报告
        logging_service.log_system_event(
            db=self.db,
            event_type="health_report",
            message=f"系统健康报告 - 状态: {health_status}, 评分: {health_score}",
            details=report
        )
        
        logger.info(f"系统健康报告生成完成: 状态={health_status}, 评分={health_score}")
        return report
        
    except Exception as exc:
        logger.error(f"生成系统健康报告失败: {str(exc)}")
        
        # 记录错误
        try:
            logging_service.log_system_event(
                db=self.db,
                event_type="health_report_error",
                message=f"系统健康报告生成失败: {str(exc)}",
                details={"error": str(exc)},
                log_level="ERROR"
            )
        except:
            pass
        
        return {"status": "error", "message": str(exc)}


## 定时任务改为在 celery_app.conf.beat_schedule 中集中配置
    
    # 每6小时生成一次性能摘要
    sender.add_periodic_task(
        6.0 * 60 * 60,  # 6小时
        generate_performance_summary.s(hours=6),
        name='generate performance summary every 6 hours'
    )
    
    # 每天生成一次健康报告
    sender.add_periodic_task(
        24.0 * 60 * 60,  # 24小时
        generate_health_report.s(),
        name='generate health report daily'
    )
    
    # 每周清理一次旧日志（保留30天）
    sender.add_periodic_task(
        7.0 * 24 * 60 * 60,  # 7天
        cleanup_old_logs.s(days=30),
        name='cleanup old logs weekly'
    )
    
    # 记录监控任务设置
    try:
        db = SessionLocal()
        logging_service.log_system_event(
            db=db,
            event_type="monitoring_tasks_setup",
            message="监控定时任务设置完成",
            details={
                "tasks": [
                    {"name": "collect_system_metrics", "schedule": "5 minutes"},
                    {"name": "check_performance_alerts", "schedule": "10 minutes"},
                    {"name": "analyze_task_performance", "schedule": "1 hour"},
                    {"name": "generate_performance_summary", "schedule": "6 hours"},
                    {"name": "generate_health_report", "schedule": "24 hours"},
                    {"name": "cleanup_old_logs", "schedule": "7 days"}
                ]
            }
        )
        db.close()
    except:
        pass