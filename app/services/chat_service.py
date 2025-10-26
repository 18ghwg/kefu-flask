"""
聊天服务
"""
import time
import hashlib
from app import db
from app.models.chat import Chat
from app.models.queue import Queue
from app.services.robot_service import RobotService


class ChatService:
    """聊天服务"""
    
    def send_message(self, visitor_id, business_id, content, 
                    msg_type='text', direction='to_service', service_id=None):
        """发送消息"""
        # 如果没有指定客服，从队列中查找
        if not service_id:
            queue = Queue.query.filter_by(
                visitor_id=visitor_id,
                business_id=business_id,
                state='normal'
            ).first()
            
            if queue:
                service_id = queue.service_id
            else:
                service_id = 0
        
        # 生成唯一字符串
        timestamp = int(time.time())
        unstr = hashlib.md5(f"{visitor_id}{service_id}{timestamp}".encode()).hexdigest()
        
        # 创建消息记录
        chat = Chat(
            visitor_id=visitor_id,
            service_id=service_id,
            business_id=business_id,
            content=content,
            msg_type=1 if msg_type == 'text' else 2,
            direction=direction,
            state='unread',
            unstr=unstr,
            timestamp=timestamp
        )
        
        db.session.add(chat)
        db.session.commit()
        
        # 如果是访客发送且没有分配客服，检查机器人回复
        if direction == 'to_service' and service_id == 0 and msg_type == 'text':
            robot_service = RobotService()
            auto_reply = robot_service.get_auto_reply(business_id, content)
            
            if auto_reply:
                # 发送机器人回复
                self.send_message(
                    visitor_id=visitor_id,
                    business_id=business_id,
                    content=auto_reply,
                    msg_type='text',
                    direction='to_visitor',
                    service_id=0  # 0表示机器人
                )
        
        return chat
    
    def get_history(self, visitor_id, business_id=None, service_id=None, 
                   limit=50, offset=0):
        """获取历史消息"""
        query = Chat.query.filter_by(visitor_id=visitor_id)
        
        if business_id:
            query = query.filter_by(business_id=business_id)
        
        if service_id:
            query = query.filter_by(service_id=service_id)
        
        total = query.count()
        messages = query.order_by(Chat.timestamp.desc())\
                       .limit(limit).offset(offset).all()
        
        return messages, total
    
    def mark_as_read(self, visitor_id, service_id):
        """标记为已读"""
        chats = Chat.query.filter_by(
            visitor_id=visitor_id,
            service_id=service_id,
            state='unread'
        ).all()
        
        for chat in chats:
            chat.state = 'read'
        
        db.session.commit()
        
        return len(chats)
