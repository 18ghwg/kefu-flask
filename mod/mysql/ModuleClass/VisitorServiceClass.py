"""
访客管理业务逻辑
"""
from mod.mysql.models import Visitor, VisitorGroup, Chat, db
from sqlalchemy import or_, func, desc
from datetime import datetime, timedelta
import hashlib


class VisitorService:
    """访客管理服务"""
    
    @staticmethod
    def parse_user_agent(user_agent):
        """
        解析User-Agent，提取浏览器、操作系统、设备信息
        
        Args:
            user_agent: User-Agent字符串
            
        Returns:
            dict: {'browser': '', 'os': '', 'device': ''}
        """
        user_agent = user_agent.lower()
        
        # 解析浏览器
        browser = 'Unknown'
        if 'edge' in user_agent or 'edg/' in user_agent:
            browser = 'Microsoft Edge'
        elif 'chrome' in user_agent:
            browser = 'Google Chrome'
        elif 'safari' in user_agent and 'chrome' not in user_agent:
            browser = 'Safari'
        elif 'firefox' in user_agent:
            browser = 'Firefox'
        elif 'msie' in user_agent or 'trident' in user_agent:
            browser = 'Internet Explorer'
        
        # 解析操作系统
        os_name = 'Unknown'
        if 'windows nt 10' in user_agent:
            os_name = 'Windows 10/11'
        elif 'windows nt 6.3' in user_agent:
            os_name = 'Windows 8.1'
        elif 'windows nt 6.2' in user_agent:
            os_name = 'Windows 8'
        elif 'windows nt 6.1' in user_agent:
            os_name = 'Windows 7'
        elif 'mac os x' in user_agent:
            os_name = 'macOS'
        elif 'linux' in user_agent:
            os_name = 'Linux'
        elif 'android' in user_agent:
            os_name = 'Android'
        elif 'iphone' in user_agent or 'ipad' in user_agent:
            os_name = 'iOS'
        
        # 解析设备类型
        device = 'Desktop'
        if 'mobile' in user_agent or 'android' in user_agent or 'iphone' in user_agent:
            device = 'Mobile'
        elif 'tablet' in user_agent or 'ipad' in user_agent:
            device = 'Tablet'
        
        return {
            'browser': browser,
            'os': os_name,
            'device': device
        }
    
    @staticmethod
    def create_or_update_visitor(visitor_data):
        """
        创建或更新访客信息
        
        Args:
            visitor_data: 访客数据字典
            
        Returns:
            Visitor对象
        """
        visitor_id = visitor_data.get('visitor_id')
        business_id = visitor_data.get('business_id', 1)
        
        # 查找是否已存在
        visitor = Visitor.query.filter_by(
            visitor_id=visitor_id,
            business_id=business_id
        ).first()
        
        if visitor:
            # 更新访客信息
            visitor.login_times += 1
            visitor.last_visit_time = datetime.utcnow()
            visitor.state = 'online'
            
            # 更新其他信息（如果提供）
            if visitor_data.get('ip'):
                visitor.ip = visitor_data['ip']
            if visitor_data.get('from_url'):
                visitor.from_url = visitor_data['from_url']
            if visitor_data.get('user_agent'):
                visitor.user_agent = visitor_data['user_agent']
                # 解析浏览器和系统信息
                parsed = VisitorService.parse_user_agent(visitor_data['user_agent'])
                visitor.browser = parsed['browser']
                visitor.os = parsed['os']
                visitor.device = parsed['device']
            if visitor_data.get('referrer'):
                visitor.referrer = visitor_data['referrer']
            
        else:
            # 创建新访客
            visitor = Visitor(
                visitor_id=visitor_id,
                visitor_name=visitor_data.get('visitor_name', f'访客{visitor_id[:8]}'),
                channel=visitor_data.get('channel', 'web'),
                avatar=visitor_data.get('avatar', '/static/images/visitor.png'),
                business_id=business_id,
                ip=visitor_data.get('ip', ''),
                from_url=visitor_data.get('from_url', ''),
                user_agent=visitor_data.get('user_agent', ''),
                referrer=visitor_data.get('referrer', ''),
                utm_source=visitor_data.get('utm_source', ''),
                utm_medium=visitor_data.get('utm_medium', ''),
                utm_campaign=visitor_data.get('utm_campaign', ''),
                state='online',
                first_visit_time=datetime.utcnow(),
                last_visit_time=datetime.utcnow()
            )
            
            # 解析User-Agent
            if visitor_data.get('user_agent'):
                parsed = VisitorService.parse_user_agent(visitor_data['user_agent'])
                visitor.browser = parsed['browser']
                visitor.os = parsed['os']
                visitor.device = parsed['device']
            
            db.session.add(visitor)
        
        db.session.commit()
        return visitor
    
    @staticmethod
    def get_visitor_list(business_id, page=1, per_page=20, **filters):
        """
        获取访客列表
        
        Args:
            business_id: 商户ID
            page: 页码
            per_page: 每页数量
            filters: 过滤条件（state, group_id, keyword, is_blacklist等）
            
        Returns:
            分页对象
        """
        from mod.mysql.models import Queue
        
        query = Visitor.query.filter_by(business_id=business_id)
        
        # 状态过滤
        if filters.get('state'):
            query = query.filter_by(state=filters['state'])
        
        # 分组过滤
        if filters.get('group_id'):
            query = query.filter_by(group_id=filters['group_id'])
        
        # 黑名单过滤 - 通过JOIN Queue表查询
        is_blacklist = filters.get('is_blacklist')
        if is_blacklist is not None:
            if is_blacklist == 1:
                # 只显示黑名单访客
                query = query.join(
                    Queue,
                    (Queue.visitor_id == Visitor.visitor_id) & 
                    (Queue.business_id == business_id) & 
                    (Queue.state == 'blacklist')
                )
            elif is_blacklist == 0:
                # 只显示非黑名单访客
                # 使用子查询排除黑名单访客
                blacklist_subquery = db.session.query(Queue.visitor_id).filter(
                    Queue.business_id == business_id,
                    Queue.state == 'blacklist'
                ).subquery()
                
                query = query.filter(
                    ~Visitor.visitor_id.in_(blacklist_subquery)
                )
        
        # 关键词搜索
        keyword = filters.get('keyword')
        if keyword:
            query = query.filter(
                or_(
                    Visitor.visitor_name.like(f'%{keyword}%'),
                    Visitor.name.like(f'%{keyword}%'),
                    Visitor.tel.like(f'%{keyword}%'),
                    Visitor.ip.like(f'%{keyword}%')
                )
            )
        
        # 时间范围过滤
        if filters.get('start_date'):
            query = query.filter(Visitor.created_at >= filters['start_date'])
        if filters.get('end_date'):
            query = query.filter(Visitor.created_at <= filters['end_date'])
        
        # 排序（置顶优先，然后按最后访问时间）
        query = query.order_by(
            desc(Visitor.is_top),
            desc(Visitor.last_visit_time)
        )
        
        # 分页
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return pagination
    
    @staticmethod
    def get_visitor_detail(visitor_id, business_id):
        """
        获取访客详情
        
        Args:
            visitor_id: 访客ID
            business_id: 商户ID
            
        Returns:
            访客详情字典
        """
        visitor = Visitor.query.filter_by(
            visitor_id=visitor_id,
            business_id=business_id
        ).first()
        
        if not visitor:
            return None
        
        # 获取聊天记录统计
        chat_count = Chat.query.filter_by(visitor_id=visitor_id).count()
        
        # 获取最后一条消息
        last_chat = Chat.query.filter_by(visitor_id=visitor_id).order_by(
            desc(Chat.timestamp)
        ).first()
        
        # 组装详情
        detail = visitor.to_dict()
        detail['chat_count'] = chat_count
        detail['last_chat'] = last_chat.to_dict() if last_chat else None
        
        return detail
    
    @staticmethod
    def update_visitor(visitor_id, business_id, update_data):
        """
        更新访客信息
        
        Args:
            visitor_id: 访客ID
            business_id: 商户ID
            update_data: 更新数据
            
        Returns:
            更新后的Visitor对象
        """
        visitor = Visitor.query.filter_by(
            visitor_id=visitor_id,
            business_id=business_id
        ).first()
        
        if not visitor:
            return None
        
        # 更新允许的字段
        allowed_fields = ['name', 'tel', 'connect', 'comment', 'group_id', 'tags', 'is_top', 'is_blacklist']
        for field in allowed_fields:
            if field in update_data:
                setattr(visitor, field, update_data[field])
        
        db.session.commit()
        return visitor
    
    @staticmethod
    def add_tag(visitor_id, business_id, tag):
        """
        给访客添加标签
        
        Args:
            visitor_id: 访客ID
            business_id: 商户ID
            tag: 标签名称
            
        Returns:
            True/False
        """
        visitor = Visitor.query.filter_by(
            visitor_id=visitor_id,
            business_id=business_id
        ).first()
        
        if not visitor:
            return False
        
        tags = visitor.tags.split(',') if visitor.tags else []
        if tag not in tags:
            tags.append(tag)
            visitor.tags = ','.join(tags)
            db.session.commit()
        
        return True
    
    @staticmethod
    def remove_tag(visitor_id, business_id, tag):
        """
        移除访客标签
        
        Args:
            visitor_id: 访客ID
            business_id: 商户ID
            tag: 标签名称
            
        Returns:
            True/False
        """
        visitor = Visitor.query.filter_by(
            visitor_id=visitor_id,
            business_id=business_id
        ).first()
        
        if not visitor:
            return False
        
        tags = visitor.tags.split(',') if visitor.tags else []
        if tag in tags:
            tags.remove(tag)
            visitor.tags = ','.join(tags)
            db.session.commit()
        
        return True
    
    @staticmethod
    def set_blacklist(visitor_id, business_id, is_blacklist=1):
        """
        设置/取消黑名单
        
        Args:
            visitor_id: 访客ID
            business_id: 商户ID
            is_blacklist: 1-加入黑名单，0-移除黑名单
            
        Returns:
            True/False
        """
        visitor = Visitor.query.filter_by(
            visitor_id=visitor_id,
            business_id=business_id
        ).first()
        
        if not visitor:
            return False
        
        visitor.is_blacklist = is_blacklist
        db.session.commit()
        return True
    
    @staticmethod
    def get_statistics(business_id, days=7):
        """
        获取访客统计
        
        Args:
            business_id: 商户ID
            days: 统计天数
            
        Returns:
            统计数据字典
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # 总访客数
        total_visitors = Visitor.query.filter_by(business_id=business_id).count()
        
        # 在线访客数
        online_visitors = Visitor.query.filter_by(
            business_id=business_id,
            state='online'
        ).count()
        
        # 新访客数（近N天）
        new_visitors = Visitor.query.filter(
            Visitor.business_id == business_id,
            Visitor.created_at >= start_date
        ).count()
        
        # 回访访客数（登录次数>1）
        returning_visitors = Visitor.query.filter(
            Visitor.business_id == business_id,
            Visitor.login_times > 1
        ).count()
        
        # 黑名单数
        blacklist_count = Visitor.query.filter_by(
            business_id=business_id,
            is_blacklist=1
        ).count()
        
        return {
            'total_visitors': total_visitors,
            'online_visitors': online_visitors,
            'new_visitors': new_visitors,
            'returning_visitors': returning_visitors,
            'blacklist_count': blacklist_count
        }
    
    @staticmethod
    def get_source_statistics(business_id, days=30):
        """
        获取来源统计
        
        Args:
            business_id: 商户ID
            days: 统计天数
            
        Returns:
            来源统计列表
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # 按UTM来源统计
        source_stats = db.session.query(
            Visitor.utm_source,
            func.count(Visitor.vid).label('count')
        ).filter(
            Visitor.business_id == business_id,
            Visitor.created_at >= start_date,
            Visitor.utm_source != ''
        ).group_by(Visitor.utm_source).all()
        
        # 按设备类型统计
        device_stats = db.session.query(
            Visitor.device,
            func.count(Visitor.vid).label('count')
        ).filter(
            Visitor.business_id == business_id,
            Visitor.created_at >= start_date
        ).group_by(Visitor.device).all()
        
        # 按浏览器统计
        browser_stats = db.session.query(
            Visitor.browser,
            func.count(Visitor.vid).label('count')
        ).filter(
            Visitor.business_id == business_id,
            Visitor.created_at >= start_date
        ).group_by(Visitor.browser).all()
        
        return {
            'sources': [{'name': s[0], 'count': s[1]} for s in source_stats],
            'devices': [{'name': d[0], 'count': d[1]} for d in device_stats],
            'browsers': [{'name': b[0], 'count': b[1]} for b in browser_stats]
        }
    
    # ========== 访客分组管理 ==========
    
    @staticmethod
    def create_group(business_id, service_id, group_name, bgcolor='#707070'):
        """
        创建访客分组
        
        Args:
            business_id: 商户ID
            service_id: 客服ID
            group_name: 分组名称
            bgcolor: 背景色
            
        Returns:
            VisitorGroup对象
        """
        group = VisitorGroup(
            business_id=business_id,
            service_id=service_id,
            group_name=group_name,
            bgcolor=bgcolor
        )
        db.session.add(group)
        db.session.commit()
        return group
    
    @staticmethod
    def get_groups(business_id):
        """
        获取分组列表
        
        Args:
            business_id: 商户ID
            
        Returns:
            分组列表
        """
        groups = VisitorGroup.query.filter_by(
            business_id=business_id,
            status=1
        ).all()
        return [g.to_dict() for g in groups]
    
    @staticmethod
    def delete_group(group_id):
        """
        删除分组
        
        Args:
            group_id: 分组ID
            
        Returns:
            True/False
        """
        group = VisitorGroup.query.get(group_id)
        if not group:
            return False
        
        # 将该分组的访客移到未分组
        Visitor.query.filter_by(group_id=group_id).update({'group_id': None})
        
        db.session.delete(group)
        db.session.commit()
        return True

