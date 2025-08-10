from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import CHAR
from datetime import datetime
from app.core.database import Base


class Attachment(Base):
    """发票附件模型"""
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(CHAR(36), ForeignKey("invoices.id"), nullable=False)

    # 文件信息
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    mime_type = Column(String(100))

    # 时间戳
    created_at = Column(DateTime, default=datetime.now, index=True)

    # 外键关系
    invoice = relationship("Invoice", back_populates="attachments")