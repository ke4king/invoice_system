from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# 用户基础模式
class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    is_active: bool = True


# 创建用户请求模式
class UserCreate(UserBase):
    password: str


# 更新用户请求模式
class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None


# 密码修改模式
class PasswordChange(BaseModel):
    current_password: str
    new_password: str


# 用户响应模式
class User(UserBase):
    id: int
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# 登录请求模式
class LoginRequest(BaseModel):
    username: str
    password: str


# 登录响应模式
class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: User


# 令牌数据模式
class TokenData(BaseModel):
    username: Optional[str] = None