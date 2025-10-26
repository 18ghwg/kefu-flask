"""
队列模型
"""
from datetime import datetime
from app import db


class Queue(db.Model):
    """队列表（会话表）"""
    
    __tablename__ = 'queues'
    
    qid = db.Column(db.Integer, primary_key=True)
    visitor_id = db.Column(db.String(200), nullable=False, comment='访客ID')
    service_id = db.Column(db.Integer, db.ForeignKey('services.service_id'), nullable=True, comment='客服ID (NULL=未分配)')
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False, comment='商户ID')
    group_id = db.Column(db.Integer, default=0, comment='客服分组ID')
    
    # 状态
    state = db.Column(db.Enum('normal', 'complete', 'blacklist'), 
                     default='normal', comment='会话状态')
    
    # 排队和分配信息
    wait_position = db.Column(db.Integer, comment='排队位置')
    estimated_wait_time = db.Column(db.Integer, comment='预估等待时间（秒）')
    priority = db.Column(db.Integer, default=0, comment='优先级 0=普通 1=VIP 2=紧急')
    exclusive_service_id = db.Column(db.Integer, comment='专属客服ID')
    is_exclusive = db.Column(db.SmallInteger, default=0, comment='是否专属会话')
    assign_status = db.Column(db.Enum('waiting', 'assigned', 'timeout'), 
                             default='waiting', comment='分配状态')
    
    # 通知标记
    remind_tpl = db.Column(db.SmallInteger, default=0, comment='是否已发送模板消息')
    remind_comment = db.Column(db.SmallInteger, default=0, comment='是否已推送评价')
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 索引（包含性能优化的复合索引）
    __table_args__ = (
        # 单列索引
        db.Index('idx_visitor_id', 'visitor_id'),
        db.Index('idx_service_id', 'service_id'),
        db.Index('idx_business_id', 'business_id'),
        db.Index('idx_state', 'state'),
        # 复合索引（性能优化 - 2025-10-26）
        db.Index('idx_queue_service_state', 'service_id', 'state', 'updated_at'),  # 客服当前会话列表
        db.Index('idx_queue_waiting', 'business_id', 'assign_status', 'created_at'),  # 排队访客列表
        db.Index('idx_queue_visitor_state', 'visitor_id', 'state', 'created_at'),  # 访客会话状态
    )
    
    def __repr__(self):
        return f'<Queue {self.qid}>'
    
    @property
    def is_waiting(self):
        """是否在排队"""
        return self.service_id == 0 and self.state == 'normal'
    
    @property
    def is_assigned(self):
        """是否已分配客服"""
        return self.service_id > 0 and self.assign_status == 'assigned'
    
    def to_dict(self):
        """转换为字典"""
        data = {
            'qid': self.qid,
            'visitor_id': self.visitor_id,
            'service_id': self.service_id,
            'business_id': self.business_id,
            'group_id': self.group_id,
            'state': self.state,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        # 排队信息
        if self.is_waiting:
            data.update({
                'wait_position': self.wait_position,
                'estimated_wait_time': self.estimated_wait_time,
                'priority': self.priority
            })
        
        # 专属信息
        if self.is_exclusive:
            data.update({
                'is_exclusive': True,
                'exclusive_service_id': self.exclusive_service_id
            })
        
        return data
