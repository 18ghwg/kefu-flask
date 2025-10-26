"""
缓存服务层
实现业务级别的缓存逻辑
"""
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from mod.utils.cache_manager import cache_manager, CacheKeys
from mod.mysql.models import Service, Visitor, Question, SystemSetting
from exts import db
import log

logger = log.get_logger(__name__)


class OnlineUserCache:
    """
    在线用户缓存服务
    
    设计原则：
    - Single Responsibility: 专注于在线用户的缓存管理
    - KISS: 简单直接的缓存更新和获取逻辑
    """
    
    @staticmethod
    def cache_online_service(service_id: int, service_name: str, ttl: int = 300):
        """
        缓存在线客服
        
        Args:
            service_id: 客服ID
            service_name: 客服名称
            ttl: 过期时间（秒），默认5分钟
        """
        try:
            # 使用 Redis Set 存储在线客服ID
            key = CacheKeys.ONLINE_SERVICES
            cache_manager.redis.sadd(cache_manager._make_key(key), service_id)
            
            # 设置客服详情缓存
            detail_key = f'service:detail:{service_id}'
            cache_manager.set(detail_key, {
                'service_id': service_id,
                'service_name': service_name,
                'online_time': datetime.now().isoformat()
            }, ttl)
            
            logger.debug(f"✅ 客服上线缓存：{service_name} ({service_id})")
            
        except Exception as e:
            logger.error(f"缓存在线客服失败: {e}")
    
    @staticmethod
    def remove_online_service(service_id: int):
        """
        移除在线客服缓存
        
        Args:
            service_id: 客服ID
        """
        try:
            key = CacheKeys.ONLINE_SERVICES
            cache_manager.redis.srem(cache_manager._make_key(key), service_id)
            
            # 删除客服详情缓存
            detail_key = f'service:detail:{service_id}'
            cache_manager.delete(detail_key)
            
            logger.debug(f"✅ 客服下线缓存移除：{service_id}")
            
        except Exception as e:
            logger.error(f"移除在线客服缓存失败: {e}")
    
    @staticmethod
    def get_online_services() -> List[Dict]:
        """
        获取在线客服列表
        
        Returns:
            在线客服列表
        """
        try:
            key = CacheKeys.ONLINE_SERVICES
            service_ids = cache_manager.redis.smembers(cache_manager._make_key(key))
            
            if not service_ids:
                return []
            
            # 获取客服详情
            services = []
            for service_id in service_ids:
                detail_key = f'service:detail:{service_id}'
                detail = cache_manager.get(detail_key)
                if detail:
                    services.append(detail)
            
            return services
            
        except Exception as e:
            logger.error(f"获取在线客服列表失败: {e}")
            return []
    
    @staticmethod
    def get_online_service_count() -> int:
        """
        获取在线客服数量
        
        Returns:
            在线客服数量
        """
        try:
            key = CacheKeys.ONLINE_SERVICES
            return cache_manager.redis.scard(cache_manager._make_key(key)) or 0
        except Exception as e:
            logger.error(f"获取在线客服数量失败: {e}")
            return 0
    
    @staticmethod
    def is_service_online(service_id: int) -> bool:
        """
        检查客服是否在线
        
        Args:
            service_id: 客服ID
            
        Returns:
            是否在线
        """
        try:
            key = CacheKeys.ONLINE_SERVICES
            return cache_manager.redis.sismember(
                cache_manager._make_key(key), 
                service_id
            )
        except Exception as e:
            logger.error(f"检查客服在线状态失败: {e}")
            return False


class SystemSettingsCache:
    """
    系统设置缓存服务
    
    设计原则：
    - 设置更新频率低，适合长时间缓存
    - 提供主动刷新机制
    """
    
    @staticmethod
    @cache_manager.cache_result(ttl=3600, key_prefix='get_settings')
    def get_settings(business_id: int = 1) -> Optional[Dict]:
        """
        获取系统设置（带缓存）
        
        Args:
            business_id: 商户ID
            
        Returns:
            系统设置字典
        """
        try:
            settings = SystemSetting.query.filter_by(
                business_id=business_id
            ).first()
            
            if settings:
                return {
                    'id': settings.id,
                    'business_id': settings.business_id,
                    'site_name': settings.site_name,
                    'site_logo': settings.site_logo,
                    'welcome_message': settings.welcome_message,
                    'offline_message': settings.offline_message,
                    'auto_reply_enabled': settings.auto_reply_enabled,
                    'work_time_start': settings.work_time_start,
                    'work_time_end': settings.work_time_end
                }
            
            return None
            
        except Exception as e:
            logger.error(f"获取系统设置失败: {e}")
            return None
    
    @staticmethod
    def refresh_settings(business_id: int = 1):
        """
        刷新系统设置缓存
        
        Args:
            business_id: 商户ID
        """
        try:
            # 删除缓存，下次获取时会重新加载
            cache_key = f'get_settings:{business_id}'
            cache_manager.delete(cache_key)
            logger.info(f"✅ 系统设置缓存已刷新：business_id={business_id}")
            
        except Exception as e:
            logger.error(f"刷新系统设置缓存失败: {e}")


