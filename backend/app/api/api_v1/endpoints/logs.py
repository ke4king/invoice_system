"""
日志管理相关的API端点
"""
from typing import List, Optional, Dict
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException, status, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import csv
import json
import logging
from io import StringIO, BytesIO

from app.core.deps import get_current_user, get_current_active_user, get_db
from app.models.user import User
from app.models.system_log import SystemLog
from app.services.logging_service import logging_service
from app.services.monitoring_service import monitoring_service
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)


# Pydantic模型
class LogResponse(BaseModel):
    id: int
    log_type: str
    log_level: str
    message: str
    details: Optional[dict]
    resource_type: Optional[str]
    resource_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class LogListResponse(BaseModel):
    items: List[LogResponse]
    total: int
    page: int
    size: int


class LogStatisticsResponse(BaseModel):
    total_logs: int
    error_logs: int
    success_rate: float
    by_type: List[dict]
    by_level: List[dict]
    by_date: List[dict]
    period_days: int


class DashboardStatsResponse(BaseModel):
    period_days: int
    invoice_stats: dict
    ocr_stats: dict
    email_stats: dict
    activity_stats: dict
    error_stats: dict
    last_updated: str


class SystemHealthResponse(BaseModel):
    status: str
    database: dict
    recent_errors: int
    check_time: str


class PerformanceMetricsResponse(BaseModel):
    period_hours: int
    performance: dict
    check_time: str


router = APIRouter()


@router.get("/logs", response_model=LogListResponse)
async def get_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    log_type: Optional[str] = Query(None),
    log_level: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None)
):
    """获取系统日志列表"""
    try:
        skip = (page - 1) * size
        
        logs, total = logging_service.get_logs(
            db=db,
            skip=skip,
            limit=size,
            log_type=log_type,
            log_level=log_level,
            user_id=current_user.id,
            date_from=date_from,
            date_to=date_to,
            search=search
        )
        
        return LogListResponse(
            items=[LogResponse.from_orm(log) for log in logs],
            total=total,
            page=page,
            size=size
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取日志列表失败: {str(e)}"
        )


class LogSearchRequest(BaseModel):
    page: int = 1
    size: int = 20
    log_type: Optional[str] = None
    log_level: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    search: Optional[str] = None


@router.post("/logs/search", response_model=LogListResponse)
async def search_logs(
    body: LogSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取系统日志列表（POST）"""
    try:
        skip = (body.page - 1) * body.size

        logs, total = logging_service.get_logs(
            db=db,
            skip=skip,
            limit=body.size,
            log_type=body.log_type,
            log_level=body.log_level,
            user_id=current_user.id,
            date_from=body.date_from,
            date_to=body.date_to,
            search=body.search,
        )

        return LogListResponse(
            items=[LogResponse.from_orm(log) for log in logs],
            total=total,
            page=body.page,
            size=body.size,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取日志列表失败: {str(e)}",
        )

@router.get("/logs/statistics", response_model=LogStatisticsResponse)
async def get_log_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    days: int = Query(7, ge=1, le=365)
):
    """获取日志统计信息"""
    try:
        stats = logging_service.get_log_statistics(
            db=db,
            days=days,
            user_id=current_user.id
        )
        
        return LogStatisticsResponse(**stats)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取日志统计失败: {str(e)}"
        )


@router.get("/dashboard/statistics", response_model=DashboardStatsResponse)
async def get_dashboard_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    days: int = Query(30, ge=1, le=365)
):
    """获取仪表板统计信息"""
    try:
        stats = monitoring_service.get_dashboard_statistics(
            db=db,
            user_id=current_user.id,
            days=days
        )
        
        return DashboardStatsResponse(**stats)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取仪表板统计失败: {str(e)}"
        )


@router.get("/system/health", response_model=SystemHealthResponse)
async def get_system_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取系统健康状态"""
    try:
        # 只有超级用户才能查看系统健康状态
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="需要超级用户权限"
            )
        
        health = monitoring_service.get_system_health(db=db)
        
        return SystemHealthResponse(**health)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取系统健康状态失败: {str(e)}"
        )


@router.get("/system/performance", response_model=PerformanceMetricsResponse)
async def get_performance_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    hours: int = Query(24, ge=1, le=168)  # 最多7天
):
    """获取系统性能指标"""
    try:
        metrics = monitoring_service.get_performance_metrics(
            db=db,
            user_id=current_user.id,
            hours=hours
        )
        
        return PerformanceMetricsResponse(**metrics)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取性能指标失败: {str(e)}"
        )


