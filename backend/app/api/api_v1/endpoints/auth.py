from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from fastapi.responses import JSONResponse
from app.core.deps import get_current_active_user

from app.core.database import get_db
from app.core.security import create_access_token
from app.core.deps import get_current_active_user
from app.core.config import settings
from app.services.user_service import UserService
from app.services.logging_service import logging_service, get_client_info
from app.schemas.user import LoginResponse, User, PasswordChange

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """用户登录"""
    user_service = UserService(db)
    ip_address, user_agent = get_client_info(request)
    
    user = user_service.authenticate_user(form_data.username, form_data.password)
    
    if not user:
        # 记录登录失败
        logging_service.log_auth_event(
            db=db,
            event_type="login_failed",
            message=f"用户登录失败: {form_data.username}",
            username=form_data.username,
            ip_address=ip_address,
            user_agent=user_agent,
            success=False
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    # 记录登录成功
    logging_service.log_auth_event(
        db=db,
        event_type="login_success",
        message=f"用户登录成功: {form_data.username}",
        user_id=user.id,
        username=form_data.username,
        ip_address=ip_address,
        user_agent=user_agent,
        success=True
    )
    
    # 兼容：如启用 Cookie 模式，则通过 HttpOnly Cookie 下发令牌
    if settings.USE_COOKIE_AUTH:
        response = JSONResponse({
            "token_type": "bearer",
            "user": User.from_orm(user).model_dump()
        })
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE
        )
        return response
    return LoginResponse(access_token=access_token, token_type="bearer", user=User.from_orm(user))


@router.post("/change-password")
def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """修改密码"""
    user_service = UserService(db)
    success = user_service.change_password(
        current_user.id,
        password_data.current_password,
        password_data.new_password
    )
    
    if not success:
        # 记录密码修改失败
        logging_service.log_auth_event(
            db=db,
            event_type="password_change_failed",
            message=f"用户密码修改失败: {current_user.username}",
            user_id=current_user.id,
            username=current_user.username,
            success=False
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="当前密码错误"
        )
    
    # 记录密码修改成功
    logging_service.log_auth_event(
        db=db,
        event_type="password_change_success",
        message=f"用户密码修改成功: {current_user.username}",
        user_id=current_user.id,
        username=current_user.username,
        success=True
    )
    
    return {"message": "密码修改成功"}


@router.get("/me", response_model=User)
def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """获取当前用户信息"""
    return current_user


@router.post("/logout")
def logout(current_user: User = Depends(get_current_active_user)):
    """用户登出"""
    # 支持 Cookie 模式：清除 cookie
    response = JSONResponse({"message": "登出成功"})
    if settings.USE_COOKIE_AUTH:
        response.delete_cookie("access_token")
    return response