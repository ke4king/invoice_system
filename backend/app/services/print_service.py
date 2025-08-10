import fitz  # PyMuPDF
from typing import List, Dict, Optional, Callable
from io import BytesIO
import os
import logging
import sys
from enum import Enum
import gc
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.invoice import Invoice
from app.core.config import settings, get_absolute_file_path
from app.services.logging_service import logging_service

# Configure logger with UTF-8 support
logger = logging.getLogger(__name__)

# A4页面常量
A4_WIDTH = 595.28
A4_HEIGHT = 841.89
MARGIN = 20


class PrintLayout(Enum):
    """打印布局枚举"""
    ONE_PER_PAGE = "1_per_page"
    TWO_PER_PAGE = "2_per_page"
    FOUR_PER_PAGE = "4_per_page"
    EIGHT_PER_PAGE = "8_per_page"  # 仅火车票支持


class PrintOptions:
    """打印选项"""
    def __init__(
        self,
        layout: PrintLayout = PrintLayout.FOUR_PER_PAGE,
        invoice_type: str = 'normal',
        show_dividers: bool = True,
        sort_by_type: bool = True
    ):
        self.layout = layout
        self.invoice_type = invoice_type
        self.show_dividers = show_dividers
        self.sort_by_type = sort_by_type


class PrintService:
    """基于原始发票合并逻辑的打印服务类"""
    
    def __init__(self, db: Session = None):
        self.db = db
    
    def _resolve_file_path(self, file_path: str) -> str:
        """解析文件路径，使用统一的路径转换工具"""
        if not file_path:
            return file_path
            
        # 使用统一的路径转换函数
        resolved_path = get_absolute_file_path(file_path)
        logger.debug(f"路径转换: {file_path} -> {resolved_path}")
        return resolved_path
    
    def _create_placeholder_pdf(self, missing_files: list, failed_files: list) -> fitz.Document:
        """创建包含错误信息的占位符PDF"""
        output_doc = fitz.open()
        page = output_doc.new_page(width=A4_WIDTH, height=A4_HEIGHT)
        
        # 添加错误信息文本
        text_content = "发票文件处理错误\n\n"
        
        if missing_files:
            text_content += f"缺失文件 ({len(missing_files)} 个):\n"
            for i, file_path in enumerate(missing_files[:10]):  # 只显示前10个
                text_content += f"• {file_path}\n"
            if len(missing_files) > 10:
                text_content += f"... 还有 {len(missing_files) - 10} 个文件\n"
            text_content += "\n"
        
        if failed_files:
            text_content += f"加载失败文件 ({len(failed_files)} 个):\n"
            for i, (file_path, error) in enumerate(failed_files[:10]):  # 只显示前10个
                text_content += f"• {file_path}: {error}\n"
            if len(failed_files) > 10:
                text_content += f"... 还有 {len(failed_files) - 10} 个文件\n"
        
        # 在页面上插入文本
        text_rect = fitz.Rect(50, 50, A4_WIDTH - 50, A4_HEIGHT - 50)
        page.insert_textbox(text_rect, text_content, fontsize=12, color=(0, 0, 0))
        
        return output_doc
    
    def calculate_pages(self, invoice_count: int, layout: PrintLayout) -> int:
        """计算需要的页数"""
        # 确保layout是枚举类型
        if isinstance(layout, str):
            layout = PrintLayout(layout)
            
        layout_mapping = {
            PrintLayout.ONE_PER_PAGE: 1,
            PrintLayout.TWO_PER_PAGE: 2, 
            PrintLayout.FOUR_PER_PAGE: 4,
            PrintLayout.EIGHT_PER_PAGE: 8
        }
        invoices_per_page = layout_mapping.get(layout, 4)
        return (invoice_count + invoices_per_page - 1) // invoices_per_page
    
    def _sort_invoices_by_type(self, invoices: List[Invoice]) -> List[Invoice]:
        """按消费类型排序发票"""
        return sorted(invoices, key=lambda inv: inv.service_type or "未分类")
    
    def _get_merge_config(self, layout: PrintLayout, invoice_type: str, show_dividers: bool):
        """获取合并配置 - 简化版本"""
        # 确保layout是枚举类型
        if isinstance(layout, str):
            layout = PrintLayout(layout)
            
        layout_mapping = {
            PrintLayout.ONE_PER_PAGE: 1,
            PrintLayout.TWO_PER_PAGE: 2,
            PrintLayout.FOUR_PER_PAGE: 4,
            PrintLayout.EIGHT_PER_PAGE: 8
        }
        
        invoices_per_page = layout_mapping[layout]
        orientation = 'horizontal'  # 统一使用horizontal布局逻辑
        layout_type = 'normal'
        draw_lines = show_dividers
        
        return (invoices_per_page, orientation, layout_type, draw_lines)
    
    def _insert_page_with_stamps(self, target_page, target_rect, src_doc, src_page_num, src_type='pdf', dpi=300):
        """在保留签章的前提下插入页面内容"""
        try:
            src_page = src_doc.load_page(src_page_num)
            actual_dpi = dpi if dpi < 200 else 150 if dpi < 300 else dpi
            pix = src_page.get_pixmap(dpi=actual_dpi, colorspace=fitz.csRGB, annots=True)
            
            src_width = src_page.rect.width
            src_height = src_page.rect.height
            scale_x = target_rect.width / src_width
            scale_y = target_rect.height / src_height
            scale = min(scale_x, scale_y)
            actual_width = src_width * scale
            actual_height = src_height * scale
            center_x = target_rect.x0 + (target_rect.width - actual_width) / 2
            center_y = target_rect.y0 + (target_rect.height - actual_height) / 2
            actual_rect = fitz.Rect(center_x, center_y, center_x + actual_width, center_y + actual_height)
            
            target_page.insert_image(actual_rect, pixmap=pix, keep_proportion=True, overlay=False)
            
            if src_type == 'pdf' and src_page.annots():
                annots = list(src_page.annots())
                for annot in annots:
                    try:
                        annot_type = annot.type[1]
                        if annot_type not in ['Stamp']:
                            rect = annot.rect
                            new_rect = fitz.Rect(
                                actual_rect.x0 + rect.x0 / src_width * actual_width,
                                actual_rect.y0 + rect.y0 / src_height * actual_height, 
                                actual_rect.x0 + rect.x1 / src_width * actual_width,
                                actual_rect.y0 + rect.y1 / src_height * actual_height
                            )
                            
                            if annot_type == 'FreeText':
                                new_annot = target_page.add_text_annot(new_rect.tl, annot.info.get('content', ''))
                                new_annot.set_rect(new_rect)
                            elif annot_type == 'Square':
                                new_annot = target_page.add_rect_annot(new_rect)
                            elif annot_type == 'Circle':
                                new_annot = target_page.add_circle_annot(new_rect)
                            else:
                                new_annot = target_page.add_redact_annot(new_rect)
                            
                            if new_annot:
                                new_annot.set_info(
                                    title=annot.info.get('title', ''),
                                    content=annot.info.get('content', ''),
                                    subject=annot.info.get('subject', '')
                                )
                                try:
                                    if hasattr(annot, 'colors') and annot.colors:
                                        new_annot.set_colors(annot.colors)
                                    if hasattr(annot, 'border') and annot.border:
                                        new_annot.set_border(annot.border)
                                    new_annot.update()
                                except Exception:
                                    pass
                    except Exception as e:
                        logger.warning(f'复制注释时出错: {e}')
            
            del pix
            if dpi > 200:
                import gc
                gc.collect()
                
        except Exception as e:
            logger.error(f'插入页面内容失败: {e}')
    
    def _perform_merge(self, invoices: List[Invoice], options: PrintOptions, dpi=300, progress_callback=None) -> fitz.Document:
        """核心合并逻辑 - 完全基于参考代码重写，只保留4种布局"""
        invoices_per_page, orientation, layout_type, draw_lines = self._get_merge_config(
            options.layout, options.invoice_type, options.show_dividers
        )
        
        # 构建页面信息
        all_pages = []
        missing_files = []
        failed_files = []
        
        logger.info(f"开始处理 {len(invoices)} 张发票文件")
        
        for invoice in invoices:
            resolved_path = self._resolve_file_path(invoice.file_path)
            
            if not os.path.exists(resolved_path):
                logger.warning(f"文件不存在: {resolved_path}")
                missing_files.append(resolved_path)
                continue
                
            try:
                doc = fitz.open(resolved_path)
                if resolved_path.lower().endswith('.pdf'):
                    page_count = len(doc)
                    for i in range(page_count):
                        all_pages.append({
                            'doc': doc, 
                            'page_num': i, 
                            'type': 'pdf'
                        })
                else:
                    all_pages.append({
                        'doc': doc, 
                        'page_num': 0, 
                        'type': 'image'
                    })
            except Exception as e:
                logger.error(f"加载文档失败 {resolved_path}: {e}")
                failed_files.append((resolved_path, str(e)))
                continue
        
        if not all_pages:
            error_details = []
            if missing_files:
                error_details.append(f"缺失文件 {len(missing_files)} 个: {missing_files[:3]}")
            if failed_files:
                error_details.append(f"加载失败 {len(failed_files)} 个: {[f[0] for f in failed_files[:3]]}")
            
            error_msg = f"No valid PDF files found. {'; '.join(error_details)}"
            logger.error(f"PDF合并失败: {error_msg}")
            
            # 如果所有文件都缺失，创建错误信息PDF
            logger.warning(f"所有文件都缺失或无法加载，创建错误信息PDF")
            return self._create_placeholder_pdf(missing_files, failed_files)
        
        # 如果有部分文件缺失，记录警告但继续处理
        if missing_files or failed_files:
            warning_details = []
            if missing_files:
                warning_details.append(f"跳过缺失文件 {len(missing_files)} 个")
                logger.warning(f"缺失的文件: {missing_files[:5]}")  # 记录前5个缺失文件
            if failed_files:
                warning_details.append(f"跳过加载失败文件 {len(failed_files)} 个")
                logger.warning(f"加载失败的文件: {[f[0] for f in failed_files[:5]]}")  # 记录前5个失败文件
            logger.warning(f"PDF合并警告: {'; '.join(warning_details)}，继续处理剩余 {len(all_pages)} 个页面")
        
        output_doc = fitz.open()
        processed_pages = 0
        
        try:
            # 根据布局类型处理
            if invoices_per_page == 1:
                # 1张/页 - 使用横版A4纸
                for src_page_info in all_pages:
                    page = output_doc.new_page(width=A4_HEIGHT, height=A4_WIDTH)  # 横版：宽高互换
                    target_rect = fitz.Rect(MARGIN, MARGIN, A4_HEIGHT - MARGIN, A4_WIDTH - MARGIN)
                    
                    self._insert_page_with_stamps(
                        page, target_rect, src_page_info['doc'],
                        src_page_info['page_num'], src_page_info['type'], dpi
                    )
                    
                    if progress_callback:
                        progress_callback(processed_pages)
                    processed_pages += 1
                        
            elif invoices_per_page == 8:
                # 8张/页（火车票）
                cols, rows = 2, 4
                col_spacing, row_spacing = 15, 8
                
                for i in range(0, len(all_pages), invoices_per_page):
                    chunk = all_pages[i:i + invoices_per_page]
                    page = output_doc.new_page(width=A4_WIDTH, height=A4_HEIGHT)
                    
                    available_width = A4_WIDTH - 2 * MARGIN
                    available_height = A4_HEIGHT - 2 * MARGIN
                    total_col_spacing = (cols - 1) * col_spacing
                    total_row_spacing = (rows - 1) * row_spacing
                    invoice_width = (available_width - total_col_spacing) / cols
                    invoice_height = (available_height - total_row_spacing) / rows
                    
                    for j, src_page_info in enumerate(chunk):
                        if j >= invoices_per_page:
                            break
                        
                        col = j % cols
                        row = j // cols
                        base_x = MARGIN + col * (invoice_width + col_spacing)
                        base_y = MARGIN + row * (invoice_height + row_spacing)
                        target_rect = fitz.Rect(base_x, base_y, base_x + invoice_width, base_y + invoice_height)
                        
                        self._insert_page_with_stamps(
                            page, target_rect, src_page_info['doc'],
                            src_page_info['page_num'], src_page_info['type'], dpi
                        )
                        
                        if progress_callback:
                            progress_callback(processed_pages)
                        processed_pages += 1
                        
                        if draw_lines:
                            if col < cols - 1:
                                line_x = base_x + invoice_width + col_spacing / 2
                                p1 = fitz.Point(line_x, MARGIN)
                                p2 = fitz.Point(line_x, A4_HEIGHT - MARGIN)
                                page.draw_line(p1, p2, color=(0.7, 0.7, 0.7), dashes='[3 3] 0')
                            if row < rows - 1:
                                line_y = base_y + invoice_height + row_spacing / 2
                                p1 = fitz.Point(MARGIN, line_y)
                                p2 = fitz.Point(A4_WIDTH - MARGIN, line_y)
                                page.draw_line(p1, p2, color=(0.7, 0.7, 0.7), dashes='[3 3] 0')
                                
            else:
                # 2张/页和4张/页使用horizontal布局逻辑
                if invoices_per_page == 2:
                    cols, rows = 1, 2
                    col_spacing, row_spacing = 25, 20
                    # 2张/页使用竖版A4纸
                    page_width, page_height = A4_WIDTH, A4_HEIGHT
                elif invoices_per_page == 4:
                    cols, rows = 2, 2  
                    col_spacing, row_spacing = 15, 12
                    # 4张/页使用横版A4纸
                    page_width, page_height = A4_HEIGHT, A4_WIDTH
                else:
                    cols, rows = 2, 1
                    col_spacing, row_spacing = 25, 20
                    page_width, page_height = A4_WIDTH, A4_HEIGHT
                
                for i in range(0, len(all_pages), invoices_per_page):
                    chunk = all_pages[i:i + invoices_per_page]
                    page = output_doc.new_page(width=page_width, height=page_height)
                    
                    available_width = page_width - 2 * MARGIN
                    available_height = page_height - 2 * MARGIN
                    total_col_spacing = (cols - 1) * col_spacing if cols > 1 else 0
                    total_row_spacing = (rows - 1) * row_spacing if rows > 1 else 0
                    invoice_width = (available_width - total_col_spacing) / cols
                    invoice_height = (available_height - total_row_spacing) / rows
                    
                    for j, src_page_info in enumerate(chunk):
                        if j >= invoices_per_page:
                            break
                        
                        # 使用参考代码的位置计算逻辑：col = j // rows, row = j % rows
                        col = j // rows
                        row = j % rows
                        base_x = MARGIN + col * (invoice_width + col_spacing)
                        base_y = MARGIN + row * (invoice_height + row_spacing)
                        target_rect = fitz.Rect(base_x, base_y, base_x + invoice_width, base_y + invoice_height)
                        
                        self._insert_page_with_stamps(
                            page, target_rect, src_page_info['doc'],
                            src_page_info['page_num'], src_page_info['type'], dpi
                        )
                        
                        if progress_callback:
                            progress_callback(processed_pages)
                        processed_pages += 1
                        
                        if draw_lines:
                            if col < cols - 1:
                                line_x = base_x + invoice_width + col_spacing / 2
                                p1 = fitz.Point(line_x, MARGIN)
                                p2 = fitz.Point(line_x, page_height - MARGIN)
                                page.draw_line(p1, p2, color=(0.7, 0.7, 0.7), dashes='[3 3] 0')
                            if row < rows - 1:
                                line_y = base_y + invoice_height + row_spacing / 2
                                p1 = fitz.Point(MARGIN, line_y)
                                p2 = fitz.Point(page_width - MARGIN, line_y)
                                page.draw_line(p1, p2, color=(0.7, 0.7, 0.7), dashes='[3 3] 0')
            
            return output_doc
            
        finally:
            # 清理资源
            for page_info in all_pages:
                try:
                    page_info['doc'].close()
                except:
                    pass
    
    def generate_pdf(self, invoices: List[Invoice], options: PrintOptions, user_id: int = None) -> bytes:
        """统一的PDF生成入口方法"""
        if not invoices:
            raise ValueError("No invoices provided")
        
        print_start_time = datetime.now()
        
        # 记录批量打印开始
        if self.db and user_id:
            logging_service.log_print_event(
                db=self.db,
                event_type="batch_print_started",
                message=f"开始批量打印 {len(invoices)} 张发票",
                user_id=user_id,
                details={
                    "invoice_count": len(invoices),
                    "layout": options.layout.value,
                    "invoice_type": options.invoice_type,
                    "show_dividers": options.show_dividers,
                    "sort_by_type": options.sort_by_type,
                    "start_time": print_start_time.isoformat(),
                    "invoice_ids": [invoice.id for invoice in invoices[:10]]
                }
            )
        
        try:
            logger.info(f"Generating PDF with layout: {options.layout.value}, invoice_type: {options.invoice_type}")
            
            # 排序发票
            if options.sort_by_type:
                invoices = self._sort_invoices_by_type(invoices)
            
            # 执行合并
            merged_doc = self._perform_merge(invoices, options)
            
            if not merged_doc:
                raise Exception("合并文档失败")
            
            # 保存为字节流
            pdf_bytes = merged_doc.tobytes(garbage=4, deflate=True, clean=True)
            merged_doc.close()
            
            # 记录打印成功
            print_duration = (datetime.now() - print_start_time).total_seconds()
            pdf_size = len(pdf_bytes)
            expected_pages = self.calculate_pages(len(invoices), options.layout)
            
            if self.db and user_id:
                logging_service.log_print_event(
                    db=self.db,
                    event_type="batch_print_completed",
                    message=f"批量打印完成: {len(invoices)} 张发票，生成 {expected_pages} 页PDF",
                    user_id=user_id,
                    details={
                        "invoice_count": len(invoices),
                        "expected_pages": expected_pages,
                        "pdf_size": pdf_size,
                        "print_duration": print_duration,
                        "layout": options.layout.value,
                        "success": True
                    }
                )
            
            return pdf_bytes
            
        except Exception as e:
            # 记录打印失败
            error_duration = (datetime.now() - print_start_time).total_seconds()
            
            if self.db and user_id:
                logging_service.log_print_event(
                    db=self.db,
                    event_type="batch_print_failed",
                    message=f"批量打印失败: {str(e)}",
                    user_id=user_id,
                    details={
                        "invoice_count": len(invoices),
                        "error": str(e),
                        "error_duration": error_duration,
                        "layout": options.layout.value,
                        "success": False
                    },
                    log_level="ERROR"
                )
            
            raise
    
    