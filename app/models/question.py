"""
常见问题模型
"""
from app import db


class Question(db.Model):
    """常见问题表"""
    
    __tablename__ = 'questions'
    
    qid = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False, comment='商户ID')
    question = db.Column(db.Text, nullable=False, comment='问题')
    keyword = db.Column(db.String(12), default='', comment='关键词')
    answer = db.Column(db.Text, nullable=False, comment='答案（HTML）')
    answer_text = db.Column(db.Text, nullable=False, comment='答案（纯文本）')
    sort = db.Column(db.Integer, default=0, comment='排序')
    status = db.Column(db.SmallInteger, default=1, comment='状态：1显示 0不显示')
    
    # 索引
    __table_args__ = (
        db.Index('idx_business_id', 'business_id'),
        db.Index('idx_keyword', 'keyword'),
    )
    
    def __repr__(self):
        return f'<Question {self.qid}>'
    
    def to_dict(self):
        """转换为字典"""
        return {
            'qid': self.qid,
            'business_id': self.business_id,
            'question': self.question,
            'keyword': self.keyword,
            'answer': self.answer,
            'answer_text': self.answer_text,
            'sort': self.sort,
            'status': self.status
        }
