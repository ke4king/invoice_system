from pydantic_settings import BaseSettings
from typing import List, Optional
import os


def get_absolute_file_path(relative_path: str) -> str:
    """将相对路径转换为绝对路径"""
    if os.path.isabs(relative_path):
        return relative_path
    
    # 获取当前的UPLOAD_DIR基础路径
    upload_dir = os.getenv("UPLOAD_DIR", os.path.abspath(os.path.join(os.getcwd(), "storage")))
    base_dir = os.path.dirname(upload_dir)  # 获取storage的上级目录
    
    return os.path.join(base_dir, relative_path)


def get_relative_file_path(absolute_path: str) -> str:
    """将绝对路径转换为相对路径"""
    if not os.path.isabs(absolute_path):
        return absolute_path
    
    # 获取当前的UPLOAD_DIR基础路径
    upload_dir = os.getenv("UPLOAD_DIR", os.path.abspath(os.path.join(os.getcwd(), "storage")))
    base_dir = os.path.dirname(upload_dir)  # 获取storage的上级目录
    
    return os.path.relpath(absolute_path, base_dir)


class Settings(BaseSettings):
    # 应用基础配置
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key")
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # 数据库配置
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://invoice_user:invoice_pass_2024_secure@localhost:3306/invoice_system"
    )
    
    # Redis配置
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # CORS配置
    ALLOWED_HOSTS: List[str] = ["*"]  # 生产环境应该限制具体域名
    
    # 文件存储配置
    # 默认以当前工作目录下的 storage 目录作为根，生产通过环境变量覆盖
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", os.path.abspath(os.path.join(os.getcwd(), "storage")))
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB
    ALLOWED_FILE_TYPES: List[str] = ["pdf"]
    
    # 百度OCR配置
    BAIDU_OCR_API_KEY: Optional[str] = os.getenv("BAIDU_OCR_API_KEY")
    BAIDU_OCR_SECRET_KEY: Optional[str] = os.getenv("BAIDU_OCR_SECRET_KEY")
    
    # OCR配置
    OCR_RETRY_TIMES: int = int(os.getenv("OCR_RETRY_TIMES", "3"))
    OCR_TIMEOUT: int = int(os.getenv("OCR_TIMEOUT", "30"))
    OCR_AMOUNT_IN_CENTS: bool = os.getenv("OCR_AMOUNT_IN_CENTS", "false").lower() == "true"
    OCR_QPS_LIMIT: int = int(os.getenv("OCR_QPS_LIMIT", "2"))
    
    # 邮箱配置
    DEFAULT_EMAIL_SERVER: str = os.getenv("DEFAULT_EMAIL_SERVER", "imap.gmail.com")
    DEFAULT_EMAIL_PORT: int = int(os.getenv("DEFAULT_EMAIL_PORT", "993"))
    EMAIL_ENCRYPTION_KEY: Optional[str] = os.getenv("EMAIL_ENCRYPTION_KEY")
    
    # 管理员配置
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@example.com")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "change_me_in_production")
    
    # 日志配置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE_MAX_SIZE: str = os.getenv("LOG_FILE_MAX_SIZE", "10MB")
    LOG_FILE_BACKUP_COUNT: int = int(os.getenv("LOG_FILE_BACKUP_COUNT", "5"))

    # Cookie/健康检查/限流
    USE_COOKIE_AUTH: bool = os.getenv("USE_COOKIE_AUTH", "false").lower() == "true"
    COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    COOKIE_SAMESITE: str = os.getenv("COOKIE_SAMESITE", "lax")
    HEALTH_REQUIRE_AUTH: bool = os.getenv("HEALTH_REQUIRE_AUTH", "false").lower() == "true"
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()