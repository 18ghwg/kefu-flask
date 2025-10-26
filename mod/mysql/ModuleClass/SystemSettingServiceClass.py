"""
系统设置服务类
"""
from exts import db
from mod.mysql.models import SystemSetting
import log

logger = log.get_logger(__name__)


class SystemSettingService:
    """系统设置服务"""
    
    @staticmethod
    def get_or_create_settings(business_id):
        """
        获取或创建系统设置
        
        Args:
            business_id: 商户ID
        
        Returns:
            SystemSetting对象
        """
        try:
            settings = SystemSetting.query.filter_by(business_id=business_id).first()
            
            if not settings:
                # 创建默认设置
                settings = SystemSetting(business_id=business_id)
                db.session.add(settings)
                db.session.commit()
                logger.info(f'为商户 {business_id} 创建了默认系统设置')
            
            return settings
            
        except Exception as e:
            logger.error(f'获取系统设置失败: {e}')
            db.session.rollback()
            return None
    
    @staticmethod
    def update_settings(business_id, data):
        """
        更新系统设置
        
        Args:
            business_id: 商户ID
            data: 设置数据字典
        
        Returns:
            bool: 是否成功
        """
        try:
            settings = SystemSettingService.get_or_create_settings(business_id)
            
            if not settings:
                return False
            
            # 更新字段
            if 'upload_max_size' in data:
                settings.upload_max_size = int(data['upload_max_size'])
            
            if 'upload_allowed_types' in data:
                settings.upload_allowed_types = data['upload_allowed_types']
            
            if 'upload_image_max_size' in data:
                settings.upload_image_max_size = int(data['upload_image_max_size'])
            
            if 'chat_welcome_text' in data:
                settings.chat_welcome_text = data['chat_welcome_text']
            
            if 'chat_offline_text' in data:
                settings.chat_offline_text = data['chat_offline_text']
            
            if 'chat_queue_text' in data:
                settings.chat_queue_text = data['chat_queue_text']
            
            if 'greeting_message' in data:
                settings.greeting_message = data['greeting_message']
            
            if 'robot_reply_mode' in data:
                settings.robot_reply_mode = data['robot_reply_mode']
            
            if 'session_timeout' in data:
                settings.session_timeout = int(data['session_timeout'])
            
            if 'auto_close_timeout' in data:
                settings.auto_close_timeout = int(data['auto_close_timeout'])
            
            db.session.commit()
            logger.info(f'更新商户 {business_id} 的系统设置成功')
            
            return True
            
        except Exception as e:
            logger.error(f'更新系统设置失败: {e}')
            db.session.rollback()
            return False
    
    @staticmethod
    def get_upload_config(business_id):
        """
        获取文件上传配置
        
        Args:
            business_id: 商户ID
        
        Returns:
            dict: 上传配置
        """
        try:
            settings = SystemSettingService.get_or_create_settings(business_id)
            
            if not settings:
                # 返回默认配置
                return {
                    'max_size': 10485760,  # 10MB
                    'allowed_types': ['image', 'document', 'archive'],
                    'image_max_size': 5242880  # 5MB
                }
            
            # 解析允许的类型
            allowed_types = settings.upload_allowed_types.split(',') if settings.upload_allowed_types else []
            
            return {
                'max_size': settings.upload_max_size,
                'allowed_types': allowed_types,
                'image_max_size': settings.upload_image_max_size
            }
            
        except Exception as e:
            logger.error(f'获取上传配置失败: {e}')
            # 返回默认配置
            return {
                'max_size': 10485760,
                'allowed_types': ['image', 'document', 'archive'],
                'image_max_size': 5242880
            }


# 创建单例
system_setting_service = SystemSettingService()

