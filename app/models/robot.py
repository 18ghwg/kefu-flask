"""
机器人知识库模型
"""
from exts import db


class Robot(db.Model):
    """机器人知识库表"""
    
    __tablename__ = 'robots'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False, comment='商户ID')
    keyword = db.Column(db.String(12), nullable=False, default='', comment='关键词')
    reply = db.Column(db.Text, nullable=False, comment='回复内容')
    sort = db.Column(db.Integer, default=0, comment='排序')
    status = db.Column(db.SmallInteger, default=1, comment='状态：1显示 0不显示')
    
    # 索引
    __table_args__ = (
        db.Index('idx_business_id', 'business_id'),
        db.Index('idx_keyword', 'keyword'),
    )
    
    def __repr__(self):
        return f'<Robot {self.keyword}>'
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'business_id': self.business_id,
            'keyword': self.keyword,
            'reply': self.reply,
            'sort': self.sort,
            'status': self.status
        }
