"""
系统配置管理API端点
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from io import BytesIO
import json
from datetime import datetime

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.services.config_service import config_service
from app.services.logging_service import logging_service

router = APIRouter()


# Pydantic模型
class ConfigValue(BaseModel):
    value: Any
    type: str
    description: str
    is_editable: bool
    updated_at: Optional[str] = None


class ConfigCategory(BaseModel):
    category: str
    configs: Dict[str, ConfigValue]


class ConfigUpdateRequest(BaseModel):
    configs: Dict[str, Any]


class ConfigValidationResponse(BaseModel):
    valid: bool
    message: str


class ConfigExportResponse(BaseModel):
    export_time: str
    category: Optional[str]
    configs: Dict[str, Any]


@router.get("/configs/categories")
async def get_config_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取所有配置类别"""
    try:
        # 只有管理员可以查看配置
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="需要管理员权限"
            )
        
        configs = config_service.get_all_configs(db)
        
        categories = []
        for category, category_configs in configs.items():
            categories.append({
                "name": category,
                "display_name": _get_category_display_name(category),
                "config_count": len(category_configs),
                "description": _get_category_description(category)
            })
        
        return {"categories": categories}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取配置类别失败: {str(e)}"
        )


@router.get("/configs/category/{category}")
async def get_configs_by_category(
    category: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """按类别获取配置"""
    try:
        # 只有管理员可以查看配置
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="需要管理员权限"
            )
        
        configs = config_service.get_configs_by_category(db, category)
        
        return {
            "category": category,
            "display_name": _get_category_display_name(category),
            "configs": configs
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取配置失败: {str(e)}"
        )


@router.get("/configs")
async def get_all_configs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取所有配置"""
    try:
        # 只有管理员可以查看配置
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="需要管理员权限"
            )
        
        configs = config_service.get_all_configs(db)
        
        return {"configs": configs}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取所有配置失败: {str(e)}"
        )


@router.get("/configs/{config_key}")
async def get_config(
    config_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取单个配置"""
    try:
        # 只有管理员可以查看配置
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="需要管理员权限"
            )
        
        value = config_service.get_config(db, config_key)
        
        if value is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="配置项不存在"
            )
        
        return {
            "key": config_key,
            "value": value
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取配置失败: {str(e)}"
        )


