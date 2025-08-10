from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class EmailConfig(Base):
    """邮箱配置模型"""
    __tablename__ = "email_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # 邮箱配置信息
    email_address = Column(String(100), nullable=False, index=True)
    imap_server = Column(String(100), nullable=False)
    imap_port = Column(Integer, default=993)
    username = Column(String(100), nullable=False)
    password_encrypted = Column(Text, nullable=False)  # 加密存储的密码
    
    # 配置状态
    is_active = Column(Boolean, default=True)
    last_scan_time = Column(DateTime)  # 最后扫描时间
    scan_days = Column(Integer, default=7)  # 扫描天数范围
    # 增量扫描：记录最后处理的IMAP UID 与 UIDVALIDITY
    last_seen_uid = Column(BigInteger)  # None 表示首次全量或按日期扫描
    uid_validity = Column(BigInteger)  # 服务器UIDVALIDITY，变化时需重置last_seen_uid

    # 时间戳
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 外键关系
    user = relationship("User", back_populates="email_configs")