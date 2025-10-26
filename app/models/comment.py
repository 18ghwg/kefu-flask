"""
评价模型
"""
from datetime import datetime
from app import db


class Comment(db.Model):
    """评价表"""
    
    __tablename__ = 'comments'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False, comment='商户ID')
    service_id = db.Column(db.Integer, db.ForeignKey('services.service_id'), nullable=False, comment='客服ID')
    group_id = db.Column(db.Integer, default=0, comment='分组ID')
    visitor_id = db.Column(db.String(200), nullable=False, default='', comment='访客ID')
    visitor_name = db.Column(db.String(255), nullable=False, default='', comment='访客名称')
    word_comment = db.Column(db.Text, nullable=False, comment='文字评价')
    
    # 时间戳
    add_time = db.Column(db.DateTime, default=datetime.utcnow, comment='添加时间')
    
    # 关联关系
    details = db.relationship('CommentDetail', backref='comment', lazy='dynamic')
    
    # 索引
    __table_args__ = (
        db.Index('idx_business_id', 'business_id'),
        db.Index('idx_service_id', 'service_id'),
    )
    
    def __repr__(self):
        return f'<Comment {self.id}>'
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'business_id': self.business_id,
            'service_id': self.service_id,
            'visitor_id': self.visitor_id,
            'visitor_name': self.visitor_name,
            'word_comment': self.word_comment,
            'details': [d.to_dict() for d in self.details],
            'add_time': self.add_time.isoformat()
        }


class CommentDetail(db.Model):
    """评价详情表"""
    
    __tablename__ = 'comment_details'
    
    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=False, comment='评价ID')
    title = db.Column(db.String(32), nullable=False, default='', comment='评价项标题')
    score = db.Column(db.SmallInteger, default=1, comment='评分')
    
    def __repr__(self):
        return f'<CommentDetail {self.id}>'
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'title': self.title,
            'score': self.score
        }


class CommentSetting(db.Model):
    """评价设置表"""
    
    __tablename__ = 'comment_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False, comment='商户ID')
    title = db.Column(db.String(128), nullable=False, default='', comment='评价说明')
    comments = db.Column(db.Text, nullable=False, comment='评价条目（JSON）')
    word_switch = db.Column(db.Enum('open', 'close'), default='close', comment='文字评价开关')
    word_title = db.Column(db.String(32), nullable=False, default='', comment='文字评价标题')
    add_time = db.Column(db.DateTime, default=datetime.utcnow, comment='添加时间')
    
    def __repr__(self):
        return f'<CommentSetting {self.id}>'
