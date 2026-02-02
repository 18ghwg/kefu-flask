"""
进一步优化慢查询
针对 COUNT(DISTINCT visitor_id) 的更激进优化方案
"""
from app import app
from exts import db, redis_client
from sqlalchemy import text
from datetime import datetime, timedelta
import json
import log

logger = log.get_logger(__name__)


def check_indexes():
    """检查索引是否已创建"""
    with app.app_context():
        try:
            result = db.session.execute(text("SHOW INDEX FROM chats"))
            indexes = [row[2] for row in result]
            
            logger.info("当前chats表的索引:")
            for idx in set(indexes):
                logger.info(f"  - {idx}")
            
            required_indexes = [
                'idx_chats_business_visitor',
                'idx_chats_business_timestamp',
                'idx_chats_visitor_timestamp',
                'idx_chats_timestamp'
            ]
            
            missing = [idx for idx in required_indexes if idx not in indexes]
            
            if missing:
                logger.warning(f"⚠️ 缺少索引: {', '.join(missing)}")
                logger.info("请运行: python optimize_slow_queries.py")
                return False
            else:
                logger.info("✅ 所有索引都已创建")
                return True
                
        except Exception as e:
            logger.error(f"检查索引失败: {e}")
            return False


def analyze_query_performance():
    """分析查询性能"""
    with app.app_context():
        try:
            # 测试当前查询
            thirty_days_ago = int((datetime.now() - timedelta(days=30)).timestamp())
            
            logger.info("测试查询性能...")
            
            # 使用EXPLAIN分析查询
            result = db.session.execute(text("""
                EXPLAIN SELECT COUNT(DISTINCT visitor_id) 
                FROM chats 
                WHERE business_id = 1 
                AND timestamp >= :timestamp
            """), {"timestamp": thirty_days_ago})
            
            logger.info("查询执行计划:")
            for row in result:
                logger.info(f"  {row}")
            
            # 测试查询时间
            import time
            start = time.time()
            
            result = db.session.execute(text("""
                SELECT COUNT(DISTINCT visitor_id) 
                FROM chats 
                WHERE business_id = 1 
                AND timestamp >= :timestamp
            """), {"timestamp": thirty_days_ago})
            
            count = result.fetchone()[0]
            duration = time.time() - start
            
            logger.info(f"查询结果: {count} 个访客")
            logger.info(f"查询时间: {duration:.3f}秒")
            
            if duration > 0.5:
                logger.warning("⚠️ 查询时间仍然较慢，建议使用缓存或近似算法")
            else:
                logger.info("✅ 查询性能良好")
            
            return duration
            
        except Exception as e:
            logger.error(f"性能分析失败: {e}")
            return None


