from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
from io import BytesIO
import logging
from datetime import datetime

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.services.print_service import PrintService, PrintOptions
from app.services.invoice_service import InvoiceService
from app.services.logging_service import logging_service
from app.schemas.print import (
    BatchPrintRequest, PrintPreviewRequest, PrintPreviewResponse,
    BatchStatusUpdateRequest, BatchStatusUpdateResponse, PrintLayout, InvoiceType
)
from app.schemas.user import User

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/preview", response_model=PrintPreviewResponse)
def preview_batch_print(
    preview_request: PrintPreviewRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """预览批量打印"""
    try:
        invoice_service = InvoiceService(db)
        print_service = PrintService(db)
        
        # 获取发票列表
        invoices = []
        for invoice_id in preview_request.invoice_ids:
            invoice = invoice_service.get_invoice(invoice_id, current_user.id)
            if invoice:
                invoices.append(invoice)
        
        if not invoices:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="没有找到有效的发票"
            )
        
        # 按类型排序（如果需要）
        if preview_request.sort_by_type:
            invoices = print_service._sort_invoices_by_type(invoices)
        
        # 验证布局和发票类型组合
        if (preview_request.layout == PrintLayout.EIGHT_PER_PAGE and 
            preview_request.invoice_type != InvoiceType.TRAIN_TICKET):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="每页8张布局仅支持火车票类型"
            )
        
        # 计算页数 - 使用新的映射方式
        layout_mapping = {
            PrintLayout.ONE_PER_PAGE: 1,
            PrintLayout.TWO_PER_PAGE: 2,
            PrintLayout.FOUR_PER_PAGE: 4,
            PrintLayout.EIGHT_PER_PAGE: 8
        }
        invoices_per_page = layout_mapping[preview_request.layout]
        total_pages = (len(invoices) + invoices_per_page - 1) // invoices_per_page
        
        # 统计按类型分组的发票
        invoices_by_type = {}
        for invoice in invoices:
            service_type = invoice.service_type or "未分类"
            if service_type not in invoices_by_type:
                invoices_by_type[service_type] = 0
            invoices_by_type[service_type] += 1
        
        # 布局描述
        layout_descriptions = {
            PrintLayout.ONE_PER_PAGE: "1张/页",
            PrintLayout.TWO_PER_PAGE: "2张/页", 
            PrintLayout.FOUR_PER_PAGE: "4张/页",
            PrintLayout.EIGHT_PER_PAGE: "8张/页"
        }
        layout_info = layout_descriptions.get(preview_request.layout, "未知布局")
        
        return PrintPreviewResponse(
            total_invoices=len(invoices),
            total_pages=total_pages,
            layout_info=f"{layout_info}，共需{total_pages}页纸",
            invoices_by_type=invoices_by_type
        )
        
    except Exception as e:
        logger.error(f"预览批量打印失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"预览失败: {str(e)}"
        )


