"""
邮件相关的Pydantic模型
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class EmailBase(BaseModel):
    """邮件基础模型"""
    subject: Optional[str] = None
    sender: Optional[str] = None
    recipient: Optional[str] = None
    date_sent: Optional[datetime] = None
    date_received: Optional[datetime] = None
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    has_attachments: bool = False
    attachment_count: int = 0
    attachment_info: Optional[List[Dict[str, Any]]] = None


class EmailCreate(EmailBase):
    """创建邮件模型"""
    message_id: str = Field(..., description="邮件唯一标识")


class EmailUpdate(BaseModel):
    """更新邮件模型"""
    subject: Optional[str] = None
    invoice_scan_status: Optional[str] = None
    processing_status: Optional[str] = None
    invoice_count: Optional[int] = None
    scan_result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class Email(EmailBase):
    """邮件响应模型"""
    id: str
    user_id: int
    message_id: str
    invoice_scan_status: str
    invoice_count: int
    scan_result: Optional[Dict[str, Any]] = None
    processing_status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    scanned_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EmailFilter(BaseModel):
    """邮件筛选模型"""
    invoice_scan_status: Optional[str] = Field(None, description="发票扫描状态")
    processing_status: Optional[str] = Field(None, description="处理状态")
    sender: Optional[str] = Field(None, description="发送者")
    subject: Optional[str] = Field(None, description="主题关键词")
    has_attachments: Optional[bool] = Field(None, description="是否有附件")
    has_invoice: Optional[bool] = Field(None, description="是否检测到发票")
    date_from: Optional[datetime] = Field(None, description="开始日期")
    date_to: Optional[datetime] = Field(None, description="结束日期")


class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=100, description="每页大小")


class EmailListResponse(BaseModel):
    """邮件列表响应模型"""
    emails: List[Email]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def create(cls, emails: List[Email], total: int, page: int, size: int):
        pages = (total + size - 1) // size
        return cls(
            emails=emails,
            total=total,
            page=page,
            size=size,
            pages=pages
        )


class EmailStatistics(BaseModel):
    """邮件统计模型"""
    period_days: int
    total_emails: int
    emails_with_attachments: int
    emails_with_invoices: int
    emails_without_invoices: int
    total_invoices_found: int
    scan_status_breakdown: Dict[str, int]
    processing_status_breakdown: Dict[str, int]
    attachment_rate: float
    invoice_detection_rate: float


class EmailBatchOperation(BaseModel):
    """邮件批量操作模型"""
    email_ids: List[str] = Field(..., description="邮件ID列表")
    operation: str = Field(..., description="操作类型: rescan, delete")


class EmailBatchOperationResponse(BaseModel):
    """邮件批量操作响应模型"""
    success: bool
    total: int
    processed: int
    failed: int
    failed_details: Optional[List[Dict[str, Any]]] = None
    message: str