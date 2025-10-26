"""
数据库模型定义
"""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from exts import db


# ✅ 使用本地时区时间（非UTC）
def get_local_time():
    """获取本地时间"""
    return datetime.now()


# ========== 商户模型 ==========
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
    created_at = db.Column(db.DateTime, default=get_local_time, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=get_local_time, onupdate=get_local_time, comment='更新时间')
    
    # 关联关系
    services = db.relationship('Service', backref='business', lazy='dynamic')
    visitors = db.relationship('Visitor', backref='business', lazy='dynamic')
    chats = db.relationship('Chat', backref='business', lazy='dynamic')
    
    def __repr__(self):
        return f'<Business {self.business_name}>'
    
    def to_dict(self):
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


# ========== 客服模型 ==========
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
    level = db.Column(db.Enum('super_manager', 'manager', 'service'), default='service', comment='权限级别')
    
    # 状态
    state = db.Column(db.Enum('online', 'offline'), default='offline', comment='在线状态')
    offline_first = db.Column(db.SmallInteger, default=0, comment='优先离线')
    max_concurrent = db.Column(db.Integer, default=10, comment='最大并发会话数')
    
    # 接待能力配置（新增）
    max_concurrent_chats = db.Column(db.Integer, default=5, comment='最大并发接待数')
    current_chat_count = db.Column(db.Integer, default=0, comment='当前接待数')
    last_assign_time = db.Column(db.DateTime, comment='最后分配时间')
    auto_accept = db.Column(db.SmallInteger, default=1, comment='是否自动接待')
    
    # 微信
    open_id = db.Column(db.String(255), default='', comment='微信OpenID')
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=get_local_time, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=get_local_time, onupdate=get_local_time, comment='更新时间')
    
    # 关联关系
    chats = db.relationship('Chat', backref='service', lazy='dynamic', foreign_keys='Chat.service_id')
    queues = db.relationship('Queue', backref='service', lazy='dynamic')
    
    def __repr__(self):
        return f'<Service {self.nick_name}>'
    
    def get_id(self):
        return str(self.service_id)
    
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')
    
    @password.setter
    def password(self, password):
        import hashlib
        raw_password = f"{self.user_name}hjkj{password}"
        self.password_hash = hashlib.md5(raw_password.encode()).hexdigest()
    
    def verify_password(self, password):
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


