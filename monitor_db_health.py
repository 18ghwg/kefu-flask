"""
数据库健康监控脚本
实时监控连接池状态和慢查询
"""
import time
import sys
from datetime import datetime
from app import app
from exts import db
from sqlalchemy import text, event
from sqlalchemy.pool import Pool
import log

logger = log.get_logger(__name__)


class DatabaseHealthMonitor:
    """数据库健康监控器"""
    
    def __init__(self):
        self.slow_query_threshold = 1.0  # 慢查询阈值（秒）
        self.check_interval = 30  # 检查间隔（秒）
        
    def setup_query_logging(self):
        """设置查询日志监听"""
        @event.listens_for(Pool, "connect")
        def receive_connect(dbapi_conn, connection_record):
            logger.debug(f"新连接建立: {id(dbapi_conn)}")
        
        @event.listens_for(Pool, "checkout")
        def receive_checkout(dbapi_conn, connection_record, connection_proxy):
            logger.debug(f"连接签出: {id(dbapi_conn)}")
        
        @event.listens_for(Pool, "checkin")
        def receive_checkin(dbapi_conn, connection_record):
            logger.debug(f"连接签入: {id(dbapi_conn)}")
    
    def check_pool_status(self):
        """检查连接池状态"""
        try:
            pool = db.engine.pool
            status = {
                'size': pool.size(),
                'checkedout': pool.checkedout(),
                'overflow': pool.overflow(),
                'checkedin': pool.checkedin(),
                'timestamp': datetime.now().isoformat()
            }
            
            # 计算使用率
            total_available = status['size'] + status['overflow']
            usage_rate = (status['checkedout'] / total_available * 100) if total_available > 0 else 0
            
            status['usage_rate'] = round(usage_rate, 2)
            
            # 警告阈值
            if usage_rate > 80:
                logger.warning(f"⚠️ 连接池使用率过高: {usage_rate}%")
            elif usage_rate > 60:
                logger.info(f"📊 连接池使用率: {usage_rate}%")
            
            return status
            
        except Exception as e:
            logger.error(f"检查连接池状态失败: {e}")
            return None
    
    def check_mysql_connections(self):
        """检查MySQL实际连接数"""
        try:
            with app.app_context():
                # 当前用户的连接数
                result = db.session.execute(text("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN command = 'Sleep' THEN 1 ELSE 0 END) as sleeping,
                        SUM(CASE WHEN command != 'Sleep' THEN 1 ELSE 0 END) as active,
                        MAX(time) as max_time
                    FROM information_schema.processlist
                    WHERE user = :user
                """), {"user": app.config.get('USERNAME', 'root')})
                
                row = result.fetchone()
                
                status = {
                    'total': row[0],
                    'sleeping': row[1] or 0,
                    'active': row[2] or 0,
                    'max_time': row[3] or 0,
                    'timestamp': datetime.now().isoformat()
                }
                
                if status['max_time'] > 60:
                    logger.warning(f"⚠️ 发现长时间运行的查询: {status['max_time']}秒")
                
                return status
                
        except Exception as e:
            logger.error(f"检查MySQL连接失败: {e}")
            return None
    
    def check_slow_queries(self):
        """检查慢查询"""
        try:
            with app.app_context():
                result = db.session.execute(text("""
                    SELECT 
                        id, user, host, db, command, time, state, 
                        LEFT(info, 200) as query_preview
                    FROM information_schema.processlist
                    WHERE command != 'Sleep' 
                    AND time > :threshold
                    AND user != 'system user'
                    ORDER BY time DESC
                    LIMIT 10
                """), {"threshold": self.slow_query_threshold})
                
                slow_queries = result.fetchall()
                
                if slow_queries:
                    logger.warning(f"🐌 发现 {len(slow_queries)} 个慢查询:")
                    for query in slow_queries:
                        query_id, user, host, db_name, command, time, state, preview = query
                        logger.warning(f"  ID:{query_id} | 时间:{time}s | 状态:{state}")
                        logger.warning(f"  SQL: {preview}")
                
                return slow_queries
                
        except Exception as e:
            logger.error(f"检查慢查询失败: {e}")
            return []
    
    def check_table_locks(self):
        """检查表锁"""
        try:
            with app.app_context():
                result = db.session.execute(text("""
                    SELECT 
                        r.trx_id waiting_trx_id,
                        r.trx_mysql_thread_id waiting_thread,
                        r.trx_query waiting_query,
                        b.trx_id blocking_trx_id,
                        b.trx_mysql_thread_id blocking_thread,
                        b.trx_query blocking_query
                    FROM information_schema.innodb_lock_waits w
                    INNER JOIN information_schema.innodb_trx b ON b.trx_id = w.blocking_trx_id
                    INNER JOIN information_schema.innodb_trx r ON r.trx_id = w.requesting_trx_id
                """))
                
                locks = result.fetchall()
                
                if locks:
                    logger.warning(f"🔒 发现 {len(locks)} 个表锁:")
                    for lock in locks:
                        logger.warning(f"  等待事务: {lock[0]} (线程:{lock[1]})")
                        logger.warning(f"  阻塞事务: {lock[3]} (线程:{lock[4]})")
                
                return locks
                
        except Exception as e:
            # 某些MySQL版本可能不支持innodb_lock_waits
            logger.debug(f"检查表锁失败（可能不支持）: {e}")
            return []
    
    def print_status_report(self, pool_status, mysql_status):
        """打印状态报告"""
        print("\n" + "=" * 60)
        print(f"数据库健康报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        if pool_status:
            print("\n📊 连接池状态:")
            print(f"  池大小: {pool_status['size']}")
            print(f"  已签出: {pool_status['checkedout']}")
            print(f"  溢出连接: {pool_status['overflow']}")
            print(f"  已签入: {pool_status['checkedin']}")
            print(f"  使用率: {pool_status['usage_rate']}%")
        
        if mysql_status:
            print("\n🔌 MySQL连接:")
            print(f"  总连接数: {mysql_status['total']}")
            print(f"  活跃连接: {mysql_status['active']}")
            print(f"  休眠连接: {mysql_status['sleeping']}")
            print(f"  最长查询: {mysql_status['max_time']}秒")
        
        print("\n" + "=" * 60)
    
    def run_continuous_monitoring(self):
        """持续监控"""
        logger.info("🚀 启动数据库健康监控...")
        logger.info(f"检查间隔: {self.check_interval}秒")
        logger.info(f"慢查询阈值: {self.slow_query_threshold}秒")
        
        try:
            while True:
                # 检查连接池
                pool_status = self.check_pool_status()
                
                # 检查MySQL连接
                mysql_status = self.check_mysql_connections()
                
                # 检查慢查询
                self.check_slow_queries()
                
                # 检查表锁
                self.check_table_locks()
                
                # 打印报告
                self.print_status_report(pool_status, mysql_status)
                
                # 等待下次检查
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            logger.info("\n⏹️ 监控已停止")
        except Exception as e:
            logger.error(f"监控异常: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def run_single_check(self):
        """单次检查"""
        logger.info("🔍 执行单次健康检查...")
        
        # 检查连接池
        pool_status = self.check_pool_status()
        
        # 检查MySQL连接
        mysql_status = self.check_mysql_connections()
        
        # 检查慢查询
        slow_queries = self.check_slow_queries()
        
        # 检查表锁
        locks = self.check_table_locks()
        
        # 打印报告
        self.print_status_report(pool_status, mysql_status)
        
        # 返回健康状态
        is_healthy = True
        issues = []
        
        if pool_status and pool_status['usage_rate'] > 80:
            is_healthy = False
            issues.append(f"连接池使用率过高: {pool_status['usage_rate']}%")
        
        if mysql_status and mysql_status['max_time'] > 60:
            is_healthy = False
            issues.append(f"存在长时间运行的查询: {mysql_status['max_time']}秒")
        
        if slow_queries:
            is_healthy = False
            issues.append(f"发现 {len(slow_queries)} 个慢查询")
        
        if locks:
            is_healthy = False
            issues.append(f"发现 {len(locks)} 个表锁")
        
        if is_healthy:
            logger.info("✅ 数据库健康状况良好")
        else:
            logger.warning("⚠️ 数据库存在以下问题:")
            for issue in issues:
                logger.warning(f"  - {issue}")
        
        return is_healthy


def main():
    """主函数"""
    monitor = DatabaseHealthMonitor()
    
    if len(sys.argv) > 1 and sys.argv[1] == '--continuous':
        # 持续监控模式
        monitor.run_continuous_monitoring()
    else:
        # 单次检查模式
        monitor.run_single_check()


if __name__ == '__main__':
    main()
