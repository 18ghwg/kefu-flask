"""
系统维护任务
包含数据库优化、索引维护、性能监控等自动化维护功能
"""
from exts import app, db
from sqlalchemy import text, inspect
from datetime import datetime, timedelta
import log

logger = log.get_logger(__name__)


def optimize_database_indexes():
    """
    优化数据库索引
    每周执行一次，检查并添加缺失的索引
    """
    try:
        with app.app_context():
            logger.info("🔧 开始数据库索引优化...")
            
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            # 需要优化的索引列表
            indexes_to_check = {
                'chats': [
                    ('idx_chats_business_visitor', 'business_id, visitor_id'),
                    ('idx_chats_business_timestamp', 'business_id, timestamp'),
                    ('idx_chats_visitor_timestamp', 'visitor_id, timestamp'),
                    ('idx_chats_timestamp', 'timestamp'),
                ],
                'queues': [
                    ('idx_queues_visitor_state', 'visitor_id, state'),
                    ('idx_queues_service_state', 'service_id, state'),
                    ('idx_queues_business_state', 'business_id, state'),
                ],
                'visitors': [
                    ('idx_visitors_business', 'visitor_id, business_id'),
                ],
            }
            
            added_count = 0
            
            for table_name, indexes in indexes_to_check.items():
                if table_name not in existing_tables:
                    continue
                
                existing_indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]
                
                for index_name, columns in indexes:
                    if index_name not in existing_indexes:
                        try:
                            sql = f"CREATE INDEX {index_name} ON {table_name} ({columns})"
                            db.session.execute(text(sql))
                            db.session.commit()
                            logger.info(f"✅ 创建索引: {index_name} ON {table_name}({columns})")
                            added_count += 1
                        except Exception as e:
                            logger.warning(f"索引创建失败 {index_name}: {e}")
                            db.session.rollback()
            
            if added_count > 0:
                logger.info(f"✅ 索引优化完成，新增 {added_count} 个索引")
            else:
                logger.debug("✅ 所有索引已存在，无需优化")
                
    except Exception as e:
        logger.error(f"❌ 数据库索引优化失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        try:
            db.session.remove()
        except:
            pass


def analyze_tables():
    """
    分析表统计信息
    每天执行一次，优化查询计划
    """
    try:
        with app.app_context():
            logger.info("📊 开始分析表统计信息...")
            
            # 需要分析的表
            tables = ['chats', 'queues', 'visitors', 'services', 'comments']
            
            for table in tables:
                try:
                    db.session.execute(text(f"ANALYZE TABLE {table}"))
                    logger.debug(f"✅ 分析表: {table}")
                except Exception as e:
                    logger.warning(f"分析表失败 {table}: {e}")
            
            db.session.commit()
            logger.info("✅ 表统计信息分析完成")
            
    except Exception as e:
        logger.error(f"❌ 表分析失败: {e}")
    finally:
        try:
            db.session.remove()
        except:
            pass


def cleanup_old_data():
    """
    清理过期数据
    每天执行一次，清理超过60天的数据
    """
    try:
        with app.app_context():
            logger.info("🗑️ 开始清理过期数据...")
            
            sixty_days_ago = int((datetime.now() - timedelta(days=60)).timestamp())
            sixty_days_ago_dt = datetime.now() - timedelta(days=60)
            
            total_deleted = 0
            
            # 1. 清理chats表（聊天记录）- 最耗时的表
            logger.info("清理chats表（60天前的聊天记录）...")
            
            # 先统计要删除的记录数
            result = db.session.execute(text("""
                SELECT COUNT(*) as cnt FROM chats WHERE timestamp < :timestamp
            """), {"timestamp": sixty_days_ago})
            
            chats_count = result.fetchone()[0]
            
            if chats_count > 0:
                logger.info(f"发现 {chats_count:,} 条过期聊天记录")
                
                # 分批删除，避免锁表（每批1000条）
                batch_size = 1000
                deleted = 0
                
                while deleted < chats_count:
                    db.session.execute(text("""
                        DELETE FROM chats 
                        WHERE timestamp < :timestamp 
                        LIMIT :limit
                    """), {"timestamp": sixty_days_ago, "limit": batch_size})
                    
                    db.session.commit()
                    deleted += batch_size
                    
                    if deleted % 10000 == 0:
                        logger.info(f"已清理 {deleted:,}/{chats_count:,} 条聊天记录...")
                
                logger.info(f"✅ chats表清理完成，删除了 {chats_count:,} 条记录")
                total_deleted += chats_count
            else:
                logger.debug("✅ chats表无需清理")
            
            # 2. 清理queues表（已完成的队列记录）
            logger.info("清理queues表（60天前已完成的队列）...")
            
            result = db.session.execute(text("""
                SELECT COUNT(*) as cnt 
                FROM queues 
                WHERE updated_at < :date 
                AND state IN ('complete', 'closed', 'blacklist')
            """), {"date": sixty_days_ago_dt})
            
            queues_count = result.fetchone()[0]
            
            if queues_count > 0:
                logger.info(f"发现 {queues_count:,} 条过期队列记录")
                
                # 分批删除
                deleted = 0
                while deleted < queues_count:
                    db.session.execute(text("""
                        DELETE FROM queues 
                        WHERE updated_at < :date 
                        AND state IN ('complete', 'closed', 'blacklist')
                        LIMIT :limit
                    """), {"date": sixty_days_ago_dt, "limit": batch_size})
                    
                    db.session.commit()
                    deleted += batch_size
                    
                    if deleted % 5000 == 0:
                        logger.info(f"已清理 {deleted:,}/{queues_count:,} 条队列记录...")
                
                logger.info(f"✅ queues表清理完成，删除了 {queues_count:,} 条记录")
                total_deleted += queues_count
            else:
                logger.debug("✅ queues表无需清理")
            
            # 3. 清理comments表（评价记录）
            logger.info("清理comments表（60天前的评价）...")
            
            result = db.session.execute(text("""
                SELECT COUNT(*) as cnt 
                FROM comments 
                WHERE add_time < :date
            """), {"date": sixty_days_ago_dt})
            
            comments_count = result.fetchone()[0]
            
            if comments_count > 0:
                logger.info(f"发现 {comments_count:,} 条过期评价记录")
                
                db.session.execute(text("""
                    DELETE FROM comments 
                    WHERE add_time < :date
                """), {"date": sixty_days_ago_dt})
                
                db.session.commit()
                logger.info(f"✅ comments表清理完成，删除了 {comments_count:,} 条记录")
                total_deleted += comments_count
            else:
                logger.debug("✅ comments表无需清理")
            
            # 4. 清理operation_logs表（操作日志）
            logger.info("清理operation_logs表（60天前的操作日志）...")
            
            try:
                result = db.session.execute(text("""
                    SELECT COUNT(*) as cnt 
                    FROM operation_logs 
                    WHERE created_at < :date
                """), {"date": sixty_days_ago_dt})
                
                logs_count = result.fetchone()[0]
                
                if logs_count > 0:
                    logger.info(f"发现 {logs_count:,} 条过期操作日志")
                    
                    # 分批删除
                    deleted = 0
                    while deleted < logs_count:
                        db.session.execute(text("""
                            DELETE FROM operation_logs 
                            WHERE created_at < :date
                            LIMIT :limit
                        """), {"date": sixty_days_ago_dt, "limit": batch_size})
                        
                        db.session.commit()
                        deleted += batch_size
                        
                        if deleted % 5000 == 0:
                            logger.info(f"已清理 {deleted:,}/{logs_count:,} 条操作日志...")
                    
                    logger.info(f"✅ operation_logs表清理完成，删除了 {logs_count:,} 条记录")
                    total_deleted += logs_count
                else:
                    logger.debug("✅ operation_logs表无需清理")
            except Exception as e:
                logger.debug(f"operation_logs表可能不存在: {e}")
            
            # 5. 清理汇总表中的旧数据
            logger.info("清理visitor_stats_cache表（90天前的汇总数据）...")
            
            try:
                ninety_days_ago_date = (datetime.now() - timedelta(days=90)).date()
                
                result = db.session.execute(text("""
                    SELECT COUNT(*) as cnt 
                    FROM visitor_stats_cache 
                    WHERE stat_date < :date
                """), {"date": ninety_days_ago_date})
                
                cache_count = result.fetchone()[0]
                
                if cache_count > 0:
                    db.session.execute(text("""
                        DELETE FROM visitor_stats_cache 
                        WHERE stat_date < :date
                    """), {"date": ninety_days_ago_date})
                    
                    db.session.commit()
                    logger.info(f"✅ visitor_stats_cache表清理完成，删除了 {cache_count:,} 条记录")
                    total_deleted += cache_count
                else:
                    logger.debug("✅ visitor_stats_cache表无需清理")
            except Exception as e:
                logger.debug(f"visitor_stats_cache表可能不存在: {e}")
            
            # 总结
            if total_deleted > 0:
                logger.info(f"✅ 数据清理完成，共删除 {total_deleted:,} 条过期记录")
                logger.info(f"释放的存储空间预计: {total_deleted * 0.5 / 1024:.2f} MB")
            else:
                logger.info("✅ 所有表都无需清理，数据保持最新")
                
        except Exception as e:
            logger.error(f"❌ 数据清理失败: {e}")
            db.session.rollback()
            import traceback
            logger.error(traceback.format_exc())
        finally:
            try:
                db.session.remove()
            except:
                pass


def check_table_fragmentation():
    """
    检查表碎片
    每周执行一次，检测需要优化的表
    """
    try:
        with app.app_context():
            logger.info("🔍 检查表碎片...")
            
            result = db.session.execute(text("""
                SELECT 
                    table_name,
                    ROUND(data_length / 1024 / 1024, 2) as data_mb,
                    ROUND(data_free / 1024 / 1024, 2) as free_mb,
                    ROUND(data_free / data_length * 100, 2) as fragmentation
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
                AND data_free > 0
                ORDER BY fragmentation DESC
            """))
            
            fragmented_tables = []
            
            for row in result:
                table_name, data_mb, free_mb, fragmentation = row
                
                # 碎片率超过20%需要优化
                if fragmentation > 20:
                    fragmented_tables.append({
                        'table': table_name,
                        'data_mb': data_mb,
                        'free_mb': free_mb,
                        'fragmentation': fragmentation
                    })
                    logger.warning(
                        f"⚠️ 表 {table_name} 碎片率: {fragmentation}% "
                        f"(数据: {data_mb}MB, 碎片: {free_mb}MB)"
                    )
            
            if fragmented_tables:
                logger.info(f"发现 {len(fragmented_tables)} 个表需要优化")
                logger.info("建议手动执行: OPTIMIZE TABLE table_name;")
            else:
                logger.debug("✅ 所有表碎片率正常")
                
    except Exception as e:
        logger.error(f"❌ 表碎片检查失败: {e}")
    finally:
        try:
            db.session.remove()
        except:
            pass


def generate_performance_report():
    """
    生成性能报告
    每天执行一次，汇总系统性能指标
    """
    try:
        with app.app_context():
            logger.info("📈 生成性能报告...")
            
            report = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'metrics': {}
            }
            
            # 1. 数据库连接数
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
                report['metrics']['connections'] = {
                    'total': row[0],
                    'sleeping': row[1] or 0,
                    'active': row[2] or 0
                }
            except:
                pass
            
            # 2. 表大小统计
            try:
                result = db.session.execute(text("""
                    SELECT 
                        table_name,
                        ROUND(data_length / 1024 / 1024, 2) as size_mb,
                        table_rows
                    FROM information_schema.tables
                    WHERE table_schema = DATABASE()
                    ORDER BY data_length DESC
                    LIMIT 5
                """))
                
                report['metrics']['top_tables'] = [
                    {'table': row[0], 'size_mb': row[1], 'rows': row[2]}
                    for row in result
                ]
            except:
                pass
            
            # 3. 连接池状态
            try:
                pool = db.engine.pool
                report['metrics']['pool'] = {
                    'size': pool.size(),
                    'checkedout': pool.checkedout(),
                    'overflow': pool.overflow(),
                    'usage_rate': round(
                        pool.checkedout() / (pool.size() + pool.overflow()) * 100, 2
                    ) if (pool.size() + pool.overflow()) > 0 else 0
                }
            except:
                pass
            
            # 输出报告
            logger.info("=" * 60)
            logger.info(f"性能报告 - {report['date']}")
            logger.info("=" * 60)
            
            if 'connections' in report['metrics']:
                conn = report['metrics']['connections']
                logger.info(f"数据库连接: 总数={conn['total']}, 活跃={conn['active']}, 休眠={conn['sleeping']}")
            
            if 'pool' in report['metrics']:
                pool = report['metrics']['pool']
                logger.info(f"连接池: 使用率={pool['usage_rate']}%, 已签出={pool['checkedout']}/{pool['size']}")
            
            if 'top_tables' in report['metrics']:
                logger.info("最大的表:")
                for table in report['metrics']['top_tables']:
                    logger.info(f"  {table['table']}: {table['size_mb']}MB ({table['rows']:,} 行)")
            
            logger.info("=" * 60)
            
    except Exception as e:
        logger.error(f"❌ 性能报告生成失败: {e}")
    finally:
        try:
            db.session.remove()
        except:
            pass