# ========== 访客模型 ==========
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
    
    # IP地理位置信息
    country = db.Column(db.String(100), default='', comment='国家')
    province = db.Column(db.String(100), default='', comment='省份/州')
    city = db.Column(db.String(100), default='', comment='城市')
    country_code = db.Column(db.String(10), default='', comment='国家代码')
    latitude = db.Column(db.Float, comment='纬度')
    longitude = db.Column(db.Float, comment='经度')
    
    # 设备和浏览器信息
    user_agent = db.Column(db.String(512), default='', comment='User-Agent')
    browser = db.Column(db.String(128), default='', comment='浏览器')
    os = db.Column(db.String(128), default='', comment='操作系统')
    device = db.Column(db.String(128), default='', comment='设备类型')
    
    # 来源追踪
    referrer = db.Column(db.String(512), default='', comment='来源页面')
    utm_source = db.Column(db.String(128), default='', comment='UTM来源')
    utm_medium = db.Column(db.String(128), default='', comment='UTM媒介')
    utm_campaign = db.Column(db.String(128), default='', comment='UTM活动')
    
    # 分组和标签
    group_id = db.Column(db.Integer, db.ForeignKey('visitor_groups.id'), comment='分组ID')
    tags = db.Column(db.String(512), default='', comment='标签，逗号分隔')
    
    # 状态
    state = db.Column(db.Enum('online', 'offline'), default='offline', comment='在线状态')
    is_top = db.Column(db.SmallInteger, default=0, comment='是否置顶')
    is_blacklist = db.Column(db.SmallInteger, default=0, comment='是否黑名单')
    
    # 时间戳
    first_visit_time = db.Column(db.DateTime, default=get_local_time, comment='首次访问时间')
    last_visit_time = db.Column(db.DateTime, default=get_local_time, comment='最后访问时间')
    msg_time = db.Column(db.DateTime, comment='最后消息时间')
    created_at = db.Column(db.DateTime, default=get_local_time, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=get_local_time, onupdate=get_local_time, comment='更新时间')
    
    # 唯一约束
    __table_args__ = (
        db.UniqueConstraint('visitor_id', 'business_id', name='uix_visitor_business'),
        db.Index('idx_visitor_id', 'visitor_id'),
        db.Index('idx_business_id', 'business_id'),
        db.Index('idx_state', 'state'),
        db.Index('idx_group_id', 'group_id'),
    )
    
    def __repr__(self):
        return f'<Visitor {self.visitor_name}>'
    
    def get_full_location(self):
        """获取完整地理位置字符串"""
        parts = []
        if self.country:
            parts.append(self.country)
        if self.province:
            parts.append(self.province)
        if self.city:
            parts.append(self.city)
        return ' '.join(parts) if parts else '未知'
    
    def to_dict(self):
        """转换为字典"""
        return {
            'vid': self.vid,
            'visitor_id': self.visitor_id,
            'visitor_name': self.visitor_name,
            'channel': self.channel,
            'avatar': self.avatar,
            'name': self.name,
            'tel': self.tel,
            'connect': self.connect,
            'comment': self.comment,
            'business_id': self.business_id,
            'ip': self.ip,
            'from_url': self.from_url,
            'login_times': self.login_times,
            'user_agent': self.user_agent,
            'browser': self.browser,
            'os': self.os,
            'device': self.device,
            # 地理位置信息
            'country': self.country,
            'province': self.province,
            'city': self.city,
            'country_code': self.country_code,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'location': self.get_full_location(),
            # 其他信息
            'referrer': self.referrer,
            'utm_source': self.utm_source,
            'utm_medium': self.utm_medium,
            'utm_campaign': self.utm_campaign,
            'group_id': self.group_id,
            'tags': self.tags.split(',') if self.tags else [],
            'state': self.state,
            'is_top': self.is_top,
            'is_blacklist': self.is_blacklist,
            'first_visit_time': self.first_visit_time.isoformat() if self.first_visit_time else None,
            'last_visit_time': self.last_visit_time.isoformat() if self.last_visit_time else None,
            'msg_time': self.msg_time.isoformat() if self.msg_time else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


# ========== 聊天消息模型 ==========
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
    
    # 状态
    state = db.Column(db.Enum('read', 'unread'), default='unread', comment='阅读状态')
    
    # 唯一标识
    unstr = db.Column(db.String(32), default='', comment='唯一字符串')
    
    # 时间戳
    timestamp = db.Column(db.Integer, nullable=False, comment='时间戳')
    created_at = db.Column(db.DateTime, default=get_local_time, comment='创建时间')
    
    # 索引
    __table_args__ = (
        db.Index('idx_visitor_id', 'visitor_id'),
        db.Index('idx_service_id', 'service_id'),
        db.Index('idx_business_id', 'business_id'),
        db.Index('idx_timestamp', 'timestamp'),
    )
    
    def __repr__(self):
        return f'<Chat {self.cid}>'
    
    def to_dict(self):
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


# ========== 队列模型 ==========
class Queue(db.Model):
    """队列表（会话表）"""
    __tablename__ = 'queues'
    
    qid = db.Column(db.Integer, primary_key=True)
    visitor_id = db.Column(db.String(200), nullable=False, comment='访客ID')
    service_id = db.Column(db.Integer, db.ForeignKey('services.service_id'), nullable=True, comment='客服ID (NULL=未分配)')
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False, comment='商户ID')
    group_id = db.Column(db.Integer, default=0, comment='客服分组ID')
    
    # 状态
    state = db.Column(db.Enum('normal', 'complete', 'blacklist'), default='normal', comment='会话状态')
    
    # 排队和分配信息（新增）
    wait_position = db.Column(db.Integer, comment='排队位置')
    estimated_wait_time = db.Column(db.Integer, default=0, comment='预计等待时间(秒)')
    priority = db.Column(db.SmallInteger, default=0, comment='优先级: 0=普通,1=VIP,2=紧急')
    exclusive_service_id = db.Column(db.Integer, comment='专属客服ID')
    is_exclusive = db.Column(db.SmallInteger, default=0, comment='是否专属会话')
    assign_status = db.Column(db.Enum('waiting', 'assigned', 'timeout'), default='waiting', comment='分配状态')
    
    # 通知标记
    remind_tpl = db.Column(db.SmallInteger, default=0, comment='是否已发送模板消息')
    remind_comment = db.Column(db.SmallInteger, default=0, comment='是否已推送评价')
    remind_notification = db.Column(db.SmallInteger, default=0, comment='是否已发送通知')
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=get_local_time, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=get_local_time, onupdate=get_local_time, comment='更新时间')
    last_message_time = db.Column(db.DateTime, default=get_local_time, comment='最后消息时间')
    
    # 索引
    __table_args__ = (
        db.Index('idx_visitor_id', 'visitor_id'),
        db.Index('idx_service_id', 'service_id'),
        db.Index('idx_business_id', 'business_id'),
        db.Index('idx_state', 'state'),
        db.Index('idx_priority', 'priority'),
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


# ========== 机器人知识库模型 ==========
class Robot(db.Model):
    """机器人知识库表"""
    __tablename__ = 'robots'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False, comment='商户ID')
    keyword = db.Column(db.String(12), nullable=False, default='', comment='关键词')
    reply = db.Column(db.Text, nullable=False, comment='回复内容')
    sort = db.Column(db.Integer, default=0, comment='排序')
    status = db.Column(db.SmallInteger, default=1, comment='状态：1显示 0不显示')
    type = db.Column(db.String(20), default='keyword', comment='类型：faq-常见问题，keyword-智能关键词')
    
    # 索引
    __table_args__ = (
        db.Index('idx_business_id', 'business_id'),
        db.Index('idx_keyword', 'keyword'),
    )
    
    def __repr__(self):
        return f'<Robot {self.keyword}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'business_id': self.business_id,
            'keyword': self.keyword,
            'reply': self.reply,
            'sort': self.sort,
            'status': self.status,
            'type': self.type or 'keyword'
        }