@router.post("/generate")
def generate_batch_print(
    print_request: BatchPrintRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """生成批量打印PDF"""
    start_time = datetime.now()
    
    try:
        # 记录打印开始
        logging_service.log_print_event(
            db=db,
            user_id=current_user.id,
            event_type="batch_print_started",
            message=f"开始批量打印 - {len(print_request.invoice_ids)}个发票",
            details={
                "invoice_ids": print_request.invoice_ids,
                "layout": print_request.layout.value,
                "invoice_type": print_request.invoice_type.value,
                "show_dividers": print_request.show_dividers,
                "sort_by_type": print_request.sort_by_type,
                "update_status": print_request.update_status
            }
        )
        
        invoice_service = InvoiceService(db)
        print_service = PrintService(db)
        
        # 获取发票列表
        invoices = []
        missing_invoices = []
        
        for invoice_id in print_request.invoice_ids:
            invoice = invoice_service.get_invoice(invoice_id, current_user.id)
            if invoice:
                invoices.append(invoice)
            else:
                missing_invoices.append(invoice_id)
        
        if missing_invoices:
            # 记录缺失的发票
            logging_service.log_print_event(
                db=db,
                user_id=current_user.id,
                event_type="batch_print_missing_invoices",
                message=f"批量打印中发现缺失的发票",
                details={"missing_invoice_ids": missing_invoices},
                log_level="WARNING"
            )
        
        if not invoices:
            # 记录失败
            logging_service.log_print_event(
                db=db,
                user_id=current_user.id,
                event_type="batch_print_no_valid_invoices",
                message="批量打印失败 - 没有找到有效的发票",
                details={"requested_ids": print_request.invoice_ids},
                log_level="ERROR"
            )
            
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="没有找到有效的发票"
            )
        
        # 创建打印选项 - 验证布局和发票类型组合
        if (print_request.layout == PrintLayout.EIGHT_PER_PAGE and 
            print_request.invoice_type != InvoiceType.TRAIN_TICKET):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="每页8张布局仅支持火车票类型"
            )
            
        options = PrintOptions(
            layout=print_request.layout,
            invoice_type=print_request.invoice_type.value,
            show_dividers=print_request.show_dividers,
            sort_by_type=print_request.sort_by_type
        )
        
        # 生成PDF - 使用统一的高效方法
        pdf_data = print_service.generate_pdf(
            invoices, options, 
            user_id=current_user.id
        )
        
        # 更新发票状态（如果需要）
        updated_invoices = []
        failed_updates = []
        
        if print_request.update_status:
            for invoice in invoices:
                try:
                    success = invoice_service.update_invoice(
                        invoice.id, 
                        current_user.id, 
                        {"status": "printed"}
                    )
                    if success:
                        updated_invoices.append(invoice.id)
                    else:
                        failed_updates.append(invoice.id)
                except Exception as e:
                    logger.warning(f"Failed to update invoice status: {invoice.id}, {str(e)}")
                    failed_updates.append(invoice.id)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # 记录成功完成
        logging_service.log_print_event(
            db=db,
            user_id=current_user.id,
            event_type="batch_print_completed",
            message=f"批量打印成功生成 - {len(invoices)}个发票",
            details={
                "total_invoices": len(invoices),
                "successful_invoices": len(invoices),
                "missing_invoices": len(missing_invoices),
                "updated_invoices": len(updated_invoices),
                "failed_updates": len(failed_updates),
                "layout": print_request.layout.value,
                "pdf_size": len(pdf_data),
                "processing_time": processing_time
            }
        )
        
        # 创建文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"batch_print_{timestamp}.pdf"
        
        # 返回PDF流
        return StreamingResponse(
            BytesIO(pdf_data),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{filename}"
            }
        )
        
    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"Failed to generate batch print PDF: {str(e)}")
        
        # 记录错误
        logging_service.log_print_event(
            db=db,
            user_id=current_user.id,
            event_type="batch_print_error",
            message=f"批量打印失败: {str(e)}",
            details={
                "invoice_ids": print_request.invoice_ids,
                "error": str(e),
                "processing_time": processing_time,
                "exception_type": e.__class__.__name__
            },
            log_level="ERROR"
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF: {str(e)}"
        )


