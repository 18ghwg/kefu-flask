"""
定时任务配置列表
"""


class Config(object):
    """定时任务配置"""
    
    JOBS = [
        # 数据库健康检查 - 每3分钟执行一次
        {
            'id': 'db_health_check',
            'func': 'Tasks.db_health_check:check_db_health',
            'trigger': 'interval',
            'minutes': 3,
            'misfire_grace_time': 30
        },
        
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
