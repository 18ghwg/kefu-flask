#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
聊天记录业务逻辑
负责聊天记录查询、会话管理等功能
"""
from datetime import datetime, timedelta
from sqlalchemy import and_, or_
from exts import db
from mod.mysql.models import Chat, Queue, Visitor, Service


class ChatService:
    """聊天记录服务"""
    
    @staticmethod
    def get_chat_history(business_id, visitor_id=None, service_id=None, 
                        start_date=None, end_date=None, keyword=None,
                        page=1, per_page=50):
        """
        获取聊天记录
        
        Args:
            business_id: 商户ID
            visitor_id: 访客ID（可选）
            service_id: 客服ID（可选）
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            keyword: 关键词（可选）
            page: 页码
            per_page: 每页数量
        
        Returns:
            dict: 聊天记录列表
        """
        try:
            # 构建查询，通过business_id过滤
            query = Chat.query.filter_by(business_id=business_id)
            
            if visitor_id:
                query = query.filter_by(visitor_id=visitor_id)
            
            if service_id:
                query = query.filter(Chat.service_id == service_id)
            
            if start_date:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(Chat.created_at >= start)
            
            if end_date:
                end = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(Chat.created_at < end)
            
            if keyword:
                query = query.filter(Chat.content.like(f'%{keyword}%'))
            
            # 排序和分页
            query = query.order_by(Chat.created_at.desc())
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            
            # 组装数据
            chat_list = []
            for chat in pagination.items:
                visitor = Visitor.query.filter_by(
                    visitor_id=chat.visitor_id,
                    business_id=business_id
                ).first()
                service = Service.query.filter_by(service_id=chat.service_id).first() if chat.service_id else None
                
                # 判断消息类型
                msg_type = 'text'
                if chat.msg_type == 2:
                    msg_type = 'image' if 'image' in chat.content or 'jpg' in chat.content or 'png' in chat.content else 'file'
                
                chat_list.append({
                    'id': chat.cid,
                    'visitor_id': chat.visitor_id,
                    'visitor_name': visitor.visitor_name if visitor else '未知',
                    'service_id': chat.service_id,
                    'service_name': service.nick_name if service else '机器人',
                    'content': chat.content,
                    'direction': chat.direction,
                    'msg_type': msg_type,
                    'timestamp': chat.created_at.isoformat() if chat.created_at else None
                })
            
            return {
                'code': 0,
                'data': {
                    'list': chat_list,
                    'total': pagination.total,
                    'pages': pagination.pages,
                    'page': page
                }
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {'code': -1, 'msg': f'获取聊天记录失败: {str(e)}'}
    
    @staticmethod
    def get_chat_sessions(business_id, state=None, page=1, per_page=20):
        """
        获取会话列表（从Chat表聚合）
        
        Args:
            business_id: 商户ID
            state: 状态筛选（waiting/chatting/complete）- 暂时忽略
            page: 页码
            per_page: 每页数量
        
        Returns:
            dict: 会话列表
        """
        try:
            from sqlalchemy import func, distinct
            
            # 从Chat表按visitor_id聚合会话
            # 获取每个访客的聊天记录
            chat_query = db.session.query(
                Chat.visitor_id,
                func.min(Chat.created_at).label('start_time'),
                func.max(Chat.created_at).label('end_time'),
                func.count(Chat.cid).label('message_count')
            ).filter_by(business_id=business_id)
            
            chat_query = chat_query.group_by(Chat.visitor_id)
            chat_query = chat_query.order_by(func.max(Chat.created_at).desc())
            
            # 分页
            offset = (page - 1) * per_page
            total_count = chat_query.count()
            sessions_data = chat_query.offset(offset).limit(per_page).all()
            
            session_list = []
            for sess_data in sessions_data:
                visitor_id = sess_data.visitor_id
                
                # 获取访客信息
                visitor = Visitor.query.filter_by(
                    visitor_id=visitor_id,
                    business_id=business_id
                ).first()
                
                # 获取该访客最近的客服ID（从Chat表中获取）
                latest_service_chat = Chat.query.filter_by(
                    visitor_id=visitor_id,
                    business_id=business_id
                ).filter(Chat.service_id > 0).order_by(Chat.created_at.desc()).first()
                
                service_id = latest_service_chat.service_id if latest_service_chat else 0
                service = Service.query.filter_by(service_id=service_id).first() if service_id > 0 else None
                
                # 计算会话时长
                duration = 0
                if sess_data.start_time and sess_data.end_time:
                    duration = int((sess_data.end_time - sess_data.start_time).total_seconds())
                
                # 判断状态（基于最后消息时间）
                from datetime import timedelta
                now = datetime.now()
                time_since_last = (now - sess_data.end_time).total_seconds() if sess_data.end_time else 9999
                
                if time_since_last < 1800:  # 30分钟内有消息
                    state_value = 'chatting'
                else:
                    state_value = 'complete'
                
                session_list.append({
                    'queue_id': visitor_id,  # 使用visitor_id作为标识
                    'visitor_id': visitor_id,
                    'visitor_name': visitor.name if visitor else f'访客{visitor_id}',
                    'service_id': service_id,
                    'service_name': service.nick_name if service else '机器人',
                    'state': state_value,
                    'message_count': sess_data.message_count,
                    'duration': duration,
                    'start_time': sess_data.start_time.isoformat() if sess_data.start_time else None,
                    'end_time': sess_data.end_time.isoformat() if sess_data.end_time else None
                })
            
            import math
            total_pages = math.ceil(total_count / per_page) if total_count > 0 else 1
            
            return {
                'code': 0,
                'data': {
                    'list': session_list,
                    'total': total_count,
                    'pages': total_pages,
                    'page': page
                }
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {'code': -1, 'msg': f'获取会话列表失败: {str(e)}'}
    
    @staticmethod
    def save_message(visitor_id, service_id, content, direction='to_service', msg_type='text'):
        """
        保存消息到数据库
        
        Args:
            visitor_id: 访客ID
            service_id: 客服ID
            content: 消息内容
            direction: 消息方向（to_service/to_visiter）
            msg_type: 消息类型（text/image/file）
        
        Returns:
            Chat: 保存的消息对象
        """
        try:
            chat = Chat(
                visiter_id=visitor_id,
                service_id=service_id,
                content=content,
                direction=direction,
                timestamp=datetime.now()
            )
            db.session.add(chat)
            db.session.commit()
            
            return chat
            
        except Exception as e:
            db.session.rollback()
            print(f'保存消息失败: {e}')
            return None
    
    @staticmethod
    def get_visitor_history(visitor_id, business_id, limit=50, offset=0):
        """
        获取访客的聊天历史记录
        
        Args:
            visitor_id: 访客ID
            business_id: 商户ID
            limit: 返回数量限制
            offset: 偏移量
        
        Returns:
            tuple: (messages列表, 总数)
        """
        try:
            # 查询该访客的所有聊天记录（按时间升序）
            query = Chat.query.filter_by(
                visitor_id=visitor_id,
                business_id=business_id
            ).order_by(Chat.created_at.asc())
            
            total = query.count()
            messages = query.offset(offset).limit(limit).all()
            
            return messages, total
            
        except Exception as e:
            print(f'获取访客历史消息失败: {e}')
            return [], 0


# 创建单例实例
chat_service = ChatService()