# ========== 常见问题模型 ==========
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


# ========== 评价模型 ==========
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
    add_time = db.Column(db.DateTime, default=get_local_time, comment='添加时间')
    
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
    add_time = db.Column(db.DateTime, default=get_local_time, comment='添加时间')
    
    def __repr__(self):
        return f'<CommentSetting {self.id}>'


# ========== 分组模型 ==========
class ServiceGroup(db.Model):
    """客服分组表"""
    __tablename__ = 'service_groups'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False, comment='商户ID')
    group_name = db.Column(db.String(255), nullable=False, comment='分组名称')
    bgcolor = db.Column(db.String(50), default='#667eea', comment='背景颜色')
    description = db.Column(db.String(500), default='', comment='分组描述')
    add_time = db.Column(db.DateTime, default=get_local_time, comment='添加时间')
    status = db.Column(db.SmallInteger, default=1, comment='状态：1=启用，0=禁用')
    sort = db.Column(db.Integer, default=0, comment='排序')
    
    def __repr__(self):
        return f'<ServiceGroup {self.group_name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'business_id': self.business_id,
            'group_name': self.group_name,
            'bgcolor': self.bgcolor,
            'description': self.description,
            'add_time': self.add_time.strftime('%Y-%m-%d %H:%M:%S') if self.add_time else None,
            'status': self.status,
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
    created_at = db.Column(db.DateTime, default=get_local_time, comment='创建时间')
    
    def __repr__(self):
        return f'<VisitorGroup {self.group_name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'business_id': self.business_id,
            'service_id': self.service_id,
            'group_name': self.group_name,
            'status': self.status,
            'bgcolor': self.bgcolor
        }


# ========== 系统设置模型 ==========
class SystemSetting(db.Model):
    """系统设置表"""
    __tablename__ = 'system_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False, comment='商户ID')
    
    # 文件上传设置
    upload_max_size = db.Column(db.Integer, default=10485760, comment='最大文件大小（字节，默认10MB）')
    upload_allowed_types = db.Column(db.Text, default='image,document,archive', comment='客服允许的文件类型（逗号分隔）')
    upload_image_max_size = db.Column(db.Integer, default=5242880, comment='最大图片大小（字节，默认5MB）')
    visitor_upload_allowed_types = db.Column(db.Text, default='image', comment='访客允许的文件类型（默认只允许图片）')
    
    # 聊天设置
    chat_welcome_text = db.Column(db.Text, default='您好，有什么可以帮助您的？', comment='欢迎语')
    chat_offline_text = db.Column(db.Text, default='当前客服不在线，请留言', comment='离线提示')
    chat_queue_text = db.Column(db.Text, default='当前排队人数较多，请稍候', comment='排队提示')
    
    # 自动回复设置
    greeting_message = db.Column(db.Text, comment='访客进入时的问候语（支持HTML）')
    robot_reply_mode = db.Column(db.String(20), default='offline_only', comment='机器人回复模式：always-始终回复，offline_only-仅离线时回复')
    
    # 客服设置
    default_max_concurrent_chats = db.Column(db.Integer, default=5, comment='默认最大接待数（新建客服的默认值）')
    
    # 其他设置
    session_timeout = db.Column(db.Integer, default=1800, comment='会话超时时间（秒，默认30分钟）')
    auto_close_timeout = db.Column(db.Integer, default=300, comment='自动关闭超时（秒，默认5分钟）')
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=get_local_time, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=get_local_time, onupdate=get_local_time, comment='更新时间')
    
    def __repr__(self):
        return f'<SystemSetting business_id={self.business_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'business_id': self.business_id,
            'upload_max_size': self.upload_max_size,
            'upload_allowed_types': self.upload_allowed_types,
            'upload_image_max_size': self.upload_image_max_size,
            'default_max_concurrent_chats': self.default_max_concurrent_chats,
            'visitor_upload_allowed_types': self.visitor_upload_allowed_types,
            'chat_welcome_text': self.chat_welcome_text,
            'chat_offline_text': self.chat_offline_text,
            'chat_queue_text': self.chat_queue_text,
            'greeting_message': self.greeting_message,
            'robot_reply_mode': self.robot_reply_mode or 'offline_only',
            'session_timeout': self.session_timeout,
            'auto_close_timeout': self.auto_close_timeout
        }


