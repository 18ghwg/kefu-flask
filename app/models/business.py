"""
商户模型
"""
from datetime import datetime
from app import db


class Business(db.Model):
    """商户表"""
    
    __tablename__ = 'businesses'
    
    id = db.Column(db.Integer, primary_key=True)
    business_name = db.Column(db.String(100), nullable=False, comment='商户名称')
    logo = db.Column(db.String(255), default='', comment='Logo')
    copyright = db.Column(db.String(255), default='', comment='版权信息')
    
    # 功能开关
    video_state = db.Column(db.Enum('open', 'close'), default='close', comment='视频状态')
    audio_state = db.Column(db.Enum('open', 'close'), default='close', comment='音频状态')
    voice_state = db.Column(db.Enum('open', 'close'), default='open', comment='语音提示')
    template_state = db.Column(db.Enum('open', 'close'), default='close', comment='模板消息')
    
    # 业务配置
    distribution_rule = db.Column(db.Enum('auto', 'claim'), default='auto', comment='分配规则')
    voice_address = db.Column(db.String(255), default='/static/voice/default.mp3', comment='提示音地址')
    push_url = db.Column(db.String(255), default='', comment='推送URL')
    
    # 状态
    state = db.Column(db.Enum('open', 'close'), default='open', comment='商户状态')
    is_delete = db.Column(db.SmallInteger, default=0, comment='是否删除')
    
    # 多语言
    lang = db.Column(db.String(50), default='cn', comment='语言')
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 关联关系
    services = db.relationship('Service', backref='business', lazy='dynamic')
    visitors = db.relationship('Visitor', backref='business', lazy='dynamic')
    chats = db.relationship('Chat', backref='business', lazy='dynamic')
    
    def __repr__(self):
        return f'<Business {self.business_name}>'
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'business_name': self.business_name,
            'logo': self.logo,
            'copyright': self.copyright,
            'video_state': self.video_state,
            'audio_state': self.audio_state,
            'voice_state': self.voice_state,
            'distribution_rule': self.distribution_rule,
            'state': self.state,
            'lang': self.lang
        }
