"""
访客模型
"""
from datetime import datetime
from app import db


class Visitor(db.Model):
    """访客表"""
    
    __tablename__ = 'visitors'
    
    vid = db.Column(db.Integer, primary_key=True)
    visitor_id = db.Column(db.String(200), nullable=False, comment='访客唯一ID')
    visitor_name = db.Column(db.String(255), nullable=False, comment='访客名称')
    channel = db.Column(db.String(255), nullable=False, comment='访客频道')
    avatar = db.Column(db.String(1024), nullable=False, default='/static/images/visitor.png', comment='头像')
    
    # 联系信息
    name = db.Column(db.String(255), default='', comment='真实姓名')
    tel = db.Column(db.String(32), default='', comment='电话')
    connect = db.Column(db.Text, comment='联系方式')
    comment = db.Column(db.Text, comment='备注')
    
    # 访问信息
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False, comment='商户ID')
    ip = db.Column(db.String(255), nullable=False, comment='IP地址')
    from_url = db.Column(db.String(255), nullable=False, comment='来源URL')
    login_times = db.Column(db.Integer, default=1, comment='登录次数')
    extends = db.Column(db.Text, comment='浏览器扩展信息')
    
    # 状态
    state = db.Column(db.Enum('online', 'offline'), default='offline', comment='在线状态')
    is_top = db.Column(db.SmallInteger, default=0, comment='是否置顶')
    
    # 时间戳
    msg_time = db.Column(db.DateTime, comment='最后消息时间')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 唯一约束和索引（包含性能优化的复合索引）
    __table_args__ = (
        # 唯一约束
        db.UniqueConstraint('visitor_id', 'business_id', name='uix_visitor_business'),
        # 单列索引
        db.Index('idx_visitor_id', 'visitor_id'),
        db.Index('idx_business_id', 'business_id'),
        # 复合索引（性能优化 - 2025-10-26）
        db.Index('idx_visitor_state_msgtime', 'business_id', 'state', 'msg_time'),  # 在线访客列表
        db.Index('idx_visitor_ip_business', 'ip', 'business_id'),  # IP搜索
    )
    
    # 关联关系
    chats = db.relationship('Chat', backref='visitor', lazy='dynamic',
                           foreign_keys='Chat.visitor_id', 
                           primaryjoin='Visitor.visitor_id==Chat.visitor_id')
    queues = db.relationship('Queue', backref='visitor', lazy='dynamic',
                            foreign_keys='Queue.visitor_id',
                            primaryjoin='Visitor.visitor_id==Queue.visitor_id')
    
    def __repr__(self):
        return f'<Visitor {self.visitor_name}>'
    
    def to_dict(self):
        """转换为字典"""
        return {
            'vid': self.vid,
            'visitor_id': self.visitor_id,
            'visitor_name': self.visitor_name,
            'avatar': self.avatar,
            'name': self.name,
            'tel': self.tel,
            'ip': self.ip,
            'from_url': self.from_url,
            'login_times': self.login_times,
            'state': self.state,
            'msg_time': self.msg_time.isoformat() if self.msg_time else None,
            'created_at': self.created_at.isoformat()
        }
