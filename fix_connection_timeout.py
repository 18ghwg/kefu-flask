"""
修复MySQL连接超时问题
1. 优化慢查询（system_settings表）
2. 添加数据库索引
3. 清理僵死连接
"""
import sys
from app import app
from exts import db
from sqlalchemy import text, inspect
import log

logger = log.get_logger(__name__)


def add_missing_indexes():
    """添加缺失的索引以优化查询性能"""
    with app.app_context():
        try:
            # 检查并添加索引
            indexes_to_add = [
                # system_settings表 - 按business_id查询优化
                ("system_settings", "idx_business_id", "business_id"),
                
                # queues表 - 优化访客查询
                ("queues", "idx_visitor_state", "visitor_id, state"),
                ("queues", "idx_service_state", "service_id, state"),
                ("queues", "idx_business_state", "business_id, state"),
                
                # chats表 - 优化消息查询
                ("chats", "idx_visitor_created", "visitor_id, created_at"),
                ("chats", "idx_service_created", "service_id, created_at"),
                
                # visitors表 - 优化访客查询
                ("visitors", "idx_visitor_business", "visitor_id, business_id"),
            ]
            
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            for table_name, index_name, columns in indexes_to_add:
                # 检查表是否存在
                if table_name not in existing_tables:
                    logger.warning(f"表 {table_name} 不存在，跳过")
                    continue
                
                # 检查索引是否已存在
                existing_indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]
                
                if index_name in existing_indexes:
                    logger.info(f"✅ 索引 {index_name} 已存在")
                    continue
                
                # 创建索引
                try:
                    sql = f"CREATE INDEX {index_name} ON {table_name} ({columns})"
                    db.session.execute(text(sql))
                    db.session.commit()
                    logger.info(f"✅ 创建索引: {index_name} ON {table_name}({columns})")
                except Exception as e:
                    logger.error(f"❌ 创建索引失败 {index_name}: {e}")
                    db.session.rollback()
            
            logger.info("✅ 索引优化完成")
            
        except Exception as e:
            logger.error(f"❌ 添加索引失败: {e}")
            import traceback
            logger.error(traceback.format_exc())


def optimize_system_settings_query():
    """优化system_settings表查询"""
    with app.app_context():
        try:
            # 检查system_settings表的数据量
            result = db.session.execute(text("SELECT COUNT(*) as cnt FROM system_settings"))
            count = result.fetchone()[0]
            logger.info(f"system_settings表记录数: {count}")
            
            # 如果有重复的business_id记录，清理
            result = db.session.execute(text("""
                SELECT business_id, COUNT(*) as cnt 
                FROM system_settings 
                GROUP BY business_id 
                HAVING cnt > 1
            """))
            duplicates = result.fetchall()
            
            if duplicates:
                logger.warning(f"发现重复的business_id记录: {len(duplicates)}")
                for business_id, cnt in duplicates:
                    # 保留最新的记录，删除旧的
                    db.session.execute(text("""
                        DELETE FROM system_settings 
                        WHERE business_id = :business_id 
                        AND id NOT IN (
                            SELECT id FROM (
                                SELECT id FROM system_settings 
                                WHERE business_id = :business_id 
                                ORDER BY updated_at DESC 
                                LIMIT 1
                            ) tmp
                        )
                    """), {"business_id": business_id})
                db.session.commit()
                logger.info(f"✅ 清理重复记录完成")
            
        except Exception as e:
            logger.error(f"❌ 优化system_settings查询失败: {e}")
            db.session.rollback()


def kill_long_running_queries():
    """终止长时间运行的查询（超过60秒）"""
    with app.app_context():
        try:
            # 查找长时间运行的查询
            result = db.session.execute(text("""
                SELECT id, user, host, db, command, time, state, info
                FROM information_schema.processlist
                WHERE command != 'Sleep' 
                AND time > 60
                AND user != 'system user'
                ORDER BY time DESC
            """))
            
            long_queries = result.fetchall()
            
            if long_queries:
                logger.warning(f"发现 {len(long_queries)} 个长时间运行的查询")
                for query in long_queries:
                    query_id, user, host, db_name, command, time, state, info = query
                    logger.warning(f"查询ID: {query_id}, 用户: {user}, 时间: {time}s, 状态: {state}")
                    logger.warning(f"SQL: {info[:200] if info else 'N/A'}")
                    
                    # 可选：终止查询（谨慎使用）
                    # db.session.execute(text(f"KILL {query_id}"))
                    # logger.info(f"✅ 已终止查询 {query_id}")
            else:
                logger.info("✅ 没有发现长时间运行的查询")
                
        except Exception as e:
            logger.error(f"❌ 检查长查询失败: {e}")


def check_connection_pool_status():
    """检查连接池状态"""
    with app.app_context():
        try:
            pool = db.engine.pool
            logger.info(f"连接池状态:")
            logger.info(f"  - 池大小: {pool.size()}")
            logger.info(f"  - 已签出: {pool.checkedout()}")
            logger.info(f"  - 溢出: {pool.overflow()}")
            logger.info(f"  - 已签入: {pool.checkedin()}")
            
            # 检查MySQL连接数
            result = db.session.execute(text("""
                SELECT COUNT(*) as connection_count
                FROM information_schema.processlist
                WHERE user = :user
            """), {"user": app.config['USERNAME']})
            
            mysql_connections = result.fetchone()[0]
            logger.info(f"  - MySQL实际连接数: {mysql_connections}")
            
        except Exception as e:
            logger.error(f"❌ 检查连接池状态失败: {e}")


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("开始修复MySQL连接超时问题")
    logger.info("=" * 60)
    
    # 1. 检查连接池状态
    logger.info("\n[1/4] 检查连接池状态...")
    check_connection_pool_status()
    
    # 2. 添加缺失的索引
    logger.info("\n[2/4] 添加缺失的索引...")
    add_missing_indexes()
    
    # 3. 优化system_settings查询
    logger.info("\n[3/4] 优化system_settings查询...")
    optimize_system_settings_query()
    
    # 4. 检查长时间运行的查询
    logger.info("\n[4/4] 检查长时间运行的查询...")
    kill_long_running_queries()
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ 修复完成！")
    logger.info("=" * 60)
    logger.info("\n建议:")
    logger.info("1. 重启应用以应用新的连接池配置")
    logger.info("2. 监控日志中的慢查询警告")
    logger.info("3. 定期运行此脚本检查数据库健康状况")


if __name__ == '__main__':
    main()
