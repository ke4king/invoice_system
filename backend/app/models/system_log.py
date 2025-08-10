from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class SystemLog(Base):
    """系统日志模型"""
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # 日志信息
    log_type = Column(String(50), nullable=False, index=True)  # auth, invoice, email, ocr, print, system
    log_level = Column(String(20), default="INFO", index=True)  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    message = Column(Text, nullable=False)
    details = Column(JSON)  # 详细信息，JSON格式

    # 关联信息
    resource_type = Column(String(50))  # invoice, email, user等
    resource_id = Column(String(50))    # 关联资源的ID
    ip_address = Column(String(45))     # 客户端IP地址
    user_agent = Column(Text)           # 用户代理

    # 时间戳
    created_at = Column(DateTime, default=datetime.now, index=True)

    # 外键关系
    user = relationship("User", back_populates="system_logs")