@router.post("/update-status", response_model=BatchStatusUpdateResponse)
def batch_update_status(
    update_request: BatchStatusUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """批量更新发票状态"""
    start_time = datetime.now()
    
    try:
        # 记录操作开始
        logging_service.log_print_event(
            db=db,
            user_id=current_user.id,
            event_type="batch_status_update_started",
            message=f"开始批量更新发票状态 - {len(update_request.invoice_ids)}个发票到'{update_request.status}'",
            details={
                "invoice_ids": update_request.invoice_ids,
                "target_status": update_request.status
            }
        )
        
        invoice_service = InvoiceService(db)
        
        updated_count = 0
        failed_count = 0
        errors = []
        successful_updates = []
        
        for invoice_id in update_request.invoice_ids:
            try:
                # 检查发票是否存在且属于当前用户
                invoice = invoice_service.get_invoice(invoice_id, current_user.id)
                if not invoice:
                    failed_count += 1
                    error_msg = f"发票 {invoice_id} 不存在"
                    errors.append(error_msg)
                    
                    # 记录单个失败
                    logging_service.log_print_event(
                        db=db,
                        user_id=current_user.id,
                        event_type="status_update_not_found",
                        message=error_msg,
                        details={
                            "invoice_id": invoice_id,
                            "target_status": update_request.status
                        },
                        log_level="WARNING"
                    )
                    continue
                
                # 记录状态变更前的信息
                old_status = invoice.status
                
                # 更新状态
                success = invoice_service.update_invoice(
                    invoice_id,
                    current_user.id,
                    {"status": update_request.status}
                )
                
                if success:
                    updated_count += 1
                    successful_updates.append({
                        "invoice_id": invoice_id,
                        "old_status": old_status,
                        "new_status": update_request.status
                    })
                    
                    # 记录成功更新
                    logging_service.log_print_event(
                        db=db,
                        user_id=current_user.id,
                        event_type="status_updated",
                        message=f"发票状态更新成功: {invoice_id} 从 '{old_status}' 变为 '{update_request.status}'",
                        details={
                            "invoice_id": invoice_id,
                            "old_status": old_status,
                            "new_status": update_request.status
                        }
                    )
                else:
                    failed_count += 1
                    error_msg = f"更新发票 {invoice_id} 状态失败"
                    errors.append(error_msg)
                    
                    # 记录失败
                    logging_service.log_print_event(
                        db=db,
                        user_id=current_user.id,
                        event_type="status_update_failed",
                        message=error_msg,
                        details={
                            "invoice_id": invoice_id,
                            "target_status": update_request.status,
                            "current_status": old_status
                        },
                        log_level="ERROR"
                    )
                    
            except Exception as e:
                failed_count += 1
                error_msg = f"处理发票 {invoice_id} 时发生错误: {str(e)}"
                errors.append(error_msg)
                
                # 记录异常
                logging_service.log_print_event(
                    db=db,
                    user_id=current_user.id,
                    event_type="status_update_error",
                    message=error_msg,
                    details={
                        "invoice_id": invoice_id,
                        "target_status": update_request.status,
                        "error": str(e),
                        "exception_type": e.__class__.__name__
                    },
                    log_level="ERROR"
                )
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # 记录批量更新结果
        logging_service.log_print_event(
            db=db,
            user_id=current_user.id,
            event_type="batch_status_update_completed",
            message=f"批量状态更新完成 - 成功{updated_count}个，失败{failed_count}个",
            details={
                "total_requested": len(update_request.invoice_ids),
                "updated_count": updated_count,
                "failed_count": failed_count,
                "target_status": update_request.status,
                "processing_time": processing_time,
                "successful_updates": successful_updates[:10],  # 只记录前10个
                "error_count": len(errors)
            }
        )
        
        return BatchStatusUpdateResponse(
            updated_count=updated_count,
            failed_count=failed_count,
            errors=errors
        )
        
    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"批量更新状态失败: {str(e)}")
        
        # 记录全局错误
        logging_service.log_print_event(
            db=db,
            user_id=current_user.id,
            event_type="batch_status_update_global_error",
            message=f"批量状态更新出现全局错误: {str(e)}",
            details={
                "invoice_ids": update_request.invoice_ids,
                "target_status": update_request.status,
                "error": str(e),
                "processing_time": processing_time,
                "exception_type": e.__class__.__name__
            },
            log_level="CRITICAL"
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量更新失败: {str(e)}"
        )


@router.get("/layouts")
def get_print_layouts():
    """获取可用的打印布局"""
    return {
        "layouts": [
            {
                "value": "1_per_page",
                "label": "1张/页",
                "description": "每页打印1张发票，保持原始尺寸",
                "supported_types": ["normal", "train_ticket"]
            },
            {
                "value": "2_per_page", 
                "label": "2张/页",
                "description": "在一页上打印2张发票，垂直排列",
                "supported_types": ["normal", "train_ticket"]
            },
            {
                "value": "4_per_page",
                "label": "4张/页",
                "description": "在一页上打印4张发票，2x2网格布局",
                "supported_types": ["normal", "train_ticket"]
            },
            {
                "value": "8_per_page",
                "label": "8张/页",
                "description": "在一页上打印8张发票，2x4网格布局（仅火车票支持）",
                "supported_types": ["train_ticket"]
            }
        ],
        "invoice_types": [
            {
                "value": "normal",
                "label": "普通发票",
                "description": "支持1张/页、2张/页、4张/页布局"
            },
            {
                "value": "train_ticket", 
                "label": "火车票",
                "description": "支持所有布局，包括8张/页"
            }
        ]
    }


