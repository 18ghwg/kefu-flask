"""
数据库健康检查任务
"""
from exts import app, db
from sqlalchemy import text
from datetime import datetime
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
            db.session.execute(text("SELECT 1"))
            db.session.commit()
            logger.debug("✅ 数据库健康检查通过")
    except Exception as e:
        logger.error(f"❌ 数据库健康检查失败: {e}")
    finally:
        # ✅ 关键修复：清理数据库会话，释放连接
        try:
            db.session.remove()
        except:
            pass


def cleanup_connection_pool():
    """
    清理连接池
    每10分钟执行一次，清理僵死连接和过期连接
    优化连接池健康状况
    """
    try:
        with app.app_context():
            pool = db.engine.pool
            
            # 获取连接池状态
            pool_size = pool.size()
            checked_out = pool.checkedout()
            overflow = pool.overflow()
            
            logger.info(f"🔍 连接池状态检查 - 池大小:{pool_size}, 已签出:{checked_out}, 溢出:{overflow}")
            
            # 1. 清理所有会话（释放未正确关闭的连接）
            db.session.remove()
            
            # 2. 回收过期连接（pool_recycle会自动处理，这里只是触发检查）
            # 执行一个简单查询来触发连接池的健康检查
            db.session.execute(text("SELECT 1"))
            db.session.commit()
            
            # 3. 检查MySQL端的连接数
            try:
                result = db.session.execute(text("""
                    SELECT COUNT(*) as connection_count
                    FROM information_schema.processlist
                    WHERE user = :user AND command = 'Sleep' AND time > 60
                """), {"user": app.config.get('USERNAME', 'kefu_flask')})
                
                idle_connections = result.fetchone()[0]
                
                if idle_connections > 10:
                    logger.warning(f"⚠️ 发现 {idle_connections} 个空闲超过60秒的连接")
                    
                    # 可选：终止长时间空闲的连接（谨慎使用）
                    # result = db.session.execute(text("""
                    #     SELECT id FROM information_schema.processlist
                    #     WHERE user = :user AND command = 'Sleep' AND time > 300
                    # """), {"user": app.config.get('USERNAME', 'kefu_flask')})
                    # 
                    # for row in result:
                    #     db.session.execute(text(f"KILL {row[0]}"))
                    #     logger.info(f"🔪 终止空闲连接: {row[0]}")
                
            except Exception as e:
                logger.debug(f"检查MySQL连接数失败（可能权限不足）: {e}")
            
            # 4. 记录清理完成
            new_checked_out = pool.checkedout()
            released = checked_out - new_checked_out
            
            if released > 0:
                logger.info(f"✅ 连接池清理完成 - 释放了 {released} 个连接")
            else:
                logger.debug(f"✅ 连接池清理完成 - 状态正常")
                
    except Exception as e:
        logger.error(f"❌ 连接池清理失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        # ✅ 确保清理会话
        try:
            db.session.remove()
        except:
            pass


def check_slow_queries():
    """
    检查慢查询
    每15分钟执行一次，检测并记录慢查询
    帮助识别性能问题
    """
    try:
        with app.app_context():
            # 检查当前正在运行的慢查询（超过5秒）
            result = db.session.execute(text("""
                SELECT 
                    id, user, host, db, command, time, state,
                    LEFT(info, 200) as query_preview
                FROM information_schema.processlist
                WHERE command != 'Sleep' 
                AND time > 5
                AND user != 'system user'
                ORDER BY time DESC
                LIMIT 5
            """))
            
            slow_queries = result.fetchall()
            
            if slow_queries:
                logger.warning(f"🐌 发现 {len(slow_queries)} 个慢查询:")
                for query in slow_queries:
                    query_id, user, host, db_name, command, time, state, preview = query
                    logger.warning(f"  ID:{query_id} | 用户:{user} | 时间:{time}秒 | 状态:{state}")
                    logger.warning(f"  SQL: {preview}")
            else:
                logger.debug("✅ 未发现慢查询")
                
    except Exception as e:
        logger.debug(f"检查慢查询失败（可能权限不足）: {e}")
    finally:
        try:
            db.session.remove()
        except:
            pass


def monitor_connection_pool():
    """
    监控连接池状态
    每5分钟执行一次，监控连接池使用率
    当使用率过高时发出警告
    """
    try:
        with app.app_context():
            pool = db.engine.pool
            
            pool_size = pool.size()
            checked_out = pool.checkedout()
            overflow = pool.overflow()
            
            # 计算使用率
            total_available = pool_size + overflow
            usage_rate = (checked_out / total_available * 100) if total_available > 0 else 0
            
            # 记录状态
            status_msg = f"📊 连接池监控 - 使用率:{usage_rate:.1f}% ({checked_out}/{total_available})"
            
            if usage_rate > 80:
                logger.warning(f"⚠️ {status_msg} - 使用率过高！")
            elif usage_rate > 60:
                logger.info(f"⚡ {status_msg} - 使用率较高")
            else:
                logger.debug(status_msg)
            
            # 检查MySQL实际连接数
            try:
                result = db.session.execute(text("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN command = 'Sleep' THEN 1 ELSE 0 END) as sleeping,
                        SUM(CASE WHEN command != 'Sleep' THEN 1 ELSE 0 END) as active
                    FROM information_schema.processlist
                    WHERE user = :user
                """), {"user": app.config.get('USERNAME', 'kefu_flask')})
                
                row = result.fetchone()
                total, sleeping, active = row[0], row[1] or 0, row[2] or 0
                
                logger.debug(f"🔌 MySQL连接 - 总数:{total}, 活跃:{active}, 休眠:{sleeping}")
                
                # 如果MySQL连接数远大于连接池大小，可能有连接泄漏
                if total > (pool_size + overflow) * 1.5:
                    logger.warning(f"⚠️ MySQL连接数({total})远大于连接池配置({pool_size}+{overflow})，可能存在连接泄漏！")
                    
            except Exception as e:
                logger.debug(f"检查MySQL连接数失败: {e}")
                
    except Exception as e:
        logger.error(f"❌ 连接池监控失败: {e}")
    finally:
        try:
            db.session.remove()
        except:
            pass
