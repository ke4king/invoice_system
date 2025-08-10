"""
邮件管理API端点
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import get_current_user
from app.services.email_list_service import EmailListService
from app.schemas.email import (
    Email, EmailFilter, PaginationParams, EmailListResponse, 
    EmailStatistics, EmailBatchOperation, EmailBatchOperationResponse,
    EmailUpdate
)
from app.schemas.user import User

router = APIRouter()


@router.get("", response_model=EmailListResponse)
def get_emails(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页大小"),
    invoice_scan_status: Optional[str] = Query(None, description="发票扫描状态"),
    processing_status: Optional[str] = Query(None, description="处理状态"),
    sender: Optional[str] = Query(None, description="发送者"),
    subject: Optional[str] = Query(None, description="主题关键词"),
    has_attachments: Optional[bool] = Query(None, description="是否有附件"),
    has_invoice: Optional[bool] = Query(None, description="是否检测到发票"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取邮件列表"""
    email_service = EmailListService(db)
    
    # 构建筛选条件
    filters = EmailFilter(
        invoice_scan_status=invoice_scan_status,
        processing_status=processing_status,
        sender=sender,
        subject=subject,
        has_attachments=has_attachments,
        has_invoice=has_invoice
    ).dict(exclude_unset=True)
    
    emails, total = email_service.get_emails(
        user_id=current_user.id,
        page=page,
        size=size,
        filters=filters
    )
    
    return EmailListResponse.create(emails, total, page, size)


# 新增：POST 搜索接口，支持复杂筛选通过请求体提交
class EmailSearchRequest(BaseModel):
    page: int = 1
    size: int = 20
    invoice_scan_status: Optional[str] = None
    processing_status: Optional[str] = None
    sender: Optional[str] = None
    subject: Optional[str] = None
    has_attachments: Optional[bool] = None
    has_invoice: Optional[bool] = None


@router.post("/search", response_model=EmailListResponse)
def search_emails(
    body: EmailSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取邮件列表（POST）"""
    email_service = EmailListService(db)

    filters = EmailFilter(
        invoice_scan_status=body.invoice_scan_status,
        processing_status=body.processing_status,
        sender=body.sender,
        subject=body.subject,
        has_attachments=body.has_attachments,
        has_invoice=body.has_invoice,
    ).dict(exclude_unset=True)

    emails, total = email_service.get_emails(
        user_id=current_user.id,
        page=body.page,
        size=body.size,
        filters=filters,
    )

    return EmailListResponse.create(emails, total, body.page, body.size)


@router.get("/statistics", response_model=EmailStatistics)
def get_email_statistics(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取邮件统计信息"""
    email_service = EmailListService(db)
    statistics = email_service.get_email_statistics(current_user.id, days)
    return EmailStatistics(**statistics)


@router.get("/{email_id}", response_model=Email)
def get_email_detail(
    email_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取邮件详情"""
    email_service = EmailListService(db)
    email = email_service.get_email_detail(email_id, current_user.id)
    
    if not email:
        raise HTTPException(status_code=404, detail="邮件不存在")
    
    return email


@router.put("/{email_id}", response_model=Email)
def update_email(
    email_id: str,
    email_update: EmailUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新邮件信息"""
    email_service = EmailListService(db)
    
    # 获取邮件
    email = email_service.get_email_detail(email_id, current_user.id)
    if not email:
        raise HTTPException(status_code=404, detail="邮件不存在")
    
    # 更新扫描状态
    if email_update.invoice_scan_status:
        success = email_service.update_scan_status(
            email_id=email_id,
            user_id=current_user.id,
            scan_status=email_update.invoice_scan_status,
            invoice_count=email_update.invoice_count or 0,
            scan_result=email_update.scan_result
        )
        if not success:
            raise HTTPException(status_code=400, detail="更新扫描状态失败")
    
    # 获取更新后的邮件
    updated_email = email_service.get_email_detail(email_id, current_user.id)
    return updated_email


@router.post("/batch", response_model=EmailBatchOperationResponse)
def batch_operation(
    operation: EmailBatchOperation,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """批量操作邮件"""
    email_service = EmailListService(db)
    
    if operation.operation == "rescan":
        result = email_service.mark_emails_for_rescan(
            user_id=current_user.id,
            email_ids=operation.email_ids
        )
        message = f"标记 {result['updated']} 封邮件重新扫描"
        
    elif operation.operation == "delete":
        result = email_service.delete_emails(
            user_id=current_user.id,
            email_ids=operation.email_ids
        )
        message = f"删除 {result.get('deleted', 0)} 封邮件记录"
        
    else:
        raise HTTPException(status_code=400, detail="不支持的操作类型")
    
    return EmailBatchOperationResponse(
        success=result["success"],
        total=result["total"],
        processed=result.get("updated", result.get("deleted", 0)),
        failed=result["failed"],
        failed_details=result.get("failed_details"),
        message=message
    )


@router.get("/status/options")
def get_status_options():
    """获取状态选项"""
    return {
        "invoice_scan_status": [
            {"value": "pending", "label": "待扫描"},
            {"value": "no_invoice", "label": "无发票"},
            {"value": "has_invoice", "label": "有发票"}
        ],
        "processing_status": [
            {"value": "unprocessed", "label": "未处理"},
            {"value": "processing", "label": "处理中"},
            {"value": "completed", "label": "已完成"},
            {"value": "failed", "label": "处理失败"}
        ]
    }