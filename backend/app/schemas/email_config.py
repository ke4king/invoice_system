from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime


# 邮箱配置基础模式
class EmailConfigBase(BaseModel):
    email_address: EmailStr
    imap_server: str
    imap_port: int = 993
    username: str
    scan_days: int = 7


# 创建邮箱配置请求模式
class EmailConfigCreate(EmailConfigBase):
    password: str


# 更新邮箱配置请求模式
class EmailConfigUpdate(BaseModel):
    email_address: Optional[EmailStr] = None
    imap_server: Optional[str] = None
    imap_port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    scan_days: Optional[int] = None
    is_active: Optional[bool] = None


# 邮箱配置响应模式
class EmailConfig(EmailConfigBase):
    id: int
    user_id: int
    is_active: bool
    last_scan_time: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# 邮箱连接测试请求模式
class EmailConnectionTest(BaseModel):
    email_address: EmailStr
    imap_server: str
    imap_port: int = 993
    username: str
    password: str


# 邮箱扫描结果模式
class EmailScanResult(BaseModel):
    config_id: int
    processed_count: int
    success_count: int
    error_count: int
    errors: List[str] = []
    processed_files: List[Dict[str, Any]] = []


# 手动邮箱扫描请求模式
class ManualScanRequest(BaseModel):
    config_id: Optional[int] = None  # 如果为空，扫描所有活跃配置
    days: int = 7
    force: bool = False  # 是否强制扫描（忽略最后扫描时间）