def vacuum_redis_cache():
    """
    清理Redis缓存
    每天执行一次，清理过期的缓存键
    """
    try:
        from exts import redis_client
        
        if not redis_client:
            logger.debug("Redis未配置，跳过缓存清理")
            return
        
        logger.info("🧹 清理Redis缓存...")
        
        # 获取所有键的数量
        total_keys = redis_client.dbsize()
        
        # 清理过期键（Redis会自动处理，这里只是触发）
        # 扫描并删除特定模式的过期缓存
        patterns = ['dashboard:*', 'stats:*', 'temp:*']
        deleted = 0
        
        for pattern in patterns:
            cursor = 0
            while True:
                cursor, keys = redis_client.scan(cursor, match=pattern, count=100)
                
                for key in keys:
                    # 检查TTL，如果已过期或即将过期（<60秒），删除
                    ttl = redis_client.ttl(key)
                    if ttl < 60 and ttl != -1:  # -1表示永不过期
                        redis_client.delete(key)
                        deleted += 1
                
                if cursor == 0:
                    break
        
        logger.info(f"✅ Redis缓存清理完成，删除 {deleted} 个过期键，剩余 {total_keys - deleted} 个键")
        
    except Exception as e:
        logger.error(f"❌ Redis缓存清理失败: {e}")


