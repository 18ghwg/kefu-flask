"""
数据库健康检查任务
"""
from exts import app, db
import log

logger = log.get_logger(__name__)


def check_db_health():
    """
    数据库健康检查
    每3分钟执行一次简单查询，保持连接池活跃
    防止连接超时导致的"冷启动"延迟
    """
    try:
        with app.app_context():
            db.session.execute(db.text("SELECT 1"))
            db.session.commit()
            logger.debug("✅ 数据库健康检查通过")
    except Exception as e:
        logger.error(f"❌ 数据库健康检查失败: {e}")