@router.delete("/logs/cleanup")
async def cleanup_old_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    days_to_keep: int = Query(90, ge=30, le=365)
):
    """清理旧日志记录"""
    try:
        # 只有超级用户才能清理日志
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="需要超级用户权限"
            )
        
        deleted_count = logging_service.cleanup_old_logs(
            db=db,
            days_to_keep=days_to_keep
        )
        
        return {
            "message": f"成功清理了 {deleted_count} 条日志记录",
            "deleted_count": deleted_count,
            "days_kept": days_to_keep
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清理日志失败: {str(e)}"
        )


@router.get("/logs/export/csv")
async def export_logs_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    log_type: Optional[str] = Query(None),
    log_level: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(10000, ge=1, le=50000)  # 最多导出5万条
):
    """导出日志为CSV格式"""
    try:
        # 记录导出操作
        logging_service.log_system_event(
            db=db,
            user_id=current_user.id,
            event_type="log_export_started",
            message=f"开始导出CSV格式日志",
            details={
                "format": "csv",
                "filters": {
                    "log_type": log_type,
                    "log_level": log_level,
                    "date_from": date_from.isoformat() if date_from else None,
                    "date_to": date_to.isoformat() if date_to else None,
                    "search": search
                },
                "limit": limit
            }
        )
        
        # 获取日志数据
        logs, total = logging_service.get_logs(
            db=db,
            skip=0,
            limit=limit,
            log_type=log_type,
            log_level=log_level,
            user_id=current_user.id,
            date_from=date_from,
            date_to=date_to,
            search=search
        )
        
        # 创建CSV内容
        output = StringIO()
        writer = csv.writer(output)
        
        # 写入标题行
        headers = [
            'ID', '日志类型', '日志级别', '消息', '资源类型', '资源ID', 
            'IP地址', '用户代理', '创建时间', '详细信息'
        ]
        writer.writerow(headers)
        
        # 写入日志数据
        for log in logs:
            row = [
                str(log.id),
                log.log_type or '',
                log.log_level or '',
                log.message or '',
                log.resource_type or '',
                log.resource_id or '',
                log.ip_address or '',
                log.user_agent or '',
                log.created_at.strftime('%Y-%m-%d %H:%M:%S') if log.created_at else '',
                json.dumps(log.details, ensure_ascii=False) if log.details else ''
            ]
            writer.writerow(row)
        
        # 转换为字节流
        csv_content = output.getvalue()
        csv_bytes = csv_content.encode('utf-8-sig')  # 使用BOM确保Excel正确显示中文
        
        # 记录导出完成
        logging_service.log_system_event(
            db=db,
            user_id=current_user.id,
            event_type="log_export_completed",
            message=f"CSV格式日志导出完成",
            details={
                "format": "csv",
                "exported_count": len(logs),
                "total_available": total,
                "file_size": len(csv_bytes)
            }
        )
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"system_logs_{timestamp}.csv"
        
        return StreamingResponse(
            BytesIO(csv_bytes),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{filename}"
            }
        )
        
    except Exception as e:
        # 记录导出失败
        try:
            logging_service.log_system_event(
                db=db,
                user_id=current_user.id,
                event_type="log_export_failed",
                message=f"CSV格式日志导出失败: {str(e)}",
                details={
                    "format": "csv",
                    "error": str(e),
                    "exception_type": e.__class__.__name__
                },
                log_level="ERROR"
            )
        except:
            pass
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出日志失败: {str(e)}"
        )