class FAQCache:
    """
    常见问题缓存服务
    
    设计原则：
    - FAQ更新频率低，适合长时间缓存
    - 支持按商户和分类缓存
    """
    
    @staticmethod
    @cache_manager.cache_result(ttl=1800, key_prefix='get_faq_list')
    def get_faq_list(business_id: int = 1, limit: int = 10) -> List[Dict]:
        """
        获取常见问题列表（带缓存）
        
        Args:
            business_id: 商户ID
            limit: 数量限制
            
        Returns:
            常见问题列表
        """
        try:
            questions = Question.query.filter_by(
                business_id=business_id
            ).order_by(
                Question.sort.desc()
            ).limit(limit).all()
            
            return [
                {
                    'qid': q.qid,
                    'question': q.question,
                    'answer': q.answer,
                    'sort': q.sort
                }
                for q in questions
            ]
            
        except Exception as e:
            logger.error(f"获取常见问题列表失败: {e}")
            return []
    
    @staticmethod
    def refresh_faq_list(business_id: int = 1):
        """
        刷新常见问题缓存
        
        Args:
            business_id: 商户ID
        """
        try:
            # 删除所有FAQ相关缓存
            pattern = f'get_faq_list:{business_id}*'
            cache_manager.clear_pattern(pattern)
            logger.info(f"✅ 常见问题缓存已刷新：business_id={business_id}")
            
        except Exception as e:
            logger.error(f"刷新常见问题缓存失败: {e}")


class VisitorCache:
    """
    访客信息缓存服务
    
    设计原则：
    - 访客信息变化频率中等，使用适中的TTL
    - 提供访客基本信息和状态缓存
    """
    
    @staticmethod
    def cache_visitor_info(visitor_id: str, visitor_data: Dict, ttl: int = 600):
        """
        缓存访客信息
        
        Args:
            visitor_id: 访客ID
            visitor_data: 访客数据
            ttl: 过期时间（秒），默认10分钟
        """
        try:
            key = CacheKeys.make_key(CacheKeys.VISITOR_INFO, visitor_id)
            cache_manager.set(key, visitor_data, ttl)
            logger.debug(f"✅ 访客信息已缓存：{visitor_id}")
            
        except Exception as e:
            logger.error(f"缓存访客信息失败: {e}")
    
    @staticmethod
    def get_visitor_info(visitor_id: str) -> Optional[Dict]:
        """
        获取访客信息缓存
        
        Args:
            visitor_id: 访客ID
            
        Returns:
            访客信息字典
        """
        try:
            key = CacheKeys.make_key(CacheKeys.VISITOR_INFO, visitor_id)
            return cache_manager.get(key)
            
        except Exception as e:
            logger.error(f"获取访客信息缓存失败: {e}")
            return None
    
    @staticmethod
    def remove_visitor_info(visitor_id: str):
        """
        移除访客信息缓存
        
        Args:
            visitor_id: 访客ID
        """
        try:
            key = CacheKeys.make_key(CacheKeys.VISITOR_INFO, visitor_id)
            cache_manager.delete(key)
            logger.debug(f"✅ 访客信息缓存已移除：{visitor_id}")
            
        except Exception as e:
            logger.error(f"移除访客信息缓存失败: {e}")


class SessionCache:
    """
    会话缓存服务
    
    设计原则：
    - 会话状态变化频繁，使用较短的TTL
    - 提供客服活跃会话缓存
    """
    
    @staticmethod
    def cache_active_sessions(service_id: int, visitor_ids: List[str], ttl: int = 300):
        """
        缓存客服的活跃会话列表
        
        Args:
            service_id: 客服ID
            visitor_ids: 访客ID列表
            ttl: 过期时间（秒），默认5分钟
        """
        try:
            key = CacheKeys.make_key(CacheKeys.SESSION_ACTIVE, service_id)
            cache_manager.set(key, visitor_ids, ttl)
            logger.debug(f"✅ 活跃会话已缓存：service_id={service_id}, count={len(visitor_ids)}")
            
        except Exception as e:
            logger.error(f"缓存活跃会话失败: {e}")
    
    @staticmethod
    def get_active_sessions(service_id: int) -> List[str]:
        """
        获取客服的活跃会话列表
        
        Args:
            service_id: 客服ID
            
        Returns:
            访客ID列表
        """
        try:
            key = CacheKeys.make_key(CacheKeys.SESSION_ACTIVE, service_id)
            sessions = cache_manager.get(key)
            return sessions if sessions else []
            
        except Exception as e:
            logger.error(f"获取活跃会话失败: {e}")
            return []


# ========== 统计缓存 ==========
class StatsCache:
    """
    统计数据缓存服务
    
    设计原则：
    - 统计计算耗时，优先使用缓存
    - 支持按时间维度缓存
    """
    
    @staticmethod
    def cache_service_stats(service_id: int, date: str, stats_data: Dict, ttl: int = 1800):
        """
        缓存客服统计数据
        
        Args:
            service_id: 客服ID
            date: 日期（YYYY-MM-DD）
            stats_data: 统计数据
            ttl: 过期时间（秒），默认30分钟
        """
        try:
            key = CacheKeys.make_key(CacheKeys.STATS_SERVICE, service_id, date)
            cache_manager.set(key, stats_data, ttl)
            logger.debug(f"✅ 客服统计已缓存：service_id={service_id}, date={date}")
            
        except Exception as e:
            logger.error(f"缓存客服统计失败: {e}")
    
    @staticmethod
    def get_service_stats(service_id: int, date: str) -> Optional[Dict]:
        """
        获取客服统计数据缓存
        
        Args:
            service_id: 客服ID
            date: 日期（YYYY-MM-DD）
            
        Returns:
            统计数据字典
        """
        try:
            key = CacheKeys.make_key(CacheKeys.STATS_SERVICE, service_id, date)
            return cache_manager.get(key)
            
        except Exception as e:
            logger.error(f"获取客服统计缓存失败: {e}")
            return None


# ========== 导出所有缓存服务 ==========
__all__ = [
    'OnlineUserCache',
    'SystemSettingsCache',
    'FAQCache',
    'VisitorCache',
    'SessionCache',
    'StatsCache'
]

