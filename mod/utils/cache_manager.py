"""
缓存管理器
遵循 SOLID 原则的 Redis 缓存封装
"""
import json
import pickle
from typing import Any, Optional, Callable
from functools import wraps
from flask import current_app
from exts import redis_client
import log

logger = log.get_logger(__name__)


class CacheManager:
    """
    缓存管理器
    
    设计原则：
    - Single Responsibility: 只负责缓存的存取和管理
    - Open/Closed: 通过装饰器扩展功能，不修改原有代码
    - KISS: 简单直接的 API 设计
    """
    
    def __init__(self, prefix: str = 'kefu'):
        """
        初始化缓存管理器
        
        Args:
            prefix: 缓存键前缀，用于区分不同应用
        """
        self.prefix = prefix
        self.redis = redis_client
    
    def _make_key(self, key: str) -> str:
        """
        生成完整的缓存键
        
        Args:
            key: 原始键名
            
        Returns:
            带前缀的完整键名
        """
        return f"{self.prefix}:{key}"
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            default: 默认值（缓存不存在时返回）
            
        Returns:
            缓存值或默认值
        """
        if not self.redis:
            return default
        
        try:
            full_key = self._make_key(key)
            value = self.redis.get(full_key)
            
            if value is None:
                return default
            
            # 尝试JSON反序列化，失败则返回原始值
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
                
        except Exception as e:
            logger.warning(f"缓存获取失败 [{key}]: {e}")
            return default
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），默认1小时
            
        Returns:
            是否设置成功
        """
        if not self.redis:
            return False
        
        try:
            full_key = self._make_key(key)
            
            # 尝试JSON序列化
            try:
                serialized_value = json.dumps(value, ensure_ascii=False)
            except (TypeError, ValueError):
                # 无法JSON序列化的对象使用原始值
                serialized_value = str(value)
            
            self.redis.setex(full_key, ttl, serialized_value)
            return True
            
        except Exception as e:
            logger.error(f"缓存设置失败 [{key}]: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        删除缓存
        
        Args:
            key: 缓存键
            
        Returns:
            是否删除成功
        """
        if not self.redis:
            return False
        
        try:
            full_key = self._make_key(key)
            self.redis.delete(full_key)
            return True
            
        except Exception as e:
            logger.warning(f"缓存删除失败 [{key}]: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """
        批量删除匹配模式的缓存
        
        Args:
            pattern: 匹配模式（支持通配符 *）
            
        Returns:
            删除的键数量
        """
        if not self.redis:
            return 0
        
        try:
            full_pattern = self._make_key(pattern)
            keys = self.redis.keys(full_pattern)
            
            if keys:
                return self.redis.delete(*keys)
            return 0
            
        except Exception as e:
            logger.error(f"批量删除缓存失败 [{pattern}]: {e}")
            return 0
    
    def exists(self, key: str) -> bool:
        """
        检查缓存是否存在
        
        Args:
            key: 缓存键
            
        Returns:
            是否存在
        """
        if not self.redis:
            return False
        
        try:
            full_key = self._make_key(key)
            return self.redis.exists(full_key) > 0
        except Exception as e:
            logger.warning(f"缓存检查失败 [{key}]: {e}")
            return False
    
    def incr(self, key: str, amount: int = 1, ttl: int = 3600) -> Optional[int]:
        """
        递增计数器
        
        Args:
            key: 缓存键
            amount: 递增量
            ttl: 过期时间（秒）
            
        Returns:
            递增后的值，失败返回 None
        """
        if not self.redis:
            return None
        
        try:
            full_key = self._make_key(key)
            value = self.redis.incr(full_key, amount)
            
            # 首次创建时设置过期时间
            if value == amount:
                self.redis.expire(full_key, ttl)
            
            return value
            
        except Exception as e:
            logger.error(f"计数器递增失败 [{key}]: {e}")
            return None
    
    def cache_result(self, ttl: int = 3600, key_prefix: str = ''):
        """
        装饰器：缓存函数返回值
        
        使用示例：
            @cache_manager.cache_result(ttl=600, key_prefix='user')
            def get_user_info(user_id):
                return db.query(user_id)
        
        Args:
            ttl: 缓存过期时间（秒）
            key_prefix: 缓存键前缀
            
        Returns:
            装饰器函数
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # 生成缓存键（基于函数名和参数）
                cache_key_parts = [key_prefix or func.__name__]
                
                # 添加位置参数
                if args:
                    cache_key_parts.extend(str(arg) for arg in args)
                
                # 添加关键字参数（排序保证一致性）
                if kwargs:
                    sorted_kwargs = sorted(kwargs.items())
                    cache_key_parts.extend(f"{k}={v}" for k, v in sorted_kwargs)
                
                cache_key = ':'.join(cache_key_parts)
                
                # 尝试从缓存获取
                cached_value = self.get(cache_key)
                if cached_value is not None:
                    logger.debug(f"缓存命中: {cache_key}")
                    return cached_value
                
                # 执行函数
                result = func(*args, **kwargs)
                
                # 存入缓存
                if result is not None:
                    self.set(cache_key, result, ttl)
                    logger.debug(f"缓存已更新: {cache_key}")
                
                return result
            
            return wrapper
        return decorator


# ========== 全局缓存管理器实例 ==========
cache_manager = CacheManager(prefix='kefu')


# ========== 预定义缓存键模式 ==========
class CacheKeys:
    """
    缓存键常量类（遵循 YAGNI 原则，仅定义当前需要的）
    """
    # 在线用户
    ONLINE_SERVICES = 'online:services'  # 在线客服列表
    ONLINE_VISITORS = 'online:visitors'  # 在线访客列表
    ONLINE_COUNT = 'online:count:{}'  # 在线人数统计（按商户）
    
    # 系统设置
    SYSTEM_SETTINGS = 'settings:system:{}'  # 系统设置（按商户）
    
    # 常见问题
    FAQ_LIST = 'faq:list:{}'  # 常见问题列表（按商户）
    FAQ_DETAIL = 'faq:detail:{}'  # 常见问题详情（按ID）
    
    # 访客信息
    VISITOR_INFO = 'visitor:info:{}'  # 访客信息（按visitor_id）
    VISITOR_QUEUE = 'visitor:queue:{}'  # 访客排队信息
    
    # 统计数据
    STATS_SERVICE = 'stats:service:{}:{}'  # 客服统计（客服ID:日期）
    STATS_BUSINESS = 'stats:business:{}:{}'  # 商户统计（商户ID:日期）
    
    # 会话信息
    SESSION_ACTIVE = 'session:active:{}'  # 活跃会话（按客服ID）
    
    @staticmethod
    def make_key(pattern: str, *args) -> str:
        """
        生成缓存键
        
        Args:
            pattern: 键模板
            *args: 参数
            
        Returns:
            完整的缓存键
        """
        return pattern.format(*args)


# ========== 使用示例 ==========
"""
# 示例1：直接使用缓存管理器
from mod.utils.cache_manager import cache_manager, CacheKeys

# 设置缓存
cache_manager.set(
    CacheKeys.make_key(CacheKeys.VISITOR_INFO, visitor_id),
    visitor_data,
    ttl=600
)

# 获取缓存
visitor_data = cache_manager.get(
    CacheKeys.make_key(CacheKeys.VISITOR_INFO, visitor_id)
)

# 删除缓存
cache_manager.delete(CacheKeys.make_key(CacheKeys.VISITOR_INFO, visitor_id))

# 批量删除
cache_manager.clear_pattern('visitor:*')


# 示例2：使用装饰器缓存函数结果
from mod.utils.cache_manager import cache_manager

@cache_manager.cache_result(ttl=600, key_prefix='get_faq_list')
def get_faq_list(business_id, limit=10):
    # 从数据库查询
    return db.query(...)
"""

