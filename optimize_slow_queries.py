"""
优化慢查询 - 添加索引和缓存
解决 COUNT(DISTINCT visitor_id) 慢查询问题
"""
from app import app
from exts import db
from sqlalchemy import text, inspect
import log

logger = log.get_logger(__name__)


def add_chats_indexes():
    """为chats表添加优化索引"""
    with app.app_context():
        try:
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            if 'chats' not in existing_tables:
                logger.warning("chats表不存在")
                return
            
            # 获取现有索引
            existing_indexes = [idx['name'] for idx in inspector.get_indexes('chats')]
            
            # 需要添加的索引
            indexes_to_add = [
                # 优化 business_id + visitor_id 查询（用于去重统计）
                ("idx_chats_business_visitor", "business_id, visitor_id"),
                
                # 优化 business_id + timestamp 查询（用于时间范围统计）
                ("idx_chats_business_timestamp", "business_id, timestamp"),
                
                # 优化 visitor_id + timestamp 查询
                ("idx_chats_visitor_timestamp", "visitor_id, timestamp"),
                
                # 优化 timestamp 查询（用于日期范围）
                ("idx_chats_timestamp", "timestamp"),
            ]
            
            for index_name, columns in indexes_to_add:
                if index_name in existing_indexes:
                    logger.info(f"✅ 索引 {index_name} 已存在")
                    continue
                
                try:
                    sql = f"CREATE INDEX {index_name} ON chats ({columns})"
                    db.session.execute(text(sql))
                    db.session.commit()
                    logger.info(f"✅ 创建索引: {index_name} ON chats({columns})")
                except Exception as e:
                    logger.error(f"❌ 创建索引失败 {index_name}: {e}")
                    db.session.rollback()
            
            logger.info("✅ chats表索引优化完成")
            
        except Exception as e:
            logger.error(f"❌ 添加索引失败: {e}")
            import traceback
            logger.error(traceback.format_exc())


def analyze_chats_table():
    """分析chats表的数据量和查询性能"""
    with app.app_context():
        try:
            # 1. 统计总记录数
            result = db.session.execute(text("SELECT COUNT(*) as cnt FROM chats"))
            total_count = result.fetchone()[0]
            logger.info(f"📊 chats表总记录数: {total_count:,}")
            
            # 2. 统计不同访客数
            result = db.session.execute(text("SELECT COUNT(DISTINCT visitor_id) as cnt FROM chats"))
            distinct_visitors = result.fetchone()[0]
            logger.info(f"📊 不同访客数: {distinct_visitors:,}")
            
            # 3. 按business_id统计
            result = db.session.execute(text("""
                SELECT business_id, COUNT(*) as cnt, COUNT(DISTINCT visitor_id) as visitors
                FROM chats
                GROUP BY business_id
            """))
            
            logger.info("📊 按业务统计:")
            for row in result:
                business_id, cnt, visitors = row
                logger.info(f"  business_id={business_id}: 消息数={cnt:,}, 访客数={visitors:,}")
            
            # 4. 检查索引使用情况
            result = db.session.execute(text("""
                SHOW INDEX FROM chats
            """))
            
            logger.info("📊 现有索引:")
            for row in result:
                logger.info(f"  {row[2]}: {row[4]}")
            
            # 5. 测试慢查询性能
            import time
            
            logger.info("🔍 测试查询性能...")
            
            # 测试1: COUNT(DISTINCT visitor_id)
            start = time.time()
            result = db.session.execute(text("""
                SELECT COUNT(DISTINCT visitor_id) FROM chats WHERE business_id = 1
            """))
            result.fetchone()
            duration1 = time.time() - start
            logger.info(f"  COUNT(DISTINCT visitor_id): {duration1:.3f}秒")
            
            # 测试2: 使用子查询优化
            start = time.time()
            result = db.session.execute(text("""
                SELECT COUNT(*) FROM (
                    SELECT DISTINCT visitor_id FROM chats WHERE business_id = 1
                ) as t
            """))
            result.fetchone()
            duration2 = time.time() - start
            logger.info(f"  子查询方式: {duration2:.3f}秒")
            
            if duration1 > 1.0:
                logger.warning(f"⚠️ 查询性能较差，建议添加索引或使用缓存")
            
        except Exception as e:
            logger.error(f"❌ 分析失败: {e}")
            import traceback
            logger.error(traceback.format_exc())


def optimize_statistics_queries():
    """优化统计查询的建议"""
    logger.info("\n" + "=" * 60)
    logger.info("统计查询优化建议")
    logger.info("=" * 60)
    
    suggestions = [
        "1. 添加复合索引 (business_id, visitor_id) - 加速去重统计",
        "2. 使用Redis缓存统计结果 - 减少数据库查询",
        "3. 使用物化视图或汇总表 - 预计算统计数据",
        "4. 限制统计时间范围 - 避免全表扫描",
        "5. 使用近似算法 - HyperLogLog估算去重数量",
    ]
    
    for suggestion in suggestions:
        logger.info(f"  {suggestion}")
    
    logger.info("\n代码优化示例:")
    logger.info("""
    # 方法1: 增加缓存时间
    if redis_client:
        redis_client.setex(cache_key, 60, json.dumps(result))  # 60秒缓存
    
    # 方法2: 使用子查询
    total_visitors = db.session.query(
        func.count()
    ).select_from(
        db.session.query(Chat.visitor_id).filter(
            Chat.business_id == business_id
        ).distinct().subquery()
    ).scalar() or 0
    
    # 方法3: 限制时间范围（只统计最近30天）
    thirty_days_ago = int((datetime.now() - timedelta(days=30)).timestamp())
    total_visitors = db.session.query(
        func.count(distinct(Chat.visitor_id))
    ).filter(
        Chat.business_id == business_id,
        Chat.timestamp >= thirty_days_ago
    ).scalar() or 0
    """)


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("开始优化慢查询")
    logger.info("=" * 60)
    
    # 1. 分析chats表
    logger.info("\n[1/3] 分析chats表...")
    analyze_chats_table()
    
    # 2. 添加索引
    logger.info("\n[2/3] 添加优化索引...")
    add_chats_indexes()
    
    # 3. 优化建议
    logger.info("\n[3/3] 优化建议...")
    optimize_statistics_queries()
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ 优化完成！")
    logger.info("=" * 60)
    logger.info("\n建议:")
    logger.info("1. 重启应用以应用新索引")
    logger.info("2. 修改 StatisticsServiceClass.py 增加缓存时间")
    logger.info("3. 监控慢查询日志")


if __name__ == '__main__':
    main()