@router.get("/logs/export/json")
async def export_logs_json(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    log_type: Optional[str] = Query(None),
    log_level: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(10000, ge=1, le=50000)  # 最多导出5万条
):
    """导出日志为JSON格式"""
    try:
        # 记录导出操作
        logging_service.log_system_event(
            db=db,
            user_id=current_user.id,
            event_type="log_export_started",
            message=f"开始导出JSON格式日志",
            details={
                "format": "json",
                "filters": {
                    "log_type": log_type,
                    "log_level": log_level,
                    "date_from": date_from.isoformat() if date_from else None,
                    "date_to": date_to.isoformat() if date_to else None,
                    "search": search
                },
                "limit": limit
            }
        )
        
        # 获取日志数据
        logs, total = logging_service.get_logs(
            db=db,
            skip=0,
            limit=limit,
            log_type=log_type,
            log_level=log_level,
            user_id=current_user.id,
            date_from=date_from,
            date_to=date_to,
            search=search
        )
        
        # 构建JSON数据
        export_data = {
            "export_info": {
                "exported_at": datetime.now().isoformat(),
                "exported_by": current_user.username,
                "total_logs": len(logs),
                "filters": {
                    "log_type": log_type,
                    "log_level": log_level,
                    "date_from": date_from.isoformat() if date_from else None,
                    "date_to": date_to.isoformat() if date_to else None,
                    "search": search
                }
            },
            "logs": []
        }
        
        # 添加日志数据
        for log in logs:
            log_data = {
                "id": log.id,
                "log_type": log.log_type,
                "log_level": log.log_level,
                "message": log.message,
                "details": log.details,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "created_at": log.created_at.isoformat() if log.created_at else None
            }
            export_data["logs"].append(log_data)
        
        # 转换为JSON字符串
        json_content = json.dumps(export_data, ensure_ascii=False, indent=2)
        json_bytes = json_content.encode('utf-8')
        
        # 记录导出完成
        logging_service.log_system_event(
            db=db,
            user_id=current_user.id,
            event_type="log_export_completed",
            message=f"JSON格式日志导出完成",
            details={
                "format": "json",
                "exported_count": len(logs),
                "total_available": total,
                "file_size": len(json_bytes)
            }
        )
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"system_logs_{timestamp}.json"
        
        return StreamingResponse(
            BytesIO(json_bytes),
            media_type="application/json; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{filename}"
            }
        )
        
    except Exception as e:
        # 记录导出失败
        try:
            logging_service.log_system_event(
                db=db,
                user_id=current_user.id,
                event_type="log_export_failed",
                message=f"JSON格式日志导出失败: {str(e)}",
                details={
                    "format": "json",
                    "error": str(e),
                    "exception_type": e.__class__.__name__
                },
                log_level="ERROR"
            )
        except:
            pass
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出日志失败: {str(e)}"
        )


@router.get("/logs/export/excel")  
async def export_logs_excel(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    log_type: Optional[str] = Query(None),
    log_level: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(10000, ge=1, le=50000)  # 最多导出5万条
):
    """导出日志为Excel格式"""
    try:
        import pandas as pd
        from datetime import datetime as dt
        
        # 记录导出操作
        logging_service.log_system_event(
            db=db,
            user_id=current_user.id,
            event_type="log_export_started",
            message=f"开始导出Excel格式日志",
            details={
                "format": "excel",
                "filters": {
                    "log_type": log_type,
                    "log_level": log_level,
                    "date_from": date_from.isoformat() if date_from else None,
                    "date_to": date_to.isoformat() if date_to else None,
                    "search": search
                },
                "limit": limit
            }
        )
        
        # 获取日志数据
        logs, total = logging_service.get_logs(
            db=db,
            skip=0,
            limit=limit,
            log_type=log_type,
            log_level=log_level,
            user_id=current_user.id,
            date_from=date_from,
            date_to=date_to,
            search=search
        )
        
        # 准备数据
        data = []
        for log in logs:
            row = {
                'ID': log.id,
                '日志类型': log.log_type or '',
                '日志级别': log.log_level or '',
                '消息': log.message or '',
                '资源类型': log.resource_type or '',
                '资源ID': log.resource_id or '',
                'IP地址': log.ip_address or '',
                '用户代理': log.user_agent or '',
                '创建时间': log.created_at.strftime('%Y-%m-%d %H:%M:%S') if log.created_at else '',
                '详细信息': json.dumps(log.details, ensure_ascii=False) if log.details else ''
            }
            data.append(row)
        
        # 创建DataFrame
        df = pd.DataFrame(data)
        
        # 创建Excel文件
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # 写入日志数据
            df.to_excel(writer, sheet_name='系统日志', index=False)
            
            # 添加统计信息表
            stats_data = {
                '统计项': ['总日志数', '导出日志数', '导出时间', '导出用户'],
                '值': [
                    str(total),
                    str(len(logs)),
                    dt.now().strftime('%Y-%m-%d %H:%M:%S'),
                    current_user.username
                ]
            }
            stats_df = pd.DataFrame(stats_data)
            stats_df.to_excel(writer, sheet_name='导出信息', index=False)
        
        output.seek(0)
        excel_bytes = output.getvalue()
        
        # 记录导出完成
        logging_service.log_system_event(
            db=db,
            user_id=current_user.id,
            event_type="log_export_completed",
            message=f"Excel格式日志导出完成",
            details={
                "format": "excel",
                "exported_count": len(logs),
                "total_available": total,
                "file_size": len(excel_bytes)
            }
        )
        
        # 生成文件名
        timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
        filename = f"system_logs_{timestamp}.xlsx"
        
        return StreamingResponse(
            BytesIO(excel_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{filename}"
            }
        )
        
    except ImportError:
        # 如果没有安装pandas或openpyxl，回退到CSV格式
        return await export_logs_csv(
            db=db, current_user=current_user, log_type=log_type,
            log_level=log_level, date_from=date_from, date_to=date_to,
            search=search, limit=limit
        )
        
    except Exception as e:
        # 记录导出失败
        try:
            logging_service.log_system_event(
                db=db,
                user_id=current_user.id,
                event_type="log_export_failed",
                message=f"Excel格式日志导出失败: {str(e)}",
                details={
                    "format": "excel",
                    "error": str(e),
                    "exception_type": e.__class__.__name__
                },
                log_level="ERROR"
            )
        except:
            pass
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出日志失败: {str(e)}"
        )