def create_summary_table():
    """
    创建汇总表（物化视图）
    每小时更新一次，大幅提升查询速度
    """
    with app.app_context():
        try:
            logger.info("创建访客统计汇总表...")
            
            # 创建汇总表
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS visitor_stats_cache (
                    business_id INT NOT NULL,
                    stat_date DATE NOT NULL,
                    visitor_count INT NOT NULL DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (business_id, stat_date),
                    INDEX idx_business_date (business_id, stat_date)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """))
            
            db.session.commit()
            logger.info("✅ 汇总表创建成功")
            
            # 初始化数据
            logger.info("初始化汇总数据...")
            
            # 统计最近30天的数据
            for i in range(30):
                date = datetime.now() - timedelta(days=i)
                day_start = int(datetime.combine(date, datetime.min.time()).timestamp())
                day_end = day_start + 86400 - 1
                
                result = db.session.execute(text("""
                    SELECT COUNT(DISTINCT visitor_id) 
                    FROM chats 
                    WHERE business_id = 1 
                    AND timestamp >= :start 
                    AND timestamp <= :end
                """), {"start": day_start, "end": day_end})
                
                count = result.fetchone()[0]
                
                # 插入或更新
                db.session.execute(text("""
                    INSERT INTO visitor_stats_cache (business_id, stat_date, visitor_count)
                    VALUES (1, :date, :count)
                    ON DUPLICATE KEY UPDATE visitor_count = :count
                """), {"date": date.date(), "count": count})
                
                if i % 5 == 0:
                    logger.info(f"已处理 {i+1}/30 天...")
            
            db.session.commit()
            logger.info("✅ 汇总数据初始化完成")
            
            # 提供使用示例
            logger.info("\n使用汇总表的查询示例:")
            logger.info("""
# 在 StatisticsServiceClass.py 中使用:

# 方法1: 使用汇总表（推荐）
total_visitors = db.session.execute(text('''
    SELECT SUM(visitor_count) 
    FROM visitor_stats_cache 
    WHERE business_id = :business_id 
    AND stat_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
'''), {"business_id": self.business_id}).scalar() or 0

# 方法2: 如果汇总表不存在，回退到原查询
try:
    total_visitors = db.session.execute(text('''
        SELECT SUM(visitor_count) 
        FROM visitor_stats_cache 
        WHERE business_id = :business_id 
        AND stat_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
    '''), {"business_id": self.business_id}).scalar() or 0
except:
    # 回退到原查询
    thirty_days_ago = int((datetime.now() - timedelta(days=30)).timestamp())
    total_visitors = db.session.query(
        func.count(distinct(Chat.visitor_id))
    ).filter(
        Chat.business_id == self.business_id,
        Chat.timestamp >= thirty_days_ago
    ).scalar() or 0
            """)
            
        except Exception as e:
            logger.error(f"创建汇总表失败: {e}")
            db.session.rollback()
            import traceback
            logger.error(traceback.format_exc())


def use_redis_hyperloglog():
    """
    使用Redis HyperLogLog进行近似统计
    误差<1%，性能极高
    """
    if not redis_client:
        logger.warning("Redis未配置，跳过HyperLogLog示例")
        return
    
    logger.info("\nRedis HyperLogLog使用示例:")
    logger.info("""
# 在聊天消息处理时，添加访客到HyperLogLog:

from exts import redis_client

# 每次有新消息时
redis_client.pfadd(f'visitors:{business_id}', visitor_id)

# 获取去重访客数（近似值，误差<1%）
count = redis_client.pfcount(f'visitors:{business_id}')

# 定期清理（每月1号）
if datetime.now().day == 1:
    redis_client.delete(f'visitors:{business_id}')

# 优点:
# - 查询速度: O(1)，毫秒级
# - 内存占用: 每个HyperLogLog只需12KB
# - 误差率: <1%
# - 适合大数据量统计
    """)


def optimize_cache_strategy():
    """优化缓存策略"""
    logger.info("\n缓存策略优化建议:")
    logger.info("""
1. 增加缓存时间到300秒（5分钟）
   - 实时性要求不高的统计数据
   - 大幅减少数据库查询

2. 使用多级缓存
   - L1: 内存缓存（1分钟）
   - L2: Redis缓存（5分钟）
   - L3: 数据库查询

3. 缓存预热
   - 应用启动时预先加载常用统计
   - 避免冷启动时的慢查询

示例代码:

# 在 StatisticsServiceClass.py 中:

def get_realtime_stats(self):
    # 尝试从缓存获取
    cache_key = f"dashboard:{self.business_id}:realtime"
    
    if redis_client:
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
    
    # 查询数据库
    result = {
        'waiting_count': ...,
        'chatting_count': ...,
        'online_services': ...,
        'total_visitors': ...  # 使用汇总表或HyperLogLog
    }
    
    # 缓存300秒（5分钟）
    if redis_client:
        redis_client.setex(cache_key, 300, json.dumps(result))
    
    return result
    """)


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("进一步优化慢查询")
    logger.info("=" * 60)
    
    # 1. 检查索引
    logger.info("\n[1/5] 检查索引...")
    has_indexes = check_indexes()
    
    # 2. 分析查询性能
    logger.info("\n[2/5] 分析查询性能...")
    duration = analyze_query_performance()
    
    # 3. 创建汇总表
    if duration and duration > 0.5:
        logger.info("\n[3/5] 创建汇总表...")
        create_summary_table()
    else:
        logger.info("\n[3/5] 查询性能良好，跳过汇总表创建")
    
    # 4. HyperLogLog示例
    logger.info("\n[4/5] Redis HyperLogLog示例...")
    use_redis_hyperloglog()
    
    # 5. 缓存策略优化
    logger.info("\n[5/5] 缓存策略优化...")
    optimize_cache_strategy()
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ 分析完成！")
    logger.info("=" * 60)
    
    logger.info("\n推荐方案:")
    if duration and duration > 0.5:
        logger.info("1. 使用汇总表（visitor_stats_cache）- 已创建")
        logger.info("2. 增加缓存时间到300秒")
        logger.info("3. 考虑使用Redis HyperLogLog")
    else:
        logger.info("1. 当前性能已经不错")
        logger.info("2. 可以增加缓存时间到300秒进一步优化")


if __name__ == '__main__':
    main()
