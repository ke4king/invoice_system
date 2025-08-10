from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class PrintLayout(str, Enum):
    """打印布局枚举"""
    ONE_PER_PAGE = "1_per_page"
    TWO_PER_PAGE = "2_per_page"
    FOUR_PER_PAGE = "4_per_page"
    EIGHT_PER_PAGE = "8_per_page"  # 仅火车票支持


class InvoiceType(str, Enum):
    """发票类型枚举"""
    NORMAL = "normal"
    TRAIN_TICKET = "train_ticket"


class BatchPrintRequest(BaseModel):
    """批量打印请求模式"""
    invoice_ids: List[str] = Field(..., min_items=1, description="发票ID列表")
    layout: PrintLayout = Field(PrintLayout.FOUR_PER_PAGE, description="打印布局")
    invoice_type: InvoiceType = Field(InvoiceType.NORMAL, description="发票类型")
    show_dividers: bool = Field(True, description="是否显示分割线")
    sort_by_type: bool = Field(True, description="是否按消费类型排序")
    update_status: bool = Field(False, description="是否更新发票状态为已打印")


class PrintPreviewRequest(BaseModel):
    """打印预览请求模式"""
    invoice_ids: List[str] = Field(..., min_items=1, description="发票ID列表")
    layout: PrintLayout = Field(PrintLayout.FOUR_PER_PAGE, description="打印布局")
    invoice_type: InvoiceType = Field(InvoiceType.NORMAL, description="发票类型")
    sort_by_type: bool = Field(True, description="是否按消费类型排序")


class PrintPreviewResponse(BaseModel):
    """打印预览响应模式"""
    total_invoices: int = Field(..., description="发票总数")
    total_pages: int = Field(..., description="预计页数")
    layout_info: str = Field(..., description="布局描述")
    invoices_by_type: dict = Field(..., description="按类型分组的发票统计")


class BatchStatusUpdateRequest(BaseModel):
    """批量状态更新请求模式"""
    invoice_ids: List[str] = Field(..., min_items=1, description="发票ID列表")
    status: str = Field(..., description="目标状态")
    
    
class BatchStatusUpdateResponse(BaseModel):
    """批量状态更新响应模式"""
    updated_count: int = Field(..., description="成功更新的数量")
    failed_count: int = Field(..., description="失败的数量")
    errors: List[str] = Field(default=[], description="错误信息列表")