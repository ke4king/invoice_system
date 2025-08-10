"""
系统配置管理服务
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from app.core.database import Base
from app.services.logging_service import logging_service
import json
import logging

logger = logging.getLogger(__name__)


class SystemConfig(Base):
    """系统配置模型"""
    __tablename__ = "system_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String(255), unique=True, index=True, nullable=False)
    config_value = Column(Text, nullable=True)
    config_type = Column(String(50), nullable=False, default='string')  # string, int, float, bool, json
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True, index=True)
    is_editable = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class SystemConfigService:
    """系统配置管理服务"""
    
    # 默认配置定义
    DEFAULT_CONFIGS = {
        # 日志相关配置
        'logging.default_level': {
            'value': 'INFO',
            'type': 'string',
            'category': 'logging',
            'description': '默认日志级别',
            'options': ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        },
        'logging.retention_days': {
            'value': 90,
            'type': 'int',
            'category': 'logging',
            'description': '日志保留天数'
        },
        'logging.max_export_records': {
            'value': 50000,
            'type': 'int',
            'category': 'logging',
            'description': '单次导出最大记录数'
        },
        'logging.enable_performance_logging': {
            'value': True,
            'type': 'bool',
            'category': 'logging',
            'description': '启用性能日志记录'
        },
        
        # 监控相关配置
        'monitoring.health_check_interval': {
            'value': 300,  # 5分钟
            'type': 'int',
            'category': 'monitoring',
            'description': '系统健康检查间隔(秒)'
        },
        'monitoring.performance_metrics_interval': {
            'value': 3600,  # 1小时
            'type': 'int',
            'category': 'monitoring',
            'description': '性能指标收集间隔(秒)'
        },
        'monitoring.alert_cpu_threshold': {
            'value': 80.0,
            'type': 'float',
            'category': 'monitoring',
            'description': 'CPU使用率预警阈值(%)'
        },
        'monitoring.alert_memory_threshold': {
            'value': 85.0,
            'type': 'float',
            'category': 'monitoring',
            'description': '内存使用率预警阈值(%)'
        },
        'monitoring.alert_disk_threshold': {
            'value': 90.0,
            'type': 'float',
            'category': 'monitoring',
            'description': '磁盘使用率预警阈值(%)'
        },
        'monitoring.error_rate_threshold': {
            'value': 10.0,
            'type': 'float',
            'category': 'monitoring',
            'description': '错误率预警阈值(%)'
        },
        
        # OCR相关配置
        'ocr.max_retries': {
            'value': 3,
            'type': 'int',
            'category': 'ocr',
            'description': 'OCR识别最大重试次数'
        },
        'ocr.timeout_seconds': {
            'value': 30,
            'type': 'int',
            'category': 'ocr',
            'description': 'OCR识别超时时间(秒)'
        },
        'ocr.enable_detailed_logging': {
            'value': True,
            'type': 'bool',
            'category': 'ocr',
            'description': '启用OCR详细日志记录'
        },
        
        # 邮箱扫描配置
        'email.scan_interval_minutes': {
            'value': 30,
            'type': 'int',
            'category': 'email',
            'description': '邮箱扫描间隔(分钟)'
        },
        'email.max_scan_days': {
            'value': 7,
            'type': 'int',
            'category': 'email',
            'description': '邮箱扫描最大天数'
        },
        'email.enable_scan_logging': {
            'value': True,
            'type': 'bool',
            'category': 'email',
            'description': '启用邮箱扫描日志'
        },
        
        # 打印相关配置
        'print.enable_status_update_logging': {
            'value': True,
            'type': 'bool',
            'category': 'print',
            'description': '启用打印状态更新日志'
        },
        'print.batch_operation_logging': {
            'value': True,
            'type': 'bool',
            'category': 'print',
            'description': '启用批量操作日志'
        },
        
        # 系统配置
        'system.enable_request_logging': {
            'value': False,
            'type': 'bool',
            'category': 'system',
            'description': '启用请求日志记录'
        },
        'system.maintenance_mode': {
            'value': False,
            'type': 'bool',
            'category': 'system',
            'description': '维护模式',
            'is_editable': False  # 需要特殊权限修改
        },
        'system.backup_enabled': {
            'value': True,
            'type': 'bool',
            'category': 'system',
            'description': '启用自动备份'
        },
        'system.backup_retention_days': {
            'value': 30,
            'type': 'int',
            'category': 'system',
            'description': '备份保留天数'
        }
    }
    
    def __init__(self):
        pass
    
    def init_default_configs(self, db: Session) -> None:
        """初始化默认配置"""
        try:
            for key, config_def in self.DEFAULT_CONFIGS.items():
                existing = db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
                if not existing:
                    config = SystemConfig(
                        config_key=key,
                        config_value=self._serialize_value(config_def['value'], config_def['type']),
                        config_type=config_def['type'],
                        description=config_def['description'],
                        category=config_def['category'],
                        is_editable=config_def.get('is_editable', True)
                    )
                    db.add(config)
            
            db.commit()
            logger.info("系统默认配置初始化完成")
            
        except Exception as e:
            db.rollback()
            logger.error(f"初始化默认配置失败: {str(e)}")
            raise
    
    def get_config(self, db: Session, key: str, default: Any = None) -> Any:
        """获取配置值"""
        try:
            config = db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
            if config:
                return self._deserialize_value(config.config_value, config.config_type)
            return default
            
        except Exception as e:
            logger.error(f"获取配置失败 {key}: {str(e)}")
            return default
    
    def set_config(self, db: Session, key: str, value: Any, user_id: int = None) -> bool:
        """设置配置值"""
        try:
            config = db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
            
            if not config:
                # 如果配置不存在，创建新的
                config_def = self.DEFAULT_CONFIGS.get(key, {})
                config = SystemConfig(
                    config_key=key,
                    config_value=self._serialize_value(value, config_def.get('type', 'string')),
                    config_type=config_def.get('type', 'string'),
                    description=config_def.get('description', ''),
                    category=config_def.get('category', 'custom'),
                    is_editable=config_def.get('is_editable', True)
                )
                db.add(config)
            else:
                # 检查是否可编辑
                if not config.is_editable:
                    logger.warning(f"配置 {key} 不允许编辑")
                    return False
                
                old_value = self._deserialize_value(config.config_value, config.config_type)
                config.config_value = self._serialize_value(value, config.config_type)
                config.updated_at = datetime.now()
                
                # 记录配置变更日志
                logging_service.log_system_event(
                    db=db,
                    user_id=user_id,
                    event_type="config_changed",
                    message=f"系统配置变更: {key}",
                    details={
                        "config_key": key,
                        "old_value": old_value,
                        "new_value": value,
                        "category": config.category
                    }
                )
            
            db.commit()
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"设置配置失败 {key}: {str(e)}")
            return False
    
    def get_configs_by_category(self, db: Session, category: str) -> Dict[str, Any]:
        """按类别获取配置"""
        try:
            configs = db.query(SystemConfig).filter(SystemConfig.category == category).all()
            result = {}
            
            for config in configs:
                result[config.config_key] = {
                    'value': self._deserialize_value(config.config_value, config.config_type),
                    'type': config.config_type,
                    'description': config.description,
                    'is_editable': config.is_editable,
                    'updated_at': config.updated_at.isoformat() if config.updated_at else None
                }
            
            return result
            
        except Exception as e:
            logger.error(f"获取分类配置失败 {category}: {str(e)}")
            return {}
    
    def get_all_configs(self, db: Session) -> Dict[str, Dict[str, Any]]:
        """获取所有配置，按类别分组"""
        try:
            configs = db.query(SystemConfig).all()
            result = {}
            
            for config in configs:
                category = config.category or 'other'
                if category not in result:
                    result[category] = {}
                
                result[category][config.config_key] = {
                    'value': self._deserialize_value(config.config_value, config.config_type),
                    'type': config.config_type,
                    'description': config.description,
                    'is_editable': config.is_editable,
                    'updated_at': config.updated_at.isoformat() if config.updated_at else None
                }
            
            return result
            
        except Exception as e:
            logger.error(f"获取所有配置失败: {str(e)}")
            return {}
    
    def batch_update_configs(self, db: Session, configs: Dict[str, Any], user_id: int = None) -> Dict[str, bool]:
        """批量更新配置"""
        results = {}
        
        try:
            for key, value in configs.items():
                results[key] = self.set_config(db, key, value, user_id)
            
            # 记录批量更新日志
            logging_service.log_system_event(
                db=db,
                user_id=user_id,
                event_type="config_batch_update",
                message=f"批量更新系统配置",
                details={
                    "updated_configs": list(configs.keys()),
                    "success_count": sum(1 for success in results.values() if success),
                    "failure_count": sum(1 for success in results.values() if not success)
                }
            )
            
            return results
            
        except Exception as e:
            logger.error(f"批量更新配置失败: {str(e)}")
            return results
    
    def reset_config_to_default(self, db: Session, key: str, user_id: int = None) -> bool:
        """将配置重置为默认值"""
        try:
            if key not in self.DEFAULT_CONFIGS:
                logger.warning(f"未找到默认配置: {key}")
                return False
            
            default_config = self.DEFAULT_CONFIGS[key]
            return self.set_config(db, key, default_config['value'], user_id)
            
        except Exception as e:
            logger.error(f"重置配置失败 {key}: {str(e)}")
            return False
    
    def validate_config_value(self, key: str, value: Any) -> tuple[bool, str]:
        """验证配置值"""
        try:
            if key not in self.DEFAULT_CONFIGS:
                return True, ""  # 自定义配置不验证
            
            config_def = self.DEFAULT_CONFIGS[key]
            config_type = config_def['type']
            
            # 类型验证
            if config_type == 'int':
                try:
                    int(value)
                except ValueError:
                    return False, "必须是整数"
            elif config_type == 'float':
                try:
                    float(value)
                except ValueError:
                    return False, "必须是数字"
            elif config_type == 'bool':
                if not isinstance(value, bool):
                    return False, "必须是布尔值"
            elif config_type == 'json':
                if isinstance(value, str):
                    try:
                        json.loads(value)
                    except json.JSONDecodeError:
                        return False, "必须是有效的JSON格式"
            
            # 选项验证
            if 'options' in config_def:
                if value not in config_def['options']:
                    return False, f"必须是以下选项之一: {', '.join(config_def['options'])}"
            
            # 范围验证
            if 'min_value' in config_def:
                if float(value) < config_def['min_value']:
                    return False, f"不能小于 {config_def['min_value']}"
            
            if 'max_value' in config_def:
                if float(value) > config_def['max_value']:
                    return False, f"不能大于 {config_def['max_value']}"
            
            return True, ""
            
        except Exception as e:
            logger.error(f"验证配置值失败 {key}: {str(e)}")
            return False, "验证失败"
    
    def export_configs(self, db: Session, category: str = None) -> Dict[str, Any]:
        """导出配置"""
        try:
            if category:
                configs = self.get_configs_by_category(db, category)
            else:
                configs = self.get_all_configs(db)
            
            export_data = {
                "export_time": datetime.now().isoformat(),
                "category": category,
                "configs": configs
            }
            
            return export_data
            
        except Exception as e:
            logger.error(f"导出配置失败: {str(e)}")
            return {}
    
    def import_configs(self, db: Session, config_data: Dict[str, Any], user_id: int = None) -> Dict[str, bool]:
        """导入配置"""
        results = {}
        
        try:
            configs = config_data.get('configs', {})
            
            # 扁平化配置数据
            flat_configs = {}
            for category, category_configs in configs.items():
                if isinstance(category_configs, dict):
                    for key, config_info in category_configs.items():
                        if isinstance(config_info, dict) and 'value' in config_info:
                            flat_configs[key] = config_info['value']
                        else:
                            flat_configs[key] = config_info
                else:
                    flat_configs[category] = category_configs
            
            results = self.batch_update_configs(db, flat_configs, user_id)
            
            # 记录导入日志
            logging_service.log_system_event(
                db=db,
                user_id=user_id,
                event_type="config_import",
                message=f"导入系统配置",
                details={
                    "imported_configs": list(flat_configs.keys()),
                    "source_export_time": config_data.get('export_time'),
                    "success_count": sum(1 for success in results.values() if success),
                    "failure_count": sum(1 for success in results.values() if not success)
                }
            )
            
            return results
            
        except Exception as e:
            logger.error(f"导入配置失败: {str(e)}")
            return results
    
    def _serialize_value(self, value: Any, config_type: str) -> str:
        """序列化配置值"""
        if config_type == 'json':
            return json.dumps(value, ensure_ascii=False)
        elif config_type == 'bool':
            return 'true' if value else 'false'
        else:
            return str(value)
    
    def _deserialize_value(self, value: str, config_type: str) -> Any:
        """反序列化配置值"""
        if not value:
            return None
        
        try:
            if config_type == 'int':
                return int(value)
            elif config_type == 'float':
                return float(value)
            elif config_type == 'bool':
                return value.lower() in ('true', '1', 'yes', 'on')
            elif config_type == 'json':
                return json.loads(value)
            else:
                return value
        except (ValueError, json.JSONDecodeError) as e:
            logger.error(f"反序列化配置值失败: {value}, type: {config_type}, error: {str(e)}")
            return value


# 创建全局配置服务实例
config_service = SystemConfigService()