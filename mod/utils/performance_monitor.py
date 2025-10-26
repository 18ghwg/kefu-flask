"""
性能监控工具
监控慢查询、慢接口和系统性能指标
"""
import time
import functools
from datetime import datetime
from flask import request, g
from exts import db
import log

logger = log.get_logger(__name__)


class PerformanceMonitor:
    """
    性能监控类
    
    设计原则：
    - Single Responsibility: 只负责性能监控和日志记录
    - KISS: 简单的装饰器和钩子实现
    """
    
    # 慢查询阈值（秒）
    SLOW_QUERY_THRESHOLD = 1.0
    
    # 慢接口阈值（秒）
    SLOW_API_THRESHOLD = 2.0
    
    @staticmethod
    def monitor_query(func):
        """
        数据库查询性能监控装饰器
        
        使用示例：
            @PerformanceMonitor.monitor_query
            def get_user_list():
                return User.query.all()
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                
                # 记录慢查询
                if duration > PerformanceMonitor.SLOW_QUERY_THRESHOLD:
                    logger.warning(
                        f"🐌 慢查询警告：{func.__name__} "
                        f"耗时 {duration:.3f}s "
                        f"(阈值: {PerformanceMonitor.SLOW_QUERY_THRESHOLD}s)"
                    )
                    
                    # 记录慢查询日志到专用文件
                    slow_logger = log.get_logger('slow_query')
                    slow_logger.warning(
                        f"Function: {func.__name__} | "
                        f"Duration: {duration:.3f}s | "
                        f"Args: {args} | "
                        f"Kwargs: {kwargs}"
                    )
        
        return wrapper
    
    @staticmethod
    def monitor_api(threshold: float = None):
        """
        API接口性能监控装饰器
        
        使用示例：
            @app.route('/api/users')
            @PerformanceMonitor.monitor_api(threshold=1.0)
            def get_users():
                return jsonify(users)
        
        Args:
            threshold: 慢接口阈值（秒），不指定则使用默认值
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    threshold_value = threshold or PerformanceMonitor.SLOW_API_THRESHOLD
                    
                    # 记录慢接口
                    if duration > threshold_value:
                        logger.warning(
                            f"🐌 慢接口警告：{request.method} {request.path} "
                            f"耗时 {duration:.3f}s "
                            f"(阈值: {threshold_value}s)"
                        )
                        
                        # 记录详细信息
                        slow_logger = log.get_logger('slow_api')
                        slow_logger.warning(
                            f"Method: {request.method} | "
                            f"Path: {request.path} | "
                            f"Duration: {duration:.3f}s | "
                            f"IP: {request.remote_addr} | "
                            f"User-Agent: {request.headers.get('User-Agent', 'Unknown')}"
                        )
            
            return wrapper
        return decorator


# ========== Flask 请求钩子 ==========

def init_performance_monitoring(app):
    """
    初始化性能监控
    
    在Flask应用中注册请求钩子，自动监控所有请求的性能
    
    Args:
        app: Flask应用实例
    """
    
    @app.before_request
    def before_request_performance():
        """请求开始时记录时间"""
        g.start_time = time.time()
        g.db_query_count = 0
        g.db_query_time = 0.0
    
    @app.after_request
    def after_request_performance(response):
        """请求结束时计算耗时"""
        if hasattr(g, 'start_time'):
            duration = time.time() - g.start_time
            
            # 跳过静态资源
            if not request.path.startswith('/static/'):
                # 记录所有请求的耗时（INFO级别）
                logger.info(
                    f"📊 {request.method} {request.path} "
                    f"耗时 {duration:.3f}s | "
                    f"状态码 {response.status_code}"
                )
                
                # 记录慢接口（WARNING级别）
                if duration > PerformanceMonitor.SLOW_API_THRESHOLD:
                    logger.warning(
                        f"🐌 慢接口：{request.method} {request.path} "
                        f"耗时 {duration:.3f}s"
                    )
        
        return response


# ========== 数据库查询监控 ==========

class DatabaseQueryMonitor:
    """
    数据库查询性能监控
    
    使用SQLAlchemy事件监听器监控所有数据库查询
    """
    
    @staticmethod
    def init_app(app):
        """
        初始化数据库查询监控
        
        Args:
            app: Flask应用实例
        """
        from sqlalchemy import event
        from sqlalchemy.engine import Engine
        
        @event.listens_for(Engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """查询执行前"""
            conn.info.setdefault('query_start_time', []).append(time.time())
        
        @event.listens_for(Engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """查询执行后"""
            total_time = time.time() - conn.info['query_start_time'].pop(-1)
            
            # 累计查询次数和时间（存储在g对象中）
            if hasattr(g, 'db_query_count'):
                g.db_query_count += 1
                g.db_query_time += total_time
            
            # 记录慢查询
            if total_time > PerformanceMonitor.SLOW_QUERY_THRESHOLD:
                logger.warning(
                    f"🐌 慢查询：{total_time:.3f}s\n"
                    f"SQL: {statement[:200]}..."  # 只记录前200个字符
                )
                
                # 详细日志
                slow_logger = log.get_logger('slow_query')
                slow_logger.warning(
                    f"Duration: {total_time:.3f}s | "
                    f"SQL: {statement} | "
                    f"Parameters: {parameters}"
                )


# ========== 内存和CPU监控 ==========

class SystemResourceMonitor:
    """
    系统资源监控
    
    监控内存和CPU使用情况（可选，需要psutil库）
    """
    
    @staticmethod
    def get_memory_usage():
        """
        获取当前进程的内存使用情况
        
        Returns:
            内存使用量（MB）
        """
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            return memory_info.rss / 1024 / 1024  # 转换为MB
        except ImportError:
            logger.debug("psutil未安装，无法监控内存使用")
            return None
    
    @staticmethod
    def get_cpu_usage():
        """
        获取当前进程的CPU使用率
        
        Returns:
            CPU使用率（百分比）
        """
        try:
            import psutil
            process = psutil.Process()
            return process.cpu_percent(interval=0.1)
        except ImportError:
            logger.debug("psutil未安装，无法监控CPU使用")
            return None
    
    @staticmethod
    def log_system_stats():
        """
        记录系统统计信息
        """
        memory_mb = SystemResourceMonitor.get_memory_usage()
        cpu_percent = SystemResourceMonitor.get_cpu_usage()
        
        if memory_mb is not None:
            logger.info(f"📊 内存使用：{memory_mb:.2f} MB")
        
        if cpu_percent is not None:
            logger.info(f"📊 CPU使用率：{cpu_percent:.1f}%")


# ========== 使用示例 ==========
"""
# 在 app.py 中初始化性能监控：

from mod.utils.performance_monitor import (
    init_performance_monitoring,
    DatabaseQueryMonitor
)

# 初始化性能监控
init_performance_monitoring(app)

# 初始化数据库查询监控
DatabaseQueryMonitor.init_app(app)


# 在视图函数中使用：

from mod.utils.performance_monitor import PerformanceMonitor

@app.route('/api/users')
@PerformanceMonitor.monitor_api(threshold=1.0)
def get_users():
    return jsonify(users)


# 在服务函数中使用：

class UserService:
    @staticmethod
    @PerformanceMonitor.monitor_query
    def get_user_list():
        return User.query.all()
"""


