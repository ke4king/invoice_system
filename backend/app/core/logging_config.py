"""
Logging configuration with proper UTF-8 encoding support
"""
import logging
import logging.config
import sys
import os
from typing import Dict, Any


def configure_logging(log_level: str = "INFO") -> None:
    """配置日志系统，确保支持UTF-8编码"""
    
    # 确保stdout和stderr使用UTF-8编码
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
    
    # 配置日志格式
    logging_config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            }
        },
        "handlers": {
            "console": {
                "level": log_level,
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": "ext://sys.stdout",
                "encoding": "utf-8"  # 显式指定UTF-8编码
            },
            "error_console": {
                "level": "ERROR",
                "class": "logging.StreamHandler", 
                "formatter": "detailed",
                "stream": "ext://sys.stderr",
                "encoding": "utf-8"  # 显式指定UTF-8编码
            }
        },
        "loggers": {
            "": {  # root logger
                "handlers": ["console", "error_console"],
                "level": log_level,
                "propagate": False
            },
            "app": {
                "handlers": ["console", "error_console"],
                "level": log_level,
                "propagate": False
            },
            "uvicorn": {
                "handlers": ["console"],
                "level": log_level,
                "propagate": False
            },
            "uvicorn.access": {
                "handlers": ["console"],
                "level": log_level,
                "propagate": False
            }
        }
    }
    
    try:
        logging.config.dictConfig(logging_config)
        # 测试日志是否正常工作
        logger = logging.getLogger("app.logging_config")
        logger.info("日志系统初始化完成 - UTF-8编码支持已启用")
    except Exception as e:
        # 如果配置失败，使用基本配置
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            stream=sys.stdout,
            encoding='utf-8'
        )
        logger = logging.getLogger("app.logging_config")
        logger.warning(f"使用基本日志配置: {str(e)}")


def get_logger(name: str) -> logging.Logger:
    """获取配置好的logger实例"""
    return logging.getLogger(name)