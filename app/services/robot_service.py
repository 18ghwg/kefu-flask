"""
机器人服务
"""
from app.models.robot import Robot
from mod.mysql.models import SystemSetting
from exts import db
import logging

logger = logging.getLogger(__name__)


class RobotService:
    """机器人自动回复服务"""
    
    def match_keyword(self, business_id, message, is_service_online=False):
        """
        匹配关键词
        
        Args:
            business_id: 商户ID
            message: 用户消息
            is_service_online: 是否有客服在线
        
        Returns:
            Robot对象或None
        """
        # 获取系统设置，检查回复模式
        settings = SystemSetting.query.filter_by(business_id=business_id).first()
        robot_reply_mode = settings.robot_reply_mode if settings else 'offline_only'
        
        logger.info(f"🤖 机器人匹配开始 - 消息: '{message}', 客服在线: {is_service_online}, 回复模式: {robot_reply_mode}")
        
        # 如果设置为仅离线回复，且有客服在线，则不回复
        if robot_reply_mode == 'offline_only' and is_service_online:
            logger.info(f"   ⏸️  客服在线且设置为仅离线回复，跳过机器人回复")
            return None
        
        # Robot表专门用于智能关键词匹配，不需要type字段过滤
        robots = Robot.query.filter_by(
            business_id=business_id,
            status=1
        ).order_by(Robot.sort.desc()).all()
        
        logger.info(f"   📚 查询到 {len(robots)} 条知识库记录")
        
        for robot in robots:
            logger.info(f"   🔍 检查关键词: '{robot.keyword}'")
            # 精确匹配或模糊匹配
            if robot.keyword in message or message in robot.keyword:
                logger.info(f"   ✅ 匹配成功! 关键词: '{robot.keyword}'")
                return robot
        
        logger.info(f"   ❌ 未找到匹配的关键词")
        return None
    
    def get_auto_reply(self, business_id, message, is_service_online=False):
        """
        获取自动回复
        
        Args:
            business_id: 商户ID
            message: 用户消息
            is_service_online: 是否有客服在线
        
        Returns:
            回复内容或None
        """
        robot = self.match_keyword(business_id, message, is_service_online)
        
        if robot:
            return robot.reply
        
        return None
    
    def add_knowledge(self, business_id, keyword, reply, sort=0, status=1):
        """添加知识库"""
        robot = Robot(
            business_id=business_id,
            keyword=keyword,
            reply=reply,
            sort=sort,
            status=status
        )
        
        db.session.add(robot)
        db.session.commit()
        
        return robot
    
    def update_knowledge(self, robot_id, keyword=None, reply=None, 
                        sort=None, status=None):
        """更新知识库"""
        robot = Robot.query.get(robot_id)
        
        if not robot:
            return None
        
        if keyword is not None:
            robot.keyword = keyword
        if reply is not None:
            robot.reply = reply
        if sort is not None:
            robot.sort = sort
        if status is not None:
            robot.status = status
        
        db.session.commit()
        
        return robot
