from sqlalchemy import Column, Integer, String, DateTime, JSON, UniqueConstraint
from datetime import datetime
from app.core.database import Base


class OCRCache(Base):
    __tablename__ = "ocr_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sha256 = Column(String(64), nullable=False, index=True)
    status = Column(String(20), default="success")  # success, failed
    ocr_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint('sha256', name='uq_ocr_cache_sha256'),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}
    )


