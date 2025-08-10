"""
数据库初始化脚本
创建默认管理员用户
"""
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.core.security import get_password_hash
from app.models.user import User
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


def init_db():
    """初始化数据库"""
    db = SessionLocal()
    try:
        # 检查是否已存在管理员用户
        admin_user = db.query(User).filter(User.username == settings.ADMIN_USERNAME).first()
        
        if not admin_user:
            # 创建默认管理员用户
            admin_user = User(
                username=settings.ADMIN_USERNAME,
                email=settings.ADMIN_EMAIL,
                hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
                is_active=True,
                is_superuser=True
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            logger.info(f"创建默认管理员用户: {settings.ADMIN_USERNAME}")
        else:
            logger.info("管理员用户已存在")
            
    except Exception as e:
        logger.error(f"初始化数据库失败: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_db()