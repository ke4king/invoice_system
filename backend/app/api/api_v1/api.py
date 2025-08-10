from fastapi import APIRouter
from app.api.api_v1.endpoints import auth, invoices, email, emails, logs, configs
from app.api.api_v1.endpoints import print as print_router

api_router = APIRouter()

# 包含各个模块的路由
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(invoices.router, prefix="/invoices", tags=["发票管理"])
api_router.include_router(email.router, prefix="/email", tags=["邮箱管理"])
api_router.include_router(emails.router, prefix="/emails", tags=["邮件列表"])
api_router.include_router(print_router.router, prefix="/print", tags=["批量打印"])
api_router.include_router(logs.router, prefix="/logs", tags=["日志管理"])
api_router.include_router(configs.router, prefix="/configs", tags=["系统配置"])