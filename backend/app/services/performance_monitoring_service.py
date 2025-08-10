"""
性能监控和预警服务
监控系统性能指标并发送预警
"""

import time
import psutil
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.system_log import SystemLog
from app.services.logging_service import logging_service


class PerformanceMonitoringService:
    """性能监控服务"""
    
    def __init__(self, db: Session):
        self.db = db
        # 性能阈值配置
        self.thresholds = {
            "cpu_usage": 80.0,  # CPU使用率阈值
            "memory_usage": 85.0,  # 内存使用率阈值
            "disk_usage": 90.0,  # 磁盘使用率阈值
            "response_time": 2.0,  # 响应时间阈值（秒）
            "error_rate": 5.0,  # 错误率阈值（%）
            "log_growth_rate": 1000  # 日志增长率阈值（条/小时）
        }
        
        # 预警冷却时间（避免重复报警）
        self.alert_cooldown = {
            "cpu_usage": 300,  # 5分钟
            "memory_usage": 300,
            "disk_usage": 600,  # 10分钟
            "response_time": 180,  # 3分钟
            "error_rate": 300,
            "log_growth_rate": 1800  # 30分钟
        }
        
        # 最后预警时间记录
        self.last_alert_time = {}
    
    def collect_system_metrics(self) -> Dict[str, Any]:
        """收集系统性能指标"""
        start_time = time.time()
        
        try:
            # 系统资源使用情况
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # 网络IO统计
            try:
                net_io = psutil.net_io_counters()
                network_stats = {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv,
                    "packets_sent": net_io.packets_sent,
                    "packets_recv": net_io.packets_recv
                }
            except Exception:
                network_stats = None
            
            # 磁盘IO统计
            try:
                disk_io = psutil.disk_io_counters()
                disk_stats = {
                    "read_bytes": disk_io.read_bytes,
                    "write_bytes": disk_io.write_bytes,
                    "read_count": disk_io.read_count,
                    "write_count": disk_io.write_count
                } if disk_io else None
            except Exception:
                disk_stats = None
            
            # 进程信息
            try:
                process = psutil.Process()
                process_stats = {
                    "memory_percent": process.memory_percent(),
                    "cpu_percent": process.cpu_percent(),
                    "num_threads": process.num_threads(),
                    "open_files": len(process.open_files()),
                    "connections": len(process.connections())
                }
            except Exception:
                process_stats = None
            
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "collection_time": time.time() - start_time,
                "system": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_available": memory.available,
                    "memory_used": memory.used,
                    "memory_total": memory.total,
                    "disk_percent": (disk.used / disk.total) * 100,
                    "disk_free": disk.free,
                    "disk_used": disk.used,
                    "disk_total": disk.total
                },
                "network": network_stats,
                "disk_io": disk_stats,
                "process": process_stats
            }
            
            # 记录性能指标收集
            logging_service.log_system_event(
                db=self.db,
                event_type="performance_metrics_collected",
                message="系统性能指标收集完成",
                details={
                    "metrics": metrics,
                    "collection_duration": metrics["collection_time"]
                }
            )
            
            return metrics
            
        except Exception as e:
            # 记录收集失败
            logging_service.log_system_event(  
                db=self.db,
                event_type="performance_metrics_collection_failed",
                message=f"性能指标收集失败: {str(e)}",
                details={
                    "error": str(e),
                    "exception_type": e.__class__.__name__,
                    "collection_duration": time.time() - start_time  
                },
                log_level="ERROR"
            )
            raise
    
    def analyze_performance_trends(self, hours: int = 24) -> Dict[str, Any]:
        """分析性能趋势"""
        start_time = datetime.now()
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=hours)
        
        try:
            # 查询性能相关的日志
            performance_logs = self.db.query(SystemLog).filter(
                and_(
                    SystemLog.log_type == "system",
                    SystemLog.message.contains("性能指标"),
                    SystemLog.created_at >= start_date,
                    SystemLog.created_at <= end_date
                )
            ).order_by(SystemLog.created_at.desc()).all()
            
            # 分析趋势
            trends = {
                "period_hours": hours,
                "total_samples": len(performance_logs),
                "cpu_trend": [],
                "memory_trend": [],
                "disk_trend": [],
                "response_time_trend": [],
                "alerts_triggered": 0,
                "performance_score": 100
            }
            
            cpu_values = []
            memory_values = []
            disk_values = []
            
            for log in performance_logs:
                if log.details and "metrics" in log.details:
                    metrics = log.details["metrics"]
                    system_metrics = metrics.get("system", {})
                    
                    if "cpu_percent" in system_metrics:
                        cpu_values.append(system_metrics["cpu_percent"])
                        trends["cpu_trend"].append({
                            "timestamp": log.created_at.isoformat(),
                            "value": system_metrics["cpu_percent"]
                        })
                    
                    if "memory_percent" in system_metrics:
                        memory_values.append(system_metrics["memory_percent"])
                        trends["memory_trend"].append({
                            "timestamp": log.created_at.isoformat(),
                            "value": system_metrics["memory_percent"]
                        })
                    
                    if "disk_percent" in system_metrics:
                        disk_values.append(system_metrics["disk_percent"])
                        trends["disk_trend"].append({
                            "timestamp": log.created_at.isoformat(),
                            "value": system_metrics["disk_percent"]
                        })
            
            # 计算统计信息
            if cpu_values:
                trends["cpu_stats"] = {
                    "avg": sum(cpu_values) / len(cpu_values),
                    "max": max(cpu_values),
                    "min": min(cpu_values)
                }
            
            if memory_values:
                trends["memory_stats"] = {
                    "avg": sum(memory_values) / len(memory_values),
                    "max": max(memory_values),
                    "min": min(memory_values)
                }
            
            if disk_values:
                trends["disk_stats"] = {
                    "avg": sum(disk_values) / len(disk_values),
                    "max": max(disk_values),
                    "min": min(disk_values)
                }
            
            # 计算性能得分
            score_deductions = 0
            if cpu_values and max(cpu_values) > self.thresholds["cpu_usage"]:
                score_deductions += 20
            if memory_values and max(memory_values) > self.thresholds["memory_usage"]:
                score_deductions += 25
            if disk_values and max(disk_values) > self.thresholds["disk_usage"]:
                score_deductions += 15
            
            trends["performance_score"] = max(0, 100 - score_deductions)
            
            # 记录趋势分析完成
            processing_time = (datetime.now() - start_time).total_seconds()
            logging_service.log_system_event(
                db=self.db,
                event_type="performance_trend_analysis_completed",
                message=f"性能趋势分析完成 - {hours}小时内数据",
                details={
                    "period_hours": hours,
                    "samples_analyzed": len(performance_logs),
                    "performance_score": trends["performance_score"],
                    "processing_time": processing_time
                }
            )
            
            return trends
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # 记录分析失败
            logging_service.log_system_event(
                db=self.db,
                event_type="performance_trend_analysis_failed",
                message=f"性能趋势分析失败: {str(e)}",
                details={
                    "period_hours": hours,
                    "error": str(e),
                    "exception_type": e.__class__.__name__,
                    "processing_time": processing_time
                },
                log_level="ERROR"
            )
            raise
    
    def check_and_send_alerts(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检查性能指标并发送预警"""
        alerts = []
        current_time = datetime.now()
        
        try:
            system_metrics = metrics.get("system", {})
            
            # 检查CPU使用率
            cpu_percent = system_metrics.get("cpu_percent", 0)
            if cpu_percent > self.thresholds["cpu_usage"]:
                if self._should_send_alert("cpu_usage", current_time):
                    alert = self._create_alert(
                        "cpu_usage",
                        f"CPU使用率过高: {cpu_percent:.1f}%",
                        {
                            "current_value": cpu_percent,
                            "threshold": self.thresholds["cpu_usage"],
                            "severity": "high" if cpu_percent > 90 else "medium"
                        }
                    )
                    alerts.append(alert)
                    self.last_alert_time["cpu_usage"] = current_time
            
            # 检查内存使用率
            memory_percent = system_metrics.get("memory_percent", 0)
            if memory_percent > self.thresholds["memory_usage"]:
                if self._should_send_alert("memory_usage", current_time):
                    alert = self._create_alert(
                        "memory_usage",
                        f"内存使用率过高: {memory_percent:.1f}%",
                        {
                            "current_value": memory_percent,
                            "threshold": self.thresholds["memory_usage"],
                            "available_memory": system_metrics.get("memory_available", 0),
                            "severity": "high" if memory_percent > 95 else "medium"
                        }
                    )
                    alerts.append(alert)
                    self.last_alert_time["memory_usage"] = current_time
            
            # 检查磁盘使用率
            disk_percent = system_metrics.get("disk_percent", 0)
            if disk_percent > self.thresholds["disk_usage"]:
                if self._should_send_alert("disk_usage", current_time):
                    alert = self._create_alert(
                        "disk_usage",
                        f"磁盘使用率过高: {disk_percent:.1f}%",
                        {
                            "current_value": disk_percent,
                            "threshold": self.thresholds["disk_usage"],
                            "free_space": system_metrics.get("disk_free", 0),
                            "severity": "critical" if disk_percent > 95 else "high"
                        }
                    )
                    alerts.append(alert)
                    self.last_alert_time["disk_usage"] = current_time
            
            # 检查错误率
            error_rate = self._calculate_recent_error_rate()
            if error_rate > self.thresholds["error_rate"]:
                if self._should_send_alert("error_rate", current_time):
                    alert = self._create_alert(
                        "error_rate",
                        f"系统错误率过高: {error_rate:.1f}%",
                        {
                            "current_value": error_rate,
                            "threshold": self.thresholds["error_rate"],
                            "severity": "high" if error_rate > 10 else "medium"
                        }
                    )
                    alerts.append(alert)
                    self.last_alert_time["error_rate"] = current_time
            
            # 检查日志增长率
            log_growth_rate = self._calculate_log_growth_rate()
            if log_growth_rate > self.thresholds["log_growth_rate"]:
                if self._should_send_alert("log_growth_rate", current_time):
                    alert = self._create_alert(
                        "log_growth_rate",
                        f"日志增长过快: {log_growth_rate}条/小时",
                        {
                            "current_value": log_growth_rate,
                            "threshold": self.thresholds["log_growth_rate"],
                            "severity": "medium"
                        }
                    )
                    alerts.append(alert)
                    self.last_alert_time["log_growth_rate"] = current_time
            
            # 记录预警检查结果
            logging_service.log_system_event(
                db=self.db,
                event_type="performance_alert_check_completed",
                message=f"性能预警检查完成 - 触发{len(alerts)}个预警",
                details={
                    "alerts_triggered": len(alerts),
                    "metrics_checked": list(self.thresholds.keys()),
                    "alert_details": alerts
                }
            )
            
            return alerts
            
        except Exception as e:
            # 记录预警检查失败
            logging_service.log_system_event(
                db=self.db,
                event_type="performance_alert_check_failed",
                message=f"性能预警检查失败: {str(e)}",
                details={
                    "error": str(e),
                    "exception_type": e.__class__.__name__
                },
                log_level="ERROR"
            )
            return []
    
    def _should_send_alert(self, alert_type: str, current_time: datetime) -> bool:
        """判断是否应该发送预警（考虑冷却时间）"""
        if alert_type not in self.last_alert_time:
            return True
            
        last_time = self.last_alert_time[alert_type]
        cooldown_seconds = self.alert_cooldown.get(alert_type, 300)
        
        time_diff = (current_time - last_time).total_seconds()
        return time_diff >= cooldown_seconds
    
    def _create_alert(self, alert_type: str, message: str, details: Dict[str, Any]) -> Dict[str, Any]:
        """创建预警信息"""
        alert = {
            "type": alert_type,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "severity": details.get("severity", "medium"),
            "details": details
        }
        
        # 记录预警
        logging_service.log_system_event(
            db=self.db,
            event_type=f"performance_alert_{alert_type}",
            message=message,
            details=details,
            log_level="WARNING" if details.get("severity") == "medium" else "ERROR"
        )
        
        return alert
    
    def _calculate_recent_error_rate(self, minutes: int = 60) -> float:
        """计算最近的错误率"""
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=minutes)
            
            # 统计总日志数和错误日志数
            total_logs = self.db.query(SystemLog).filter(
                SystemLog.created_at >= start_time
            ).count()
            
            error_logs = self.db.query(SystemLog).filter(
                and_(
                    SystemLog.created_at >= start_time,
                    SystemLog.log_level.in_(["ERROR", "CRITICAL"])
                )
            ).count()
            
            if total_logs == 0:
                return 0.0
            
            return (error_logs / total_logs) * 100
            
        except Exception:
            return 0.0
    
    def _calculate_log_growth_rate(self, hours: int = 1) -> int:
        """计算日志增长率（条/小时）"""
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            
            log_count = self.db.query(SystemLog).filter(
                SystemLog.created_at >= start_time
            ).count()
            
            return int(log_count / hours)
            
        except Exception:
            return 0
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """获取性能摘要"""
        try:
            # 收集当前指标
            current_metrics = self.collect_system_metrics()
            
            # 分析趋势
            trends = self.analyze_performance_trends(hours)
            
            # 检查预警
            alerts = self.check_and_send_alerts(current_metrics)
            
            # 生成摘要
            summary = {
                "timestamp": datetime.now().isoformat(),
                "period_hours": hours,
                "current_metrics": current_metrics,
                "trends": trends,
                "active_alerts": alerts,
                "performance_score": trends.get("performance_score", 100),
                "health_status": self._determine_health_status(current_metrics, alerts)
            }
            
            # 记录摘要生成
            logging_service.log_system_event(
                db=self.db,
                event_type="performance_summary_generated",
                message=f"性能摘要生成完成 - 得分: {summary['performance_score']}",
                details={
                    "performance_score": summary["performance_score"],
                    "health_status": summary["health_status"],
                    "active_alerts": len(alerts),
                    "period_hours": hours
                }
            )
            
            return summary
            
        except Exception as e:
            # 记录摘要生成失败
            logging_service.log_system_event(
                db=self.db,
                event_type="performance_summary_generation_failed",
                message=f"性能摘要生成失败: {str(e)}",
                details={
                    "error": str(e),
                    "exception_type": e.__class__.__name__,
                    "period_hours": hours
                },
                log_level="ERROR"
            )
            raise
    
    def _determine_health_status(self, metrics: Dict[str, Any], alerts: List[Dict[str, Any]]) -> str:
        """确定系统健康状态"""
        if not alerts:
            return "healthy"
        
        # 检查严重程度
        critical_alerts = [a for a in alerts if a.get("details", {}).get("severity") == "critical"]
        high_alerts = [a for a in alerts if a.get("details", {}).get("severity") == "high"]
        
        if critical_alerts:
            return "critical"
        elif high_alerts:
            return "degraded"
        elif alerts:
            return "warning"
        else:
            return "healthy"
    
    def update_thresholds(self, new_thresholds: Dict[str, float]):
        """更新性能阈值"""
        try:
            old_thresholds = self.thresholds.copy()
            self.thresholds.update(new_thresholds)
            
            # 记录阈值更新
            logging_service.log_system_event(
                db=self.db,
                event_type="performance_thresholds_updated",
                message="性能监控阈值已更新",
                details={
                    "old_thresholds": old_thresholds,
                    "new_thresholds": self.thresholds,
                    "changes": new_thresholds
                }
            )
            
        except Exception as e:
            # 记录更新失败
            logging_service.log_system_event(
                db=self.db,
                event_type="performance_thresholds_update_failed",
                message=f"性能阈值更新失败: {str(e)}",
                details={
                    "error": str(e),
                    "exception_type": e.__class__.__name__,
                    "attempted_changes": new_thresholds
                },
                log_level="ERROR"
            )
            raise