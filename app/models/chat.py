"""
聊天消息模型
"""
from datetime import datetime
from app import db


class Chat(db.Model):
    """聊天消息表"""
    
    __tablename__ = 'chats'
    
    cid = db.Column(db.Integer, primary_key=True)
    visitor_id = db.Column(db.String(200), nullable=False, comment='访客ID')
    service_id = db.Column(db.Integer, db.ForeignKey('services.service_id'), nullable=False, comment='客服ID')
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False, comment='商户ID')
    
    # 消息内容
    content = db.Column(db.Text, nullable=False, comment='消息内容')
    msg_type = db.Column(db.SmallInteger, default=1, comment='消息类型')
    
    # 消息方向
    direction = db.Column(db.Enum('to_visitor', 'to_service'), comment='消息方向')
    
    # 会话信息
    exclusive_service_id = db.Column(db.Integer, comment='专属客服ID')
    assign_type = db.Column(db.Enum('auto', 'exclusive', 'manual'), default='auto', comment='分配类型')
    is_exclusive = db.Column(db.SmallInteger, default=0, comment='是否专属会话')
    
    # 状态
    state = db.Column(db.Enum('read', 'unread'), default='unread', comment='阅读状态')
    
    # 唯一标识（用于撤销）
    unstr = db.Column(db.String(32), default='', comment='唯一字符串')
    
    # 时间戳
    timestamp = db.Column(db.Integer, nullable=False, comment='时间戳')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    
    # 索引（包含性能优化的复合索引）
    __table_args__ = (
        # 单列索引
        db.Index('idx_visitor_id', 'visitor_id'),
        db.Index('idx_service_id', 'service_id'),
        db.Index('idx_business_id', 'business_id'),
        db.Index('idx_timestamp', 'timestamp'),
        # 复合索引（性能优化 - 2025-10-26）
        db.Index('idx_chat_visitor_timestamp', 'visitor_id', 'timestamp'),  # 访客查询历史消息
        db.Index('idx_chat_service_state', 'service_id', 'state', 'timestamp'),  # 客服未读消息统计
        db.Index('idx_chat_visitor_service', 'visitor_id', 'service_id', 'timestamp'),  # 会话消息查询
        db.Index('idx_chat_business_created', 'business_id', 'created_at'),  # 商户维度统计
    )
    
    def __repr__(self):
        return f'<Chat {self.cid}>'
    
    def to_dict(self):
        """转换为字典"""
        return {
            'cid': self.cid,
            'visitor_id': self.visitor_id,
            'service_id': self.service_id,
            'business_id': self.business_id,
            'content': self.content,
            'msg_type': self.msg_type,
            'direction': self.direction,
            'state': self.state,
            'timestamp': self.timestamp,
            'created_at': self.created_at.isoformat()
        }
