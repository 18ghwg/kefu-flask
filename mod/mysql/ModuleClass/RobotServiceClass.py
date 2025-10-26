"""
机器人服务
"""
from mod.mysql.models import Robot, SystemSetting
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
    
    # ========== 静态方法（用于API调用） ==========
    
    @staticmethod
    def get_knowledge_list(business_id, keyword='', type=None, page=1, per_page=20):
        """
        获取知识库列表（分页）
        
        Args:
            business_id: 商户ID
            keyword: 搜索关键词
            type: 知识库类型（暂时忽略）
            page: 页码
            per_page: 每页数量
        
        Returns:
            Flask-SQLAlchemy Pagination对象
        """
        query = Robot.query.filter_by(business_id=business_id)
        
        # 关键词搜索
        if keyword:
            query = query.filter(
                db.or_(
                    Robot.keyword.like(f'%{keyword}%'),
                    Robot.reply.like(f'%{keyword}%')
                )
            )
        
        # 排序
        query = query.order_by(Robot.sort.desc(), Robot.id.desc())
        
        # 分页
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return pagination
    
    @staticmethod
    def add_knowledge(business_id, keyword, reply, sort=0, status=1, type='keyword'):
        """添加知识库（静态方法版本）"""
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
    
    @staticmethod
    def update_knowledge(robot_id, keyword=None, reply=None, sort=None, status=None, type=None):
        """更新知识库（静态方法版本）"""
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
    
    @staticmethod
    def delete_knowledge(robot_id):
        """删除知识库"""
        robot = Robot.query.get(robot_id)
        
        if not robot:
            return False
        
        db.session.delete(robot)
        db.session.commit()
        
        return True
    
    @staticmethod
    def get_knowledge(robot_id):
        """获取知识库详情"""
        return Robot.query.get(robot_id)
    
    @staticmethod
    def match_keyword_static(message, business_id):
        """
        匹配关键词（静态方法版本 - 已重命名避免与实例方法冲突）
        
        Args:
            message: 用户消息
            business_id: 商户ID
        
        Returns:
            回复内容或None
        """
        robots = Robot.query.filter_by(
            business_id=business_id,
            status=1
        ).order_by(Robot.sort.desc()).all()
        
        for robot in robots:
            # 精确匹配或模糊匹配
            if robot.keyword in message or message in robot.keyword:
                return robot.reply
        
        return None
    
    @staticmethod
    def get_welcome_message(business_id):
        """
        获取欢迎语
        
        Args:
            business_id: 商户ID
        
        Returns:
            欢迎语内容
        """
        settings = SystemSetting.query.filter_by(business_id=business_id).first()
        
        if settings and settings.welcome_message:
            return settings.welcome_message
        
        # 默认欢迎语
        return "您好！有什么可以帮助您的吗？"
    
    @staticmethod
    def batch_import(business_id, data_list):
        """
        批量导入知识库
        
        Args:
            business_id: 商户ID
            data_list: 导入数据列表 [{'keyword': '...', 'reply': '...', ...}, ...]
        
        Returns:
            导入成功的数量
        """
        count = 0
        
        for data in data_list:
            if not data.get('keyword') or not data.get('reply'):
                continue
            
            robot = Robot(
                business_id=business_id,
                keyword=data['keyword'],
                reply=data['reply'],
                sort=data.get('sort', 0),
                status=data.get('status', 1)
            )
            
            db.session.add(robot)
            count += 1
        
        db.session.commit()
        
        return count
    
    @staticmethod
    def export_knowledge(business_id):
        """
        导出知识库
        
        Args:
            business_id: 商户ID
        
        Returns:
            知识库数据列表
        """
        robots = Robot.query.filter_by(business_id=business_id).order_by(Robot.sort.desc()).all()
        
        return [robot.to_dict() for robot in robots]