@router.get("/status-options")
def get_status_options():
    """获取可用的发票状态选项"""
    return {
        "statuses": [
            {
                "value": "printed",
                "label": "已打印",
                "description": "发票已打印，可用于归档"
            },
            {
                "value": "archived",
                "label": "已归档",
                "description": "发票已完成处理并归档"
            },
            {
                "value": "submitted",
                "label": "已提交",
                "description": "发票已提交报销或其他流程"
            },
            {
                "value": "completed",
                "label": "已完成",
                "description": "发票处理流程完全结束"
            }
        ]
    }


@router.post("/generate-for-browser")
def generate_print_for_browser(
    print_request: BatchPrintRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """生成用于浏览器预览和打印的PDF"""
    start_time = datetime.now()
    
    try:
        # 记录浏览器预览开始
        logging_service.log_print_event(
            db=db,
            user_id=current_user.id,
            event_type="browser_preview_started",
            message=f"开始生成浏览器预览 - {len(print_request.invoice_ids)}个发票",
            details={
                "invoice_ids": print_request.invoice_ids,
                "layout": print_request.layout.value,
                "for_browser": True
            }
        )
        
        invoice_service = InvoiceService(db)
        print_service = PrintService(db)
        
        # 获取发票列表
        invoices = []
        for invoice_id in print_request.invoice_ids:
            invoice = invoice_service.get_invoice(invoice_id, current_user.id)
            if invoice:
                invoices.append(invoice)
        
        if not invoices:
            # 记录失败
            logging_service.log_print_event(
                db=db,
                user_id=current_user.id,
                event_type="browser_preview_no_invoices",
                message="浏览器预览失败 - 没有找到有效的发票",
                details={"requested_ids": print_request.invoice_ids},
                log_level="ERROR"
            )
            
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="没有找到有效的发票"
            )
        
        # 创建打印选项 - 验证布局和发票类型组合
        if (print_request.layout == PrintLayout.EIGHT_PER_PAGE and 
            print_request.invoice_type != InvoiceType.TRAIN_TICKET):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="每页8张布局仅支持火车票类型"
            )
            
        options = PrintOptions(
            layout=print_request.layout,
            invoice_type=print_request.invoice_type.value,
            show_dividers=print_request.show_dividers,
            sort_by_type=print_request.sort_by_type
        )
        
        # 生成PDF - 使用统一的高效方法
        pdf_data = print_service.generate_pdf(
            invoices, options, 
            user_id=current_user.id
        )
        
        # 更新发票状态（如果需要）
        if print_request.update_status:
            updated_count = 0
            for invoice in invoices:
                try:
                    success = invoice_service.update_invoice(
                        invoice.id, 
                        current_user.id, 
                        {"status": "printed"}
                    )
                    if success:
                        updated_count += 1
                except Exception as e:
                    logger.warning(f"Failed to update invoice status: {invoice.id}, {str(e)}")
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # 记录成功完成
        logging_service.log_print_event(
            db=db,
            user_id=current_user.id,
            event_type="browser_preview_completed",
            message=f"浏览器预览生成成功 - {len(invoices)}个发票",
            details={
                "total_invoices": len(invoices),
                "layout": print_request.layout.value,
                "pdf_size": len(pdf_data),
                "processing_time": processing_time,
                "status_updated": print_request.update_status
            }
        )
        
        # 返回PDF用于浏览器预览，设置为inline显示
        return StreamingResponse(
            BytesIO(pdf_data),
            media_type="application/pdf",
            headers={
                "Content-Disposition": "inline; filename=batch_print_preview.pdf"
            }
        )
        
    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"Failed to generate browser preview PDF: {str(e)}")
        
        # 记录错误
        logging_service.log_print_event(
            db=db,
            user_id=current_user.id,
            event_type="browser_preview_error",
            message=f"浏览器预览失败: {str(e)}",
            details={
                "invoice_ids": print_request.invoice_ids,
                "error": str(e),
                "processing_time": processing_time,
                "exception_type": e.__class__.__name__
            },
            log_level="ERROR"
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF: {str(e)}"
        )