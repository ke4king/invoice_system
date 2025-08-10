from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import redis
import logging

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.core.config import settings
from app.services.email_service import EmailService
from app.schemas.email_config import (
    EmailConfig, EmailConfigCreate, EmailConfigUpdate, 
    EmailConnectionTest, EmailScanResult, ManualScanRequest
)
from app.schemas.user import User
from app.workers.email_tasks import manual_email_scan_task

router = APIRouter()
logger = logging.getLogger(__name__)

def get_email_scan_lock_key(user_id: int, config_id: int = None) -> str:
    """生成邮箱扫描锁的Redis key"""
    if config_id:
        return f"email_scan_lock:user:{user_id}:config:{config_id}"
    else:
        return f"email_scan_lock:user:{user_id}:all"

def is_email_scan_running(user_id: int, config_id: int = None) -> bool:
    """检查是否有正在运行的邮箱扫描任务"""
    try:
        redis_client = redis.from_url(settings.REDIS_URL)
        
        # 检查指定配置的锁
        if config_id:
            specific_lock = get_email_scan_lock_key(user_id, config_id)
            if redis_client.exists(specific_lock):
                return True
        
        # 检查用户全局扫描锁
        global_lock = get_email_scan_lock_key(user_id, None)
        if redis_client.exists(global_lock):
            return True
            
        return False
        
    except Exception as e:
        logger.warning(f"检查邮箱扫描锁失败: {e}")
        return False


@router.post("", response_model=EmailConfig)
def create_email_config(
    config_data: EmailConfigCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """创建或更新邮箱配置"""
    email_service = EmailService(db)
    
    try:
        config = email_service.create_email_config(
            user_id=current_user.id,
            email_address=config_data.email_address,
            imap_server=config_data.imap_server,
            imap_port=config_data.imap_port,
            username=config_data.username,
            password=config_data.password,
            scan_days=config_data.scan_days
        )
        
        return config
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"创建邮箱配置失败: {str(e)}"
        )


@router.get("", response_model=List[EmailConfig])
def get_email_configs(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取用户的邮箱配置列表"""
    email_service = EmailService(db)
    configs = email_service.get_user_email_configs(current_user.id)
    return configs


@router.put("/{config_id}", response_model=EmailConfig)
def update_email_config(
    config_id: int,
    config_update: EmailConfigUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新邮箱配置"""
    from app.models.email_config import EmailConfig as EmailConfigModel
    
    config = db.query(EmailConfigModel).filter(
        EmailConfigModel.id == config_id,
        EmailConfigModel.user_id == current_user.id
    ).first()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="邮箱配置不存在"
        )
    
    # 更新字段
    update_data = config_update.dict(exclude_unset=True)
    
    # 如果更新密码，需要加密
    if 'password' in update_data:
        email_service = EmailService(db)
        config.password_encrypted = email_service.encrypt_password(update_data['password'])
        del update_data['password']
    
    for field, value in update_data.items():
        setattr(config, field, value)
    
    db.commit()
    db.refresh(config)
    return config


@router.delete("/{config_id}")
def delete_email_config(
    config_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """删除邮箱配置"""
    email_service = EmailService(db)
    success = email_service.delete_email_config(config_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="邮箱配置不存在"
        )
    
    return {"message": "邮箱配置删除成功"}


@router.post("/test-connection")
def test_email_connection(
    test_data: EmailConnectionTest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """测试邮箱连接"""
    email_service = EmailService(db)
    
    # 创建临时配置对象用于测试
    from app.models.email_config import EmailConfig as EmailConfigModel
    temp_config = EmailConfigModel(
        email_address=test_data.email_address,
        imap_server=test_data.imap_server,
        imap_port=test_data.imap_port,
        username=test_data.username,
        password_encrypted=email_service.encrypt_password(test_data.password)
    )
    
    success = email_service.test_email_connection(temp_config)
    
    if success:
        return {"message": "邮箱连接测试成功", "status": "success"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱连接测试失败，请检查配置信息"
        )


@router.post("/scan", response_model=dict)
def manual_scan_emails(
    scan_request: ManualScanRequest = ManualScanRequest(),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """手动触发邮箱扫描"""
    try:
        # 检查是否有正在运行的扫描任务
        if is_email_scan_running(current_user.id, scan_request.config_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="邮箱扫描进行中，请稍候再试"
            )
        
        # 启动异步扫描任务
        task = manual_email_scan_task.delay(
            user_id=current_user.id,
            config_id=scan_request.config_id,
            days=scan_request.days
        )
        
        return {
            "message": "邮箱扫描任务已启动",
            "task_id": task.id,
            "status": "started"
        }
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"启动邮箱扫描失败: {str(e)}"
        )


@router.get("/scan-status/{task_id}")
def get_scan_status(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """获取扫描任务状态"""
    from app.workers.celery_app import celery_app
    
    try:
        task = celery_app.AsyncResult(task_id)
        
        if task.state == 'PENDING':
            response = {
                'state': task.state,
                'status': 'Task is waiting to be processed'
            }
        elif task.state == 'PROGRESS':
            response = {
                'state': task.state,
                'current': task.info.get('current', 0),
                'total': task.info.get('total', 1),
                'status': task.info.get('status', '')
            }
        elif task.state == 'SUCCESS':
            response = {
                'state': task.state,
                'result': task.result
            }
        else:  # FAILURE
            response = {
                'state': task.state,
                'error': str(task.info)
            }
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务状态失败: {str(e)}"
        )