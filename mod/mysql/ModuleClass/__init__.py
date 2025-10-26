"""
业务类封装
"""
# 导入业务类
from .RobotServiceClass import RobotService
from .VisitorServiceClass import VisitorService
from .QueueServiceClass import QueueService
from .ChatServiceClass import ChatService
from .StatisticsServiceClass import StatisticsService
from .ServiceManagementClass import ServiceManagement
from .CommentServiceClass import CommentService
from .SystemSettingServiceClass import SystemSettingService
from .IPLocationServiceClass import IPLocationService
from .QuestionServiceClass import QuestionService
from .OperationLogServiceClass import OperationLogService

# 导出单例实例（兼容旧代码）
from .QueueServiceClass import queue_service
from .ChatServiceClass import chat_service
# StatisticsService 需要参数初始化，不再提供单例
from .ServiceManagementClass import service_management
from .CommentServiceClass import comment_service
from .SystemSettingServiceClass import system_setting_service
from .IPLocationServiceClass import ip_location_service
from .QuestionServiceClass import question_service
from .OperationLogServiceClass import operation_log_service

__all__ = [
    'RobotService',
    'VisitorService',
    'QueueService',
    'ChatService',
    'StatisticsService',
    'ServiceManagement',
    'CommentService',
    'SystemSettingService',
    'IPLocationService',
    'QuestionService',
    'OperationLogService',
    'queue_service',
    'chat_service',
    # 'statistics_service',  # 已移除，需要参数初始化
    'service_management',
    'comment_service',
    'system_setting_service',
    'ip_location_service',
    'question_service',
    'operation_log_service'
]