@router.get("/duplicate-statistics")
def get_duplicate_statistics(
    days: int = Query(default=30, description="统计天数"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取重复检测统计信息（精简版：基于 system_logs 直接汇总）"""
    try:
        from app.models.system_log import SystemLog
        from sqlalchemy import and_, func

        end_date = datetime.now()
        from datetime import timedelta
        start_date = end_date - timedelta(days=days)

        base = db.query(SystemLog).filter(
            and_(
                SystemLog.created_at >= start_date,
                SystemLog.created_at <= end_date,
                SystemLog.user_id == current_user.id
            )
        )

        total_duplicate = base.filter(SystemLog.message.contains("重复")).count()
        total_errors = base.filter(SystemLog.log_level == "ERROR").count()

        return {
            "period_days": days,
            "duplicates_found": total_duplicate,
            "errors": total_errors
        }
    except Exception as e:
        logger.error(f"获取重复检测统计失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取统计信息失败: {str(e)}"
        )




@router.get("/performance/current")
def get_current_performance_metrics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取当前性能指标"""
    try:
        from app.services.performance_monitoring_service import PerformanceMonitoringService
        
        performance_service = PerformanceMonitoringService(db)
        metrics = performance_service.collect_system_metrics()
        
        return metrics
        
    except Exception as e:
        logger.error(f"获取性能指标失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取性能指标失败: {str(e)}"
        )


@router.get("/performance/trends")
def get_performance_trends(
    hours: int = Query(default=24, description="分析时间范围（小时）"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取性能趋势分析"""
    try:
        from app.services.performance_monitoring_service import PerformanceMonitoringService
        
        performance_service = PerformanceMonitoringService(db)
        trends = performance_service.analyze_performance_trends(hours)
        
        return trends
        
    except Exception as e:
        logger.error(f"获取性能趋势失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取性能趋势失败: {str(e)}"
        )


@router.get("/performance/summary")
def get_performance_summary(
    hours: int = Query(default=24, description="分析时间范围（小时）"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取性能摘要"""
    try:
        from app.services.performance_monitoring_service import PerformanceMonitoringService
        
        performance_service = PerformanceMonitoringService(db)
        summary = performance_service.get_performance_summary(hours)
        
        return summary
        
    except Exception as e:
        logger.error(f"获取性能摘要失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取性能摘要失败: {str(e)}"
        )


@router.post("/performance/check-alerts")
def check_performance_alerts(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """检查性能预警"""
    try:
        from app.services.performance_monitoring_service import PerformanceMonitoringService
        
        performance_service = PerformanceMonitoringService(db)
        metrics = performance_service.collect_system_metrics()
        alerts = performance_service.check_and_send_alerts(metrics)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "alerts_count": len(alerts),
            "alerts": alerts,
            "metrics": metrics
        }
        
    except Exception as e:
        logger.error(f"检查性能预警失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"检查预警失败: {str(e)}"
        )


@router.put("/performance/thresholds")
def update_performance_thresholds(
    thresholds: Dict[str, float] = Body(..., description="新的性能阈值"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新性能监控阈值"""
    try:
        # 只有超级用户才能更新阈值
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="需要超级用户权限"
            )
        
        from app.services.performance_monitoring_service import PerformanceMonitoringService
        
        performance_service = PerformanceMonitoringService(db)
        performance_service.update_thresholds(thresholds)
        
        return {
            "message": "性能阈值更新成功",
            "updated_thresholds": thresholds,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新性能阈值失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新阈值失败: {str(e)}"
        )
