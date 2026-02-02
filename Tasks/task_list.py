"""
定时任务配置列表
"""


class Config(object):
    """定时任务配置"""
    
    JOBS = [
        # ==================== 健康检查任务 ====================
        
        # 数据库健康检查 - 每3分钟执行一次
        {
            'id': 'db_health_check',
            'func': 'Tasks.db_health_check:check_db_health',
            'trigger': 'interval',
            'minutes': 3,
            'misfire_grace_time': 30
        },
        
        # 连接池监控 - 每5分钟执行一次
        {
            'id': 'monitor_connection_pool',
            'func': 'Tasks.db_health_check:monitor_connection_pool',
            'trigger': 'interval',
            'minutes': 5,
            'misfire_grace_time': 30
        },
        
        # 连接池清理 - 每10分钟执行一次
        {
            'id': 'cleanup_connection_pool',
            'func': 'Tasks.db_health_check:cleanup_connection_pool',
            'trigger': 'interval',
            'minutes': 10,
            'misfire_grace_time': 60
        },
        
        # 慢查询检查 - 每15分钟执行一次
        {
            'id': 'check_slow_queries',
            'func': 'Tasks.db_health_check:check_slow_queries',
            'trigger': 'interval',
            'minutes': 15,
            'misfire_grace_time': 60
        },
        
        # ==================== 维护任务 ====================
        
        # 表统计信息分析 - 每天凌晨2点执行
        {
            'id': 'analyze_tables',
            'func': 'Tasks.maintenance_tasks:analyze_tables',
            'trigger': 'cron',
            'hour': 2,
            'minute': 0,
            'misfire_grace_time': 300
        },
        
        # 数据库索引优化 - 每周日凌晨3点执行
        {
            'id': 'optimize_database_indexes',
            'func': 'Tasks.maintenance_tasks:optimize_database_indexes',
            'trigger': 'cron',
            'day_of_week': 'sun',
            'hour': 3,
            'minute': 0,
            'misfire_grace_time': 600
        },
        
        # 清理过期数据 - 每天凌晨4点执行
        {
            'id': 'cleanup_old_data',
            'func': 'Tasks.maintenance_tasks:cleanup_old_data',
            'trigger': 'cron',
            'hour': 4,
            'minute': 0,
            'misfire_grace_time': 600
        },
        
        # 检查表碎片 - 每周一凌晨5点执行
        {
            'id': 'check_table_fragmentation',
            'func': 'Tasks.maintenance_tasks:check_table_fragmentation',
            'trigger': 'cron',
            'day_of_week': 'mon',
            'hour': 5,
            'minute': 0,
            'misfire_grace_time': 300
        },
        
        # 生成性能报告 - 每天早上8点执行
        {
            'id': 'generate_performance_report',
            'func': 'Tasks.maintenance_tasks:generate_performance_report',
            'trigger': 'cron',
            'hour': 8,
            'minute': 0,
            'misfire_grace_time': 300
        },
        
        # 清理Redis缓存 - 每天凌晨1点执行
        {
            'id': 'vacuum_redis_cache',
            'func': 'Tasks.maintenance_tasks:vacuum_redis_cache',
            'trigger': 'cron',
            'hour': 1,
            'minute': 0,
            'misfire_grace_time': 300
        },
        
        # 更新访客统计汇总表 - 每小时执行
        {
            'id': 'update_visitor_stats_cache',
            'func': 'Tasks.maintenance_tasks:update_visitor_stats_cache',
            'trigger': 'interval',
            'hours': 1,
            'misfire_grace_time': 300
        },
        
        # ==================== 示例任务 ====================
        
        # 示例：每天8点执行的任务
        # {
        #     'id': 'daily_task',
        #     'func': 'Tasks.some_module:some_function',
        #     'trigger': 'cron',
        #     'day': '*',
        #     'hour': 8,
        #     'minute': 0,
        #     'misfire_grace_time': 60
        # },
    ]
    
    # 启用任务调度API
    SCHEDULER_API_ENABLED = True
    
    # 时区
    SCHEDULER_TIMEZONE = 'Asia/Shanghai'
    
    # 最大并发实例数
    SCHEDULER_MAX_INSTANCES = 15