def update_visitor_stats_cache():
    """
    更新访客统计汇总表
    每小时执行一次，保持汇总数据最新
    """
    try:
        with app.app_context():
            logger.info("📊 更新访客统计汇总表...")
            
            # 检查汇总表是否存在
            from sqlalchemy import text
            
            try:
                db.session.execute(text("SELECT 1 FROM visitor_stats_cache LIMIT 1"))
            except:
                logger.info("汇总表不存在，跳过更新")
                return
            
            # 更新今天和昨天的数据
            for days_ago in [0, 1]:
                date = datetime.now() - timedelta(days=days_ago)
                day_start = int(datetime.combine(date, datetime.min.time()).timestamp())
                day_end = day_start + 86400 - 1
                
                # 统计访客数
                result = db.session.execute(text("""
                    SELECT COUNT(DISTINCT visitor_id) 
                    FROM chats 
                    WHERE business_id = 1 
                    AND timestamp >= :start 
                    AND timestamp <= :end
                """), {"start": day_start, "end": day_end})
                
                count = result.fetchone()[0]
                
                # 更新汇总表
                db.session.execute(text("""
                    INSERT INTO visitor_stats_cache (business_id, stat_date, visitor_count)
                    VALUES (1, :date, :count)
                    ON DUPLICATE KEY UPDATE visitor_count = :count
                """), {"date": date.date(), "count": count})
            
            db.session.commit()
            logger.info("✅ 访客统计汇总表更新完成")
            
    except Exception as e:
        logger.error(f"❌ 更新汇总表失败: {e}")
        db.session.rollback()
    finally:
        try:
            db.session.remove()
        except:
            pass
