"""
分析数据库表大小
识别哪些表占用空间最大，需要清理
"""
from app import app
from exts import db
from sqlalchemy import text
import log

logger = log.get_logger(__name__)


def analyze_table_sizes():
    """分析所有表的大小"""
    with app.app_context():
        try:
            logger.info("=" * 60)
            logger.info("数据库表大小分析")
            logger.info("=" * 60)
            
            # 查询所有表的大小
            result = db.session.execute(text("""
                SELECT 
                    table_name,
                    ROUND(data_length / 1024 / 1024, 2) as data_mb,
                    ROUND(index_length / 1024 / 1024, 2) as index_mb,
                    ROUND((data_length + index_length) / 1024 / 1024, 2) as total_mb,
                    table_rows,
                    ROUND(data_length / table_rows, 2) as avg_row_length
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
                ORDER BY (data_length + index_length) DESC
            """))
            
            tables = []
            total_size = 0
            
            print("\n" + "=" * 80)
            print(f"{'表名':<30} {'数据大小':<12} {'索引大小':<12} {'总大小':<12} {'行数':<15}")
            print("=" * 80)
            
            for row in result:
                table_name, data_mb, index_mb, total_mb, table_rows, avg_row = row
                
                tables.append({
                    'name': table_name,
                    'data_mb': data_mb,
                    'index_mb': index_mb,
                    'total_mb': total_mb,
                    'rows': table_rows or 0,
                    'avg_row': avg_row or 0
                })
                
                total_size += total_mb
                
                print(f"{table_name:<30} {data_mb:>10.2f}MB {index_mb:>10.2f}MB {total_mb:>10.2f}MB {table_rows or 0:>12,}")
            
            print("=" * 80)
            print(f"{'总计':<30} {'':<12} {'':<12} {total_size:>10.2f}MB")
            print("=" * 80)
            
            # 分析最大的表
            logger.info("\n最大的5个表:")
            for i, table in enumerate(tables[:5], 1):
                logger.info(f"{i}. {table['name']}: {table['total_mb']:.2f}MB ({table['rows']:,} 行)")
                logger.info(f"   平均行大小: {table['avg_row']:.2f} 字节")
            
            # 分析需要清理的表
            logger.info("\n建议清理的表:")
            
            cleanup_suggestions = []
            
            for table in tables:
                if table['name'] == 'chats' and table['total_mb'] > 100:
                    cleanup_suggestions.append({
                        'table': 'chats',
                        'reason': '聊天记录表，建议清理60天前的数据',
                        'size': table['total_mb'],
                        'rows': table['rows']
                    })
                elif table['name'] == 'queues' and table['total_mb'] > 50:
                    cleanup_suggestions.append({
                        'table': 'queues',
                        'reason': '队列表，建议清理60天前已完成的记录',
                        'size': table['total_mb'],
                        'rows': table['rows']
                    })
                elif table['name'] == 'operation_logs' and table['total_mb'] > 50:
                    cleanup_suggestions.append({
                        'table': 'operation_logs',
                        'reason': '操作日志表，建议清理60天前的日志',
                        'size': table['total_mb'],
                        'rows': table['rows']
                    })
                elif table['name'] == 'comments' and table['total_mb'] > 20:
                    cleanup_suggestions.append({
                        'table': 'comments',
                        'reason': '评价表，建议清理60天前的评价',
                        'size': table['total_mb'],
                        'rows': table['rows']
                    })
            
            if cleanup_suggestions:
                for i, suggestion in enumerate(cleanup_suggestions, 1):
                    logger.info(f"{i}. {suggestion['table']}: {suggestion['size']:.2f}MB ({suggestion['rows']:,} 行)")
                    logger.info(f"   {suggestion['reason']}")
            else:
                logger.info("所有表大小都在合理范围内")
            
            # 分析数据增长趋势
            logger.info("\n数据增长趋势分析:")
            
            # 分析chats表的增长
            try:
                result = db.session.execute(text("""
                    SELECT 
                        DATE(FROM_UNIXTIME(timestamp)) as date,
                        COUNT(*) as count
                    FROM chats
                    WHERE timestamp >= UNIX_TIMESTAMP(DATE_SUB(NOW(), INTERVAL 7 DAY))
                    GROUP BY DATE(FROM_UNIXTIME(timestamp))
                    ORDER BY date DESC
                """))
                
                logger.info("最近7天chats表增长:")
                for row in result:
                    date, count = row
                    logger.info(f"  {date}: {count:,} 条记录")
            except Exception as e:
                logger.debug(f"无法分析增长趋势: {e}")
            
            # 预估清理效果
            logger.info("\n预估清理效果（清理60天前数据）:")
            
            for table in tables[:5]:
                if table['name'] in ['chats', 'queues', 'operation_logs', 'comments']:
                    # 假设数据均匀分布，60天前的数据占总数据的比例
                    # 如果表有90天数据，60天前的占1/3
                    estimated_cleanup = table['total_mb'] * 0.33
                    logger.info(f"{table['name']}: 预计释放 {estimated_cleanup:.2f}MB")
            
        except Exception as e:
            logger.error(f"分析失败: {e}")
            import traceback
            logger.error(traceback.format_exc())