@router.post("/configs/{config_key}")
async def update_config(
    config_key: str,
    request: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新单个配置"""
    try:
        # 只有管理员可以修改配置
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="需要管理员权限"
            )
        
        value = request.get("value")
        
        # 验证配置值
        valid, message = config_service.validate_config_value(config_key, value)
        if not valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"配置值无效: {message}"
            )
        
        success = config_service.set_config(db, config_key, value, current_user.id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="更新配置失败"
            )
        
        return {
            "message": "配置更新成功",
            "key": config_key,
            "value": value
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新配置失败: {str(e)}"
        )


@router.post("/configs/batch-update")
async def batch_update_configs(
    request: ConfigUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """批量更新配置"""
    try:
        # 只有管理员可以修改配置
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="需要管理员权限"
            )
        
        # 验证所有配置值
        validation_errors = {}
        for key, value in request.configs.items():
            valid, message = config_service.validate_config_value(key, value)
            if not valid:
                validation_errors[key] = message
        
        if validation_errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "配置值验证失败", "errors": validation_errors}
            )
        
        results = config_service.batch_update_configs(db, request.configs, current_user.id)
        
        success_count = sum(1 for success in results.values() if success)
        failure_count = len(results) - success_count
        
        return {
            "message": f"批量更新完成: 成功 {success_count} 个，失败 {failure_count} 个",
            "results": results,
            "success_count": success_count,
            "failure_count": failure_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量更新配置失败: {str(e)}"
        )


@router.post("/configs/{config_key}/validate")
async def validate_config(
    config_key: str,
    request: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """验证配置值"""
    try:
        # 只有管理员可以验证配置
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="需要管理员权限"
            )
        
        value = request.get("value")
        valid, message = config_service.validate_config_value(config_key, value)
        
        return ConfigValidationResponse(
            valid=valid,
            message=message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"验证配置失败: {str(e)}"
        )


@router.post("/configs/{config_key}/reset")
async def reset_config_to_default(
    config_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """重置配置为默认值"""
    try:
        # 只有管理员可以重置配置
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="需要管理员权限"
            )
        
        success = config_service.reset_config_to_default(db, config_key, current_user.id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="重置配置失败或配置不存在"
            )
        
        new_value = config_service.get_config(db, config_key)
        
        return {
            "message": "配置已重置为默认值",
            "key": config_key,
            "value": new_value
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重置配置失败: {str(e)}"
        )


@router.get("/configs/export/{category}")
async def export_configs(
    category: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """导出配置"""
    try:
        # 只有管理员可以导出配置
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="需要管理员权限"
            )
        
        # 记录导出操作
        logging_service.log_system_event(
            db=db,
            user_id=current_user.id,
            event_type="config_export_started",
            message=f"开始导出配置: {category or '全部'}",
            details={"category": category}
        )
        
        export_data = config_service.export_configs(db, category if category != "all" else None)
        
        if not export_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="没有找到配置数据"
            )
        
        # 转换为JSON字符串
        json_content = json.dumps(export_data, ensure_ascii=False, indent=2)
        json_bytes = json_content.encode('utf-8')
        
        # 记录导出完成
        logging_service.log_system_event(
            db=db,
            user_id=current_user.id,
            event_type="config_export_completed",
            message=f"配置导出完成: {category or '全部'}",
            details={
                "category": category,
                "file_size": len(json_bytes),
                "config_count": len(export_data.get('configs', {}))
            }
        )
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        category_suffix = f"_{category}" if category and category != "all" else ""
        filename = f"system_configs{category_suffix}_{timestamp}.json"
        
        return StreamingResponse(
            BytesIO(json_bytes),
            media_type="application/json; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{filename}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # 记录导出失败
        try:
            logging_service.log_system_event(
                db=db,
                user_id=current_user.id,
                event_type="config_export_failed",
                message=f"配置导出失败: {str(e)}",
                details={"category": category, "error": str(e)},
                log_level="ERROR"
            )
        except:
            pass
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出配置失败: {str(e)}"
        )


@router.post("/configs/import")
async def import_configs(
    import_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """导入配置"""
    try:
        # 只有管理员可以导入配置
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="需要管理员权限"
            )
        
        # 记录导入操作
        logging_service.log_system_event(
            db=db,
            user_id=current_user.id,
            event_type="config_import_started",
            message="开始导入配置",
            details={
                "source_export_time": import_data.get('export_time'),
                "category": import_data.get('category')
            }
        )
        
        results = config_service.import_configs(db, import_data, current_user.id)
        
        success_count = sum(1 for success in results.values() if success)
        failure_count = len(results) - success_count
        
        return {
            "message": f"配置导入完成: 成功 {success_count} 个，失败 {failure_count} 个",
            "results": results,
            "success_count": success_count,
            "failure_count": failure_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        # 记录导入失败
        try:
            logging_service.log_system_event(
                db=db,
                user_id=current_user.id,
                event_type="config_import_failed",
                message=f"配置导入失败: {str(e)}",
                details={"error": str(e)},
                log_level="ERROR"
            )
        except:
            pass
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导入配置失败: {str(e)}"
        )


@router.post("/configs/init-defaults")
async def init_default_configs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """初始化默认配置"""
    try:
        # 只有管理员可以初始化配置
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="需要管理员权限"
            )
        
        config_service.init_default_configs(db)
        
        # 记录初始化操作
        logging_service.log_system_event(
            db=db,
            user_id=current_user.id,
            event_type="config_init_defaults",
            message="初始化默认配置完成",
            details={}
        )
        
        return {"message": "默认配置初始化完成"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"初始化默认配置失败: {str(e)}"
        )


def _get_category_display_name(category: str) -> str:
    """获取类别显示名称"""
    display_names = {
        'logging': '日志管理',
        'monitoring': '系统监控',
        'ocr': 'OCR识别',
        'email': '邮箱扫描',
        'print': '打印管理',
        'system': '系统设置',
        'other': '其他配置'
    }
    return display_names.get(category, category)


def _get_category_description(category: str) -> str:
    """获取类别描述"""
    descriptions = {
        'logging': '日志记录、保留和导出相关配置',
        'monitoring': '系统监控、预警和性能指标配置',
        'ocr': 'OCR识别服务相关配置',
        'email': '邮箱扫描和处理配置',
        'print': '打印和批量操作配置',
        'system': '系统基础设置和维护配置',
        'other': '其他自定义配置'
    }
    return descriptions.get(category, '未知类别')