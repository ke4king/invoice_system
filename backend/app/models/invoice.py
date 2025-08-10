from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, JSON, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import CHAR
from datetime import datetime
import uuid
from app.core.database import Base
from sqlalchemy import UniqueConstraint


class Invoice(Base):
    """发票模型"""
    __tablename__ = "invoices"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # 文件信息
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    file_md5_hash = Column(String(32), index=True)  # MD5哈希值，用于快速去重
    file_sha256_hash = Column(String(64), index=True)  # SHA256哈希值，用于精确验证

    # 来源信息
    source = Column(String(20), default="manual", index=True)  # manual, email

    # 发票基本信息
    invoice_code = Column(String(50), index=True)
    invoice_num = Column(String(50), index=True)
    invoice_date = Column(DateTime, index=True)
    invoice_type = Column(String(50))

    # 购买方信息
    purchaser_name = Column(String(200), index=True)
    purchaser_register_num = Column(String(50))
    purchaser_address = Column(Text)
    purchaser_bank = Column(Text)

    # 销售方信息
    seller_name = Column(String(200), index=True)
    seller_register_num = Column(String(50))
    seller_address = Column(Text)
    seller_bank = Column(Text)

    # 金额信息
    total_amount = Column(Numeric(15, 2), index=True)
    total_tax = Column(Numeric(15, 2))
    amount_in_words = Column(String(100))
    amount_in_figures = Column(Numeric(15, 2))

    # 其他信息
    service_type = Column(String(50), index=True)  # 消费类型，用于分类打印
    commodity_details = Column(JSON)  # 商品明细，JSON格式存储
    ocr_raw_data = Column(JSON)  # OCR原始返回数据

    # 状态管理
    status = Column(String(20), default="processing", index=True)  # pending, processing, completed, failed, archived, duplicate
    ocr_status = Column(String(20), default="pending")  # pending, processing, success, failed
    ocr_error_message = Column(Text)

    # 时间戳
    created_at = Column(DateTime, default=datetime.now, index=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    processed_at = Column(DateTime)  # OCR处理完成时间

    # 外键关系
    user = relationship("User", back_populates="invoices")
    attachments = relationship("Attachment", back_populates="invoice", cascade="all, delete-orphan")

    # 添加唯一约束索引与表选项
    __table_args__ = (
        UniqueConstraint('user_id', 'file_md5_hash', 'file_size', name='uq_invoice_user_filehash_size'),
        UniqueConstraint('user_id', 'file_sha256_hash', name='uq_invoice_user_sha256'),
        UniqueConstraint('user_id', 'invoice_num', name='uq_invoice_user_invoicenum'),
        {
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_unicode_ci"
        },
    )