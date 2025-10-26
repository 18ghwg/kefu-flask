"""
客服模型
"""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db


class Service(UserMixin, db.Model):
    """客服表"""
    
    __tablename__ = 'services'
    
    service_id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(255), unique=True, nullable=False, comment='用户名')
    nick_name = db.Column(db.String(255), nullable=False, comment='昵称')
    password_hash = db.Column(db.String(255), nullable=False, comment='密码哈希')
    
    # 基本信息
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False, comment='商户ID')
    group_id = db.Column(db.String(225), default='0', comment='客服分组')
    phone = db.Column(db.String(255), default='', comment='手机号')
    email = db.Column(db.String(255), default='', comment='邮箱')
    avatar = db.Column(db.String(1024), default='/static/images/avatar.png', comment='头像')
    
    # 权限级别
    level = db.Column(db.Enum('super_manager', 'manager', 'service'), 
                     default='service', comment='权限级别')
    
    # 状态
    state = db.Column(db.Enum('online', 'offline'), default='offline', comment='在线状态')
    offline_first = db.Column(db.SmallInteger, default=0, comment='优先离线')
    
    # 接待能力配置
    max_concurrent_chats = db.Column(db.Integer, default=5, comment='最大并发接待数')
    current_chat_count = db.Column(db.Integer, default=0, comment='当前接待数')
    last_assign_time = db.Column(db.DateTime, comment='最后分配时间')
    auto_accept = db.Column(db.SmallInteger, default=1, comment='是否自动接待')
    
    # 微信
    open_id = db.Column(db.String(255), default='', comment='微信OpenID')
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 关联关系
    chats = db.relationship('Chat', backref='service', lazy='dynamic',
                           foreign_keys='Chat.service_id')
    queues = db.relationship('Queue', backref='service', lazy='dynamic')
    
    def __repr__(self):
        return f'<Service {self.nick_name}>'
    
    def get_id(self):
        """Flask-Login需要的方法"""
        return str(self.service_id)
    
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')
    
    @password.setter
    def password(self, password):
        """设置密码"""
        # 使用与PHP相同的加密方式：md5(username + "hjkj" + password)
        import hashlib
        raw_password = f"{self.user_name}hjkj{password}"
        self.password_hash = hashlib.md5(raw_password.encode()).hexdigest()
    
    def verify_password(self, password):
        """验证密码"""
        import hashlib
        raw_password = f"{self.user_name}hjkj{password}"
        return self.password_hash == hashlib.md5(raw_password.encode()).hexdigest()
    
    @property
    def is_available(self):
        """是否可接待新访客"""
        return (self.state == 'online' and 
                self.auto_accept == 1 and 
                self.current_chat_count < self.max_concurrent_chats)
    
    @property
    def work_status(self):
        """工作状态"""
        if self.state == 'offline':
            return 'offline'
        if self.current_chat_count >= self.max_concurrent_chats:
            return 'full'
        if self.current_chat_count > 0:
            return 'busy'
        return 'idle'
    
    @property
    def utilization_rate(self):
        """负载率（0-1）"""
        if self.max_concurrent_chats <= 0:
            return 1.0
        return self.current_chat_count / self.max_concurrent_chats
    
    @property
    def available_slots(self):
        """可用接待位"""
        return max(0, self.max_concurrent_chats - self.current_chat_count)
    
    def to_dict(self, include_sensitive=False, include_workload=False):
        """转换为字典"""
        data = {
            'service_id': self.service_id,
            'user_name': self.user_name,
            'nick_name': self.nick_name,
            'business_id': self.business_id,
            'group_id': self.group_id,
            'phone': self.phone,
            'email': self.email,
            'avatar': self.avatar,
            'level': self.level,
            'state': self.state
        }
        
        if include_workload:
            data.update({
                'max_concurrent_chats': self.max_concurrent_chats,
                'current_chat_count': self.current_chat_count,
                'is_available': self.is_available,
                'work_status': self.work_status,
                'utilization_rate': round(self.utilization_rate * 100, 2),
                'available_slots': self.available_slots
            })
        
        if include_sensitive:
            data['open_id'] = self.open_id
        return data
