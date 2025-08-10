from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import hashlib
import os
import uuid  # 附件仍需基于UUID生成临时唯一文件名
from pathlib import Path
import tempfile
import hashlib

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.core.config import settings, get_absolute_file_path, get_relative_file_path
from app.services.invoice_service import InvoiceService
from app.schemas.invoice import (
    Invoice, InvoiceCreate, InvoiceUpdate, InvoiceFilter, 
    PaginationParams, InvoiceListResponse, InvoiceUploadResponse, OCRRetryRequest
)
from app.schemas.user import User
from app.workers.ocr_tasks import process_invoice_ocr
from app.core.metrics import EMAIL_DUPLICATES
from hashlib import md5, sha256
from pydantic import BaseModel
from sqlalchemy import func

router = APIRouter()


@router.post("/upload", response_model=InvoiceUploadResponse)
async def upload_invoice(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """上传发票文件（仅支持 PDF）"""
    # 验证文件类型
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅支持PDF文件格式"
        )
    
    # 准备存储目录（先创建目录再进行流式写入/哈希计算）
    relative_upload_dir = os.path.join("storage", "invoices", str(current_user.id))
    absolute_upload_dir = get_absolute_file_path(relative_upload_dir)
    upload_dir = Path(absolute_upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # 流式读取上传内容：同步更新哈希与大小，并写入临时文件
    md5_hasher = hashlib.md5()
    sha256_hasher = hashlib.sha256()
    total_size = 0
    temp_file = tempfile.NamedTemporaryFile(delete=False, dir=absolute_upload_dir, suffix=".upload")
    try:
        chunk_size = 1024 * 1024  # 1MB
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > settings.MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"文件大小超过限制({settings.MAX_FILE_SIZE / 1024 / 1024:.1f}MB)"
                )
            md5_hasher.update(chunk)
            sha256_hasher.update(chunk)
            temp_file.write(chunk)
    finally:
        temp_file.close()

    file_md5_hash = md5_hasher.hexdigest()
    file_sha256_hash = sha256_hasher.hexdigest()
    file_size = total_size

    # 内容寻址文件名：sha256.ext
    file_extension = Path(file.filename).suffix or ".pdf"
    new_filename = f"{file_sha256_hash}{file_extension}"

    # 绝对/相对路径
    absolute_file_path = upload_dir / new_filename
    relative_file_path = os.path.join(relative_upload_dir, new_filename)

    # 若目标已存在则跳过写入，否则将临时文件原子重命名到目标；存在则删除临时文件
    if absolute_file_path.exists():
        try:
            EMAIL_DUPLICATES.labels(type="file_store_skip").inc()
        except Exception:
            pass
        try:
            os.unlink(temp_file.name)
        except Exception:
            pass
    else:
        os.replace(temp_file.name, str(absolute_file_path))
    
    # 创建发票记录（使用相对路径）
    invoice_service = InvoiceService(db)
    invoice_data = InvoiceCreate(
        original_filename=file.filename,
        file_path=relative_file_path,
        file_size=file_size,
        file_md5_hash=file_md5_hash,
        file_sha256_hash=file_sha256_hash,
        source="manual"
    )

    try:
        invoice = invoice_service.create_invoice(current_user.id, invoice_data)
    except ValueError as e:
        msg = str(e)
        if ("重复" in msg) or ("duplicate" in msg.lower()):
            # 尝试解析已存在发票ID
            existing_id = None
            try:
                import re as _re
                m = _re.search(r"existing_invoice_id=([\w-]+)", msg)
                if m:
                    existing_id = m.group(1)
            except Exception:
                existing_id = None
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "发票文件重复，已存在相同内容的发票",
                    "error": msg,
                    "existing_invoice_id": existing_id
                }
            )
        raise
    
    # 异步处理OCR（传递相对路径，让OCR任务根据运行环境转换）
    process_invoice_ocr.delay(invoice.id, relative_file_path, current_user.id)
    
    return InvoiceUploadResponse(
        id=invoice.id,
        message="发票上传成功，正在进行OCR识别",
        status="processing"
    )


