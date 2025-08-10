from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import CHAR
from datetime import datetime
import uuid
from app.core.database import Base
from sqlalchemy import UniqueConstraint


class Email(Base):
    """邮件模型"""
    __tablename__ = "emails"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # 邮件基本信息
    message_id = Column(String(255), nullable=False, index=True)  # 邮件唯一标识
    subject = Column(String(500))
    sender = Column(String(255), index=True)
    recipient = Column(String(255))
    date_sent = Column(DateTime, index=True)
    date_received = Column(DateTime, index=True)

    # 邮件内容
    body_text = Column(Text)
    body_html = Column(Text)
    
    # 附件信息
    has_attachments = Column(Boolean, default=False)
    attachment_count = Column(Integer, default=0)
    attachment_info = Column(JSON)  # 存储附件详细信息

    # 发票检测状态
    invoice_scan_status = Column(String(20), default="pending", index=True)  # pending, no_invoice, has_invoice
    invoice_count = Column(Integer, default=0)  # 检测到的发票数量
    scan_result = Column(JSON)  # 扫描结果详情
    
    # 处理状态
    processing_status = Column(String(20), default="unprocessed", index=True)  # unprocessed, processing, completed, failed
    error_message = Column(Text)

    # 时间戳
    created_at = Column(DateTime, default=datetime.now, index=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    scanned_at = Column(DateTime)  # 扫描完成时间

    # 外键关系
    user = relationship("User", back_populates="emails")
    
    # 添加唯一约束/索引：同一用户下的邮件message_id唯一
    __table_args__ = (
        UniqueConstraint('user_id', 'message_id', name='uq_email_user_message'),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}
    )