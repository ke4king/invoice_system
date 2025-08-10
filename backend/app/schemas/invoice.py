from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal


# 发票基础模式
class InvoiceBase(BaseModel):
    invoice_code: Optional[str] = None
    invoice_num: Optional[str] = None
    invoice_date: Optional[datetime] = None
    invoice_type: Optional[str] = None
    
    purchaser_name: Optional[str] = None
    purchaser_register_num: Optional[str] = None
    purchaser_address: Optional[str] = None
    purchaser_bank: Optional[str] = None
    
    seller_name: Optional[str] = None
    seller_register_num: Optional[str] = None
    seller_address: Optional[str] = None
    seller_bank: Optional[str] = None
    
    total_amount: Optional[Decimal] = None
    total_tax: Optional[Decimal] = None
    amount_in_words: Optional[str] = None
    amount_in_figures: Optional[Decimal] = None
    
    service_type: Optional[str] = None
    commodity_details: Optional[List[Dict[str, Any]]] = None
    source: Optional[str] = None  # manual | email


# 创建发票模式
class InvoiceCreate(InvoiceBase):
    original_filename: str
    file_path: str
    file_size: Optional[int] = None
    # 可选：预计算的文件哈希（若提供，将避免重复读取文件计算哈希）
    file_md5_hash: Optional[str] = None
    file_sha256_hash: Optional[str] = None


# 更新发票模式
class InvoiceUpdate(InvoiceBase):
    status: Optional[str] = None


# 发票响应模式
class Invoice(InvoiceBase):
    id: str
    user_id: int
    original_filename: str
    file_path: str
    file_size: Optional[int]
    status: str
    ocr_status: str
    ocr_error_message: Optional[str] = None
    ocr_raw_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# 发票列表查询参数
class InvoiceFilter(BaseModel):
    status: Optional[str] = None
    ocr_status: Optional[str] = None
    seller_name: Optional[str] = None
    purchaser_name: Optional[str] = None
    service_type: Optional[str] = None
    # 多选筛选（Excel 风格）
    seller_names: Optional[List[str]] = None
    purchaser_names: Optional[List[str]] = None
    service_types: Optional[List[str]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    amount_min: Optional[Decimal] = None
    amount_max: Optional[Decimal] = None


# 分页参数
class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)


# 发票列表响应
class InvoiceListResponse(BaseModel):
    items: List[Invoice]
    total: int
    page: int
    size: int
    pages: int


# 发票上传响应
class InvoiceUploadResponse(BaseModel):
    id: str
    message: str
    status: str = "processing"


# OCR重试请求
class OCRRetryRequest(BaseModel):
    force: bool = False  # 是否强制重试