@router.get("/", response_model=InvoiceListResponse)
def get_invoices(
    status: Optional[str] = Query(None, description="发票状态筛选"),
    ocr_status: Optional[str] = Query(None, description="OCR状态筛选"),
    seller_name: Optional[str] = Query(None, description="销售方名称筛选"),
    service_type: Optional[str] = Query(None, description="消费类型筛选"),
    include_duplicates: bool = Query(False, description="是否包含重复样本"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取发票列表"""
    invoice_service = InvoiceService(db)
    
    filters = InvoiceFilter(
        status=status,
        ocr_status=ocr_status,
        seller_name=seller_name,
        service_type=service_type
    )
    
    pagination = PaginationParams(page=page, size=size)
    
    invoices, total = invoice_service.get_invoices(current_user.id, filters, pagination, include_duplicates=include_duplicates)
    
    pages = (total + size - 1) // size
    
    return InvoiceListResponse(
        items=invoices,
        total=total,
        page=page,
        size=size,
        pages=pages
    )


# 新增：POST 搜索接口，支持在请求体中提交复杂筛选条件
class InvoiceSearchRequest(BaseModel):
    status: Optional[str] = None
    ocr_status: Optional[str] = None
    seller_name: Optional[str] = None
    purchaser_name: Optional[str] = None
    service_type: Optional[str] = None
    seller_names: Optional[list[str]] = None
    purchaser_names: Optional[list[str]] = None
    service_types: Optional[list[str]] = None
    include_duplicates: bool = False
    page: int = 1
    size: int = 20


@router.post("/search", response_model=InvoiceListResponse)
def search_invoices(
    body: InvoiceSearchRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """按条件搜索发票（POST）"""
    invoice_service = InvoiceService(db)

    filters = InvoiceFilter(
        status=body.status,
        ocr_status=body.ocr_status,
        seller_name=body.seller_name,
        purchaser_name=body.purchaser_name,
        service_type=body.service_type,
        seller_names=body.seller_names,
        purchaser_names=body.purchaser_names,
        service_types=body.service_types,
    )

    pagination = PaginationParams(page=body.page, size=body.size)

    invoices, total = invoice_service.get_invoices(
        current_user.id,
        filters,
        pagination,
        include_duplicates=body.include_duplicates,
    )

    pages = (total + body.size - 1) // body.size

    return InvoiceListResponse(
        items=invoices,
        total=total,
        page=body.page,
        size=body.size,
        pages=pages,
    )


# 过滤器选项：购方、销售方、发票类型（固定集合）
SERVICE_TYPE_OPTIONS = [
    "餐饮", "电器设备", "通讯", "服务", "日用品食品", "医疗", "交通", "其他"
]


@router.get("/filters/options")
def get_invoice_filter_options(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取发票筛选器可选项（Excel 风格）"""
    # 去重查询购方/销售方
    from app.models.invoice import Invoice as InvoiceModel
    seller_rows = (
        db.query(InvoiceModel.seller_name)
        .filter(InvoiceModel.user_id == current_user.id)
        .filter(InvoiceModel.seller_name.isnot(None))
        .distinct()
        .order_by(InvoiceModel.seller_name.asc())
        .all()
    )
    purchaser_rows = (
        db.query(InvoiceModel.purchaser_name)
        .filter(InvoiceModel.user_id == current_user.id)
        .filter(InvoiceModel.purchaser_name.isnot(None))
        .distinct()
        .order_by(InvoiceModel.purchaser_name.asc())
        .all()
    )

    sellers = [row[0] for row in seller_rows if row[0]]
    purchasers = [row[0] for row in purchaser_rows if row[0]]

    return {
        "sellers": sellers,
        "purchasers": purchasers,
        "service_types": SERVICE_TYPE_OPTIONS,
    }


@router.get("/{invoice_id}", response_model=Invoice)
def get_invoice(
    invoice_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取发票详情"""
    invoice_service = InvoiceService(db)
    invoice = invoice_service.get_invoice(invoice_id, current_user.id)
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="发票不存在"
        )
    
    return invoice


@router.put("/{invoice_id}", response_model=Invoice)
def update_invoice(
    invoice_id: str,
    invoice_update: InvoiceUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新发票信息"""
    invoice_service = InvoiceService(db)
    invoice = invoice_service.update_invoice(invoice_id, current_user.id, invoice_update)
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="发票不存在"
        )
    
    return invoice


@router.post("/{invoice_id}/retry-ocr")
def retry_ocr(
    invoice_id: str,
    retry_request: OCRRetryRequest = OCRRetryRequest(),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """重试 OCR 识别"""
    invoice_service = InvoiceService(db)
    invoice = invoice_service.get_invoice(invoice_id, current_user.id)
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="发票不存在"
        )
    
    # 检查是否需要重试
    if not retry_request.force and invoice.ocr_status == "success":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="发票OCR识别已成功，无需重试"
        )
    
    # 重置OCR状态并重新处理
    invoice.ocr_status = "pending"
    invoice.ocr_error_message = None
    db.commit()
    
    # 异步处理OCR（传递存储在数据库中的相对路径）
    process_invoice_ocr.delay(invoice.id, invoice.file_path, current_user.id)
    
    return {"message": "OCR重试已启动"}


@router.delete("/{invoice_id}")
def delete_invoice(
    invoice_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """删除发票"""
    invoice_service = InvoiceService(db)
    success = invoice_service.delete_invoice(invoice_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="发票不存在"
        )
    
    return {"message": "发票删除成功"}


@router.post("/{invoice_id}/attachments")
async def add_attachment(
    invoice_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """为发票添加附件"""
    invoice_service = InvoiceService(db)
    invoice = invoice_service.get_invoice(invoice_id, current_user.id)
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="发票不存在"
        )
    
    # 验证文件大小
    file_content = await file.read()
    if len(file_content) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件大小超过限制({settings.MAX_FILE_SIZE / 1024 / 1024:.1f}MB)"
        )
    
    # 创建存储目录 - 使用相对路径存储
    relative_attachment_dir = os.path.join("storage", "attachments", str(current_user.id), invoice_id)
    absolute_attachment_dir = get_absolute_file_path(relative_attachment_dir)
    
    attachment_dir = Path(absolute_attachment_dir)
    attachment_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成唯一文件名
    file_id = str(uuid.uuid4())
    file_extension = Path(file.filename).suffix
    new_filename = f"{file_id}{file_extension}"
    
    # 绝对路径用于保存文件
    absolute_file_path = attachment_dir / new_filename
    
    # 相对路径用于存储到数据库
    relative_file_path = os.path.join(relative_attachment_dir, new_filename)
    
    # 保存文件
    with open(absolute_file_path, "wb") as buffer:
        buffer.write(file_content)
    
    # 创建附件记录（使用相对路径）
    attachment = invoice_service.add_attachment(
        invoice_id, current_user.id, file.filename, relative_file_path,
        len(file_content), file.content_type or "application/octet-stream"
    )
    
    return {"message": "附件添加成功", "attachment_id": attachment.id}


@router.get("/{invoice_id}/download")
def download_invoice(
    invoice_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """下载发票原始 PDF 文件"""
    invoice_service = InvoiceService(db)
    invoice = invoice_service.get_invoice(invoice_id, current_user.id)
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="发票不存在"
        )
    
    # 将数据库中的相对路径转换为绝对路径
    absolute_file_path = get_absolute_file_path(invoice.file_path)
    
    if not os.path.exists(absolute_file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="发票文件不存在"
        )
    
    # 返回文件响应，filename 使用原始文件名
    return FileResponse(
        path=absolute_file_path,
        media_type="application/pdf",
        filename=invoice.original_filename or f"{invoice_id}.pdf"
    )