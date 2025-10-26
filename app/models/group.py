"""
分组模型
"""
from datetime import datetime
from app import db


class ServiceGroup(db.Model):
    """客服分组表"""
    
    __tablename__ = 'service_groups'
    
    id = db.Column(db.Integer, primary_key=True)
    groupname = db.Column(db.String(255), comment='分组名称')
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False, comment='商户ID')
    sort = db.Column(db.Integer, default=0, comment='排序')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    
    def __repr__(self):
        return f'<ServiceGroup {self.groupname}>'
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'groupname': self.groupname,
            'business_id': self.business_id,
            'sort': self.sort
        }


class VisitorGroup(db.Model):
    """访客分组表"""
    
    __tablename__ = 'visitor_groups'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False, comment='商户ID')
    service_id = db.Column(db.Integer, db.ForeignKey('services.service_id'), nullable=False, comment='客服ID')
    group_name = db.Column(db.String(128), nullable=False, default='', comment='分组名称')
    status = db.Column(db.SmallInteger, default=1, comment='状态')
    bgcolor = db.Column(db.String(7), default='#707070', comment='背景色')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    
    def __repr__(self):
        return f'<VisitorGroup {self.group_name}>'
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'business_id': self.business_id,
            'service_id': self.service_id,
            'group_name': self.group_name,
            'status': self.status,
            'bgcolor': self.bgcolor
        }