def analyze_old_data():
    """分析过期数据量"""
    with app.app_context():
        try:
            from datetime import datetime, timedelta
            
            logger.info("\n" + "=" * 60)
            logger.info("过期数据分析（60天前）")
            logger.info("=" * 60)
            
            sixty_days_ago = int((datetime.now() - timedelta(days=60)).timestamp())
            sixty_days_ago_dt = datetime.now() - timedelta(days=60)
            
            # 分析chats表
            result = db.session.execute(text("""
                SELECT COUNT(*) as cnt FROM chats WHERE timestamp < :timestamp
            """), {"timestamp": sixty_days_ago})
            
            chats_old = result.fetchone()[0]
            
            result = db.session.execute(text("SELECT COUNT(*) as cnt FROM chats"))
            chats_total = result.fetchone()[0]
            
            logger.info(f"chats表:")
            logger.info(f"  总记录数: {chats_total:,}")
            logger.info(f"  过期记录: {chats_old:,} ({chats_old/chats_total*100:.1f}%)")
            
            # 分析queues表
            try:
                result = db.session.execute(text("""
                    SELECT COUNT(*) as cnt 
                    FROM queues 
                    WHERE updated_at < :date 
                    AND state IN ('complete', 'closed', 'blacklist')
                """), {"date": sixty_days_ago_dt})
                
                queues_old = result.fetchone()[0]
                
                result = db.session.execute(text("SELECT COUNT(*) as cnt FROM queues"))
                queues_total = result.fetchone()[0]
                
                logger.info(f"queues表:")
                logger.info(f"  总记录数: {queues_total:,}")
                logger.info(f"  过期记录: {queues_old:,} ({queues_old/queues_total*100:.1f}%)")
            except Exception as e:
                logger.debug(f"queues表分析失败: {e}")
            
            # 分析comments表
            try:
                result = db.session.execute(text("""
                    SELECT COUNT(*) as cnt FROM comments WHERE add_time < :date
                """), {"date": sixty_days_ago_dt})
                
                comments_old = result.fetchone()[0]
                
                result = db.session.execute(text("SELECT COUNT(*) as cnt FROM comments"))
                comments_total = result.fetchone()[0]
                
                logger.info(f"comments表:")
                logger.info(f"  总记录数: {comments_total:,}")
                logger.info(f"  过期记录: {comments_old:,} ({comments_old/comments_total*100:.1f}%)")
            except Exception as e:
                logger.debug(f"comments表分析失败: {e}")
            
        except Exception as e:
            logger.error(f"过期数据分析失败: {e}")


def main():
    """主函数"""
    logger.info("开始分析数据库...")
    
    # 1. 分析表大小
    analyze_table_sizes()
    
    # 2. 分析过期数据
    analyze_old_data()
    
    logger.info("\n" + "=" * 60)
    logger.info("分析完成！")
    logger.info("=" * 60)
    logger.info("\n建议:")
    logger.info("1. 定时任务会每天自动清理60天前的数据")
    logger.info("2. 如需立即清理，运行: python -c \"from Tasks.maintenance_tasks import cleanup_old_data; cleanup_old_data()\"")
    logger.info("3. 定期运行此脚本监控数据库大小")


if __name__ == '__main__':
    main()