# ========== 操作日志模型 ==========
class OperationLog(db.Model):
    """操作日志表"""
    __tablename__ = 'operation_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False, comment='商户ID')
    
    # 操作人信息
    operator_id = db.Column(db.Integer, nullable=False, comment='操作人ID')
    operator_name = db.Column(db.String(100), nullable=False, comment='操作人名称')
    operator_type = db.Column(db.Enum('admin', 'service', 'system'), default='admin', comment='操作人类型')
    
    # 操作信息
    module = db.Column(db.String(50), nullable=False, comment='操作模块（如：visitor, service, robot等）')
    action = db.Column(db.String(50), nullable=False, comment='操作动作（如：create, update, delete等）')
    description = db.Column(db.String(500), nullable=False, comment='操作描述')
    
    # 请求信息
    method = db.Column(db.String(10), default='', comment='HTTP方法')
    path = db.Column(db.String(255), default='', comment='请求路径')
    ip = db.Column(db.String(50), default='', comment='操作IP')
    user_agent = db.Column(db.String(500), default='', comment='User-Agent')
    
    # 操作详情
    target_id = db.Column(db.String(50), default='', comment='目标对象ID')
    target_type = db.Column(db.String(50), default='', comment='目标对象类型')
    params = db.Column(db.Text, default='', comment='请求参数（JSON）')
    result = db.Column(db.Enum('success', 'fail'), default='success', comment='操作结果')
    error_msg = db.Column(db.Text, default='', comment='错误信息')
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=get_local_time, comment='操作时间')
    
    def __repr__(self):
        return f'<OperationLog {self.operator_name} {self.action} {self.module}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'business_id': self.business_id,
            'operator_id': self.operator_id,
            'operator_name': self.operator_name,
            'operator_type': self.operator_type,
            'module': self.module,
            'action': self.action,
            'description': self.description,
            'method': self.method,
            'path': self.path,
            'ip': self.ip,
            'user_agent': self.user_agent,
            'target_id': self.target_id,
            'target_type': self.target_type,
            'params': self.params,
            'result': self.result,
            'error_msg': self.error_msg,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }


# ========== 客服评价模型 ==========
class ServiceRating(db.Model):
    """客服评价表"""
    __tablename__ = 'service_ratings'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    visitor_id = db.Column(db.String(200), nullable=False, index=True, comment='访客ID')
    service_id = db.Column(db.Integer, nullable=False, index=True, comment='客服ID')
    business_id = db.Column(db.Integer, nullable=False, index=True, comment='商户ID')
    queue_id = db.Column(db.Integer, comment='会话队列ID')
    
    # 评价内容
    rating = db.Column(db.SmallInteger, nullable=False, comment='评分 1-5星')
    comment = db.Column(db.Text, comment='评价内容')
    tags = db.Column(db.String(500), comment='评价标签，逗号分隔')
    
    # 访客信息
    visitor_name = db.Column(db.String(100), comment='访客昵称')
    visitor_ip = db.Column(db.String(50), comment='访客IP')
    
    # 时间
    created_at = db.Column(db.DateTime, default=datetime.now, comment='评价时间')
    
    def to_dict(self):
        return {
            'id': self.id,
            'visitor_id': self.visitor_id,
            'service_id': self.service_id,
            'business_id': self.business_id,
            'queue_id': self.queue_id,
            'rating': self.rating,
            'comment': self.comment,
            'tags': self.tags.split(',') if self.tags else [],
            'visitor_name': self.visitor_name,
            'visitor_ip': self.visitor_ip,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }