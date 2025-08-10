from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Depends
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
import sys
import logging

from app.core.config import settings
from app.core.database import init_db, SessionLocal
from sqlalchemy import text
from app.core.error_tracking import setup_error_tracking
from app.api.api_v1.api import api_router
from app.services.logging_service import logging_service
from fastapi import Response
from app.core.metrics import CONTENT_TYPE_LATEST, generate_latest
from app.core.deps import get_current_user

# Configure logging with UTF-8 support
def configure_logging():
    """Configure logging system with UTF-8 encoding support"""
    # Ensure proper encoding for stdout/stderr
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
    
    # Configure basic logging
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout
    )

# Initialize logging
configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 应用启动时初始化数据库
    init_db()
    
    # 记录应用启动
    try:
        db = SessionLocal()
        logging_service.log_system_event(
            db=db,
            event_type="application_startup",
            message="发票管理系统应用启动",
            details={
                "version": "1.0.0",
                "environment": settings.ENVIRONMENT,
                "log_level": settings.LOG_LEVEL,
                "api_prefix": settings.API_V1_STR
            }
        )
        db.close()
    except Exception as e:
        logging.getLogger(__name__).warning(f"无法记录应用启动日志: {str(e)}")
    
    yield
    
    # 应用关闭时的清理
    try:
        db = SessionLocal()
        logging_service.log_system_event(
            db=db,
            event_type="application_shutdown",
            message="发票管理系统应用关闭",
            details={"version": "1.0.0"}
        )
        db.close()
    except Exception as e:
        logging.getLogger(__name__).warning(f"无法记录应用关闭日志: {str(e)}")


# 创建FastAPI应用实例
app = FastAPI(
    title="发票管理系统",
    description="发票自动归集与管理系统API",
    version="1.0.0",
    lifespan=lifespan
)

# 设置错误跟踪中间件
setup_error_tracking(app, SessionLocal)

# 配置CORS（避免 * 与凭据同用）
allowed_origins = settings.ALLOWED_HOSTS or []
allow_credentials = True
if "*" in allowed_origins:
    allow_credentials = False
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 出于安全考虑，不直接公开 /storage 目录。请通过受鉴权的下载接口访问文件。

# 包含API路由
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    return {"message": "发票管理系统API", "version": "1.0.0", "status": "running"}


@app.get("/health")
async def health_check(current_user=Depends(get_current_user) if settings.HEALTH_REQUIRE_AUTH else None):
    """基础健康检查端点"""
    try:
        # 检查数据库连接（SQLAlchemy 2.0 需使用 text()）
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        
        from datetime import datetime
        return {
            "status": "healthy",
            "database": "connected",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        from datetime import datetime
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat()
        }


@app.get("/health/detailed")
async def detailed_health_check(current_user=Depends(get_current_user) if settings.HEALTH_REQUIRE_AUTH else None):
    """详细健康检查端点"""
    from datetime import datetime
    import psutil
    
    try:
        health_info = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "services": {},
            "system": {}
        }
        
        # 检查数据库连接
        try:
            db = SessionLocal()
            db.execute(text("SELECT 1"))
            
            # 获取日志统计
            from app.models.system_log import SystemLog
            log_count = db.query(SystemLog).count()
            
            health_info["services"]["database"] = {
                "status": "healthy",
                "total_logs": log_count
            }
            db.close()
        except Exception as e:
            health_info["services"]["database"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_info["status"] = "degraded"
        
        # 检查系统资源
        try:
            health_info["system"] = {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent
            }
        except Exception as e:
            health_info["system"] = {"error": str(e)}
        
        # 记录健康检查（避免未鉴权泄露敏感信息，仅记录摘要）
        try:
            db = SessionLocal()
            logging_service.log_system_event(
                db=db,
                event_type="health_check",
                message="执行详细健康检查",
                details={"status": health_info.get("status"), "services": list(health_info.get("services", {}).keys())}
            )
            db.close()
        except Exception:
            pass
        
        return health_info
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        }


@app.get("/api/status")
async def api_status():
    """API状态信息"""
    from datetime import datetime
    
    try:
        db = SessionLocal()
        
        # 获取最近的统计信息
        from app.services.monitoring_service import monitoring_service
        stats = monitoring_service.get_dashboard_stats(db, days=1)
        
        db.close()
        
        return {
            "api_version": "1.0.0",
            "status": "operational",
            "timestamp": datetime.now().isoformat(),
            "statistics": {
                "total_logs": stats.get("activity_stats", {}).get("total_activities", 0),
                "recent_errors": stats.get("error_stats", {}).get("total_errors", 0),
                "active_users": len(stats.get("activity_stats", {}).get("by_user", [])),
                "invoice_count": stats.get("invoice_stats", {}).get("total_invoices", 0)
            }
        }
        
    except Exception as e:
        from datetime import datetime
        return {
            "api_version": "1.0.0",
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@app.get("/metrics")
async def metrics():
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)