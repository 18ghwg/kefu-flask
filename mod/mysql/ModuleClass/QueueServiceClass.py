#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
队列管理业务逻辑
负责访客排队、客服分配、会话转接等功能
"""
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, func
from exts import db
from mod.mysql.models import Queue, Service, Visitor, Chat


class QueueService:
    """队列管理服务"""
    
    @staticmethod
    def add_to_queue(visitor_id, business_id, priority=0):
        """
        添加访客到排队队列
        
        Args:
            visitor_id: 访客ID
            business_id: 商户ID
            priority: 优先级（0=普通，1=VIP，2=紧急）
        
        Returns:
            dict: 排队信息
        """
        try:
            # 检查是否已在队列中
            existing_queue = Queue.query.filter_by(
                visiter_id=visitor_id,
                business_id=business_id
            ).filter(
                Queue.state.in_(['waiting', 'chatting'])
            ).first()
            
            if existing_queue:
                return {
                    'code': 0,
                    'msg': '已在队列中',
                    'data': {
                        'queue_id': existing_queue.qid,
                        'position': QueueService.get_queue_position(visitor_id, business_id),
                        'state': existing_queue.state
                    }
                }
            
            # 创建新的排队记录
            queue = Queue(
                visiter_id=visitor_id,
                business_id=business_id,
                state='waiting',
                timestamp=datetime.now(),
                priority=priority
            )
            db.session.add(queue)
            db.session.commit()
            
            # 尝试自动分配客服
            QueueService.auto_assign_service(queue.qid)
            
            return {
                'code': 0,
                'msg': '加入队列成功',
                'data': {
                    'queue_id': queue.qid,
                    'position': QueueService.get_queue_position(visitor_id, business_id),
                    'state': queue.state
                }
            }
            
        except Exception as e:
            db.session.rollback()
            return {'code': -1, 'msg': f'加入队列失败: {str(e)}'}
    
    @staticmethod
    def get_queue_position(visitor_id, business_id):
        """
        获取访客在队列中的位置
        
        Args:
            visitor_id: 访客ID
            business_id: 商户ID
        
        Returns:
            int: 队列位置（从1开始）
        """
        try:
            # 查找当前访客的队列记录
            current_queue = Queue.query.filter_by(
                visiter_id=visitor_id,
                business_id=business_id,
                state='waiting'
            ).first()
            
            if not current_queue:
                return 0
            
            # 计算在他之前有多少人（按优先级和时间排序）
            position = Queue.query.filter(
                Queue.business_id == business_id,
                Queue.state == 'waiting',
                or_(
                    Queue.priority > current_queue.priority,
                    and_(
                        Queue.priority == current_queue.priority,
                        Queue.created_at < current_queue.created_at
                    )
                )
            ).count()
            
            return position + 1
            
        except Exception as e:
            print(f'获取队列位置失败: {e}')
            return 0
    
    @staticmethod
    def auto_assign_service(queue_id):
        """
        自动分配客服
        
        规则：
        1. 优先分配给普通客服（level='service'）
        2. 如果所有普通客服都繁忙或离线，才分配给管理员
        3. 优先分配给空闲客服
        4. 如果没有空闲客服，分配给会话数最少的客服
        5. 考虑客服的最大接待数限制
        
        Args:
            queue_id: 队列ID
        
        Returns:
            dict: 分配结果
        """
        try:
            # 获取队列记录
            queue = Queue.query.get(queue_id)
            if not queue or queue.state != 'waiting':
                return {'code': -1, 'msg': '队列记录不存在或状态不正确'}
            
            # 1. 先查找可用的普通客服（在线且未达到最大接待数）
            normal_services = Service.query.filter_by(
                business_id=queue.business_id,
                state='online',
                level='service'  # 仅查询普通客服
            ).all()
            
            # 计算每个普通客服的当前接待数
            best_service = None
            min_sessions = float('inf')
            
            for service in normal_services:
                # 计算当前接待数
                current_sessions = Queue.query.filter_by(
                    service_id=service.service_id,
                    state='chatting'
                ).count()
                
                # 检查是否达到最大接待数（默认5个）
                max_sessions = getattr(service, 'max_sessions', 5)
                if current_sessions >= max_sessions:
                    continue
                
                # 选择接待数最少的客服
                if current_sessions < min_sessions:
                    min_sessions = current_sessions
                    best_service = service
            
            # 如果找到可用的普通客服，直接分配
            if best_service:
                queue.service_id = best_service.service_id
                queue.state = 'chatting'
                queue.start_time = datetime.now()
                db.session.commit()
                
                return {
                    'code': 0,
                    'msg': '分配客服成功',
                    'data': {
                        'service_id': best_service.service_id,
                        'service_name': best_service.nick_name
                    }
                }
            
            # 2. 没有可用的普通客服，查找可用的管理员
            admin_services = Service.query.filter_by(
                business_id=queue.business_id,
                state='online'
            ).filter(
                Service.level.in_(['manager', 'super_manager'])
            ).all()
            
            if not admin_services:
                return {'code': -1, 'msg': '暂无在线客服'}
            
            # 计算每个管理员的当前接待数
            best_admin = None
            min_admin_sessions = float('inf')
            
            for service in admin_services:
                # 计算当前接待数
                current_sessions = Queue.query.filter_by(
                    service_id=service.service_id,
                    state='chatting'
                ).count()
                
                # 检查是否达到最大接待数（默认5个）
                max_sessions = getattr(service, 'max_sessions', 5)
                if current_sessions >= max_sessions:
                    continue
                
                # 选择接待数最少的管理员
                if current_sessions < min_admin_sessions:
                    min_admin_sessions = current_sessions
                    best_admin = service
            
            if not best_admin:
                return {'code': -1, 'msg': '所有客服已满载'}
            
            # 分配管理员
            queue.service_id = best_admin.service_id
            queue.state = 'chatting'
            queue.start_time = datetime.now()
            db.session.commit()
            
            return {
                'code': 0,
                'msg': '分配客服成功（管理员接入）',
                'data': {
                    'service_id': best_admin.service_id,
                    'service_name': best_admin.nick_name
                }
            }
            
        except Exception as e:
            db.session.rollback()
            return {'code': -1, 'msg': f'分配客服失败: {str(e)}'}
    
    @staticmethod
    def manual_assign_service(queue_id, service_id):
        """
        手动分配客服
        
        Args:
            queue_id: 队列ID
            service_id: 客服ID
        
        Returns:
            dict: 分配结果
        """
        try:
            queue = Queue.query.get(queue_id)
            if not queue:
                return {'code': -1, 'msg': '队列记录不存在'}
            
            service = Service.query.filter_by(service_id=service_id).first()
            if not service:
                return {'code': -1, 'msg': '客服不存在'}
            
            # 检查客服是否在线
            if service.state != 'online':
                return {'code': -1, 'msg': '客服不在线'}
            
            # 检查客服接待数
            current_sessions = Queue.query.filter_by(
                service_id=service_id,
                state='chatting'
            ).count()
            
            max_sessions = getattr(service, 'max_sessions', 5)
            if current_sessions >= max_sessions:
                return {'code': -1, 'msg': '客服接待数已满'}
            
            # 分配
            queue.service_id = service_id
            queue.state = 'chatting'
            queue.start_time = datetime.now()
            db.session.commit()
            
            return {
                'code': 0,
                'msg': '分配成功',
                'data': {
                    'service_id': service_id,
                    'service_name': service.nick_name
                }
            }
            
        except Exception as e:
            db.session.rollback()
            return {'code': -1, 'msg': f'分配失败: {str(e)}'}
    
    @staticmethod
    def transfer_session(queue_id, to_service_id):
        """
        转接会话到另一个客服
        
        Args:
            queue_id: 队列ID
            to_service_id: 目标客服ID
        
        Returns:
            dict: 转接结果
        """
        try:
            queue = Queue.query.get(queue_id)
            if not queue or queue.state not in ['normal', 'chatting']:  # ✅ 支持normal状态
                return {'code': -1, 'msg': '会话不存在或状态不正确'}
            
            # ✅ 检查是否已经是目标客服接待（避免重复转接）
            if queue.service_id == to_service_id:
                logger.info(f"⚪ 访客已由客服{to_service_id}接待，无需转接")
                return {
                    'code': 0,
                    'msg': '该访客已由目标客服接待',
                    'data': {
                        'from_service_id': to_service_id,
                        'to_service_id': to_service_id,
                        'to_service_name': None
                    }
                }
            
            # 检查目标客服
            to_service = Service.query.filter_by(service_id=to_service_id).first()
            if not to_service:
                return {'code': -1, 'msg': '目标客服不存在'}
            
            if to_service.state != 'online':
                return {'code': -1, 'msg': '目标客服不在线'}
            
            # 检查接待数（管理员不受限制）
            if to_service.level not in ['super_manager', 'manager']:
                current_sessions = Queue.query.filter_by(
                    service_id=to_service_id,
                    state='normal'  # ✅ 使用normal状态
                ).count()
                
                max_sessions = getattr(to_service, 'max_concurrent_chats', 5)  # ✅ 正确的字段名
                if current_sessions >= max_sessions:
                    return {'code': -1, 'msg': '目标客服接待数已满'}
            
            # 转接
            old_service_id = queue.service_id
            queue.service_id = to_service_id
            queue.updated_at = datetime.now()
            db.session.commit()
            
            # ✅ 使用统一的接待数管理器进行转移
            from mod.mysql.ModuleClass.ServiceWorkloadManager import workload_manager
            workload_manager.transfer_workload(
                old_service_id,
                to_service_id,
                f"会话转接: Queue#{queue_id}"
            )
            
            # 添加系统消息
            import time
            now = datetime.now()
            system_msg = Chat(
                visitor_id=queue.visitor_id,
                service_id=to_service_id,
                business_id=queue.business_id,
                content=f'会话已转接至客服 {to_service.nick_name}',
                created_at=now,
                timestamp=int(time.time()),  # ✅ 添加时间戳
                msg_type=1,  # ✅ 1=文本消息
                direction='to_visitor',  # ✅ 添加消息方向
                state='unread'  # ✅ 添加状态
            )
            db.session.add(system_msg)
            db.session.commit()
            
            logger.info(f"✅ 转接成功: Queue {queue_id} 从客服 {old_service_id} 转接到 {to_service_id}")
            
            return {
                'code': 0,
                'msg': '转接成功',
                'data': {
                    'from_service_id': old_service_id,
                    'to_service_id': to_service_id,
                    'to_service_name': to_service.nick_name
                }
            }
            
        except Exception as e:
            db.session.rollback()
            return {'code': -1, 'msg': f'转接失败: {str(e)}'}
    
    @staticmethod
    def end_session(queue_id):
        """
        结束会话
        
        Args:
            queue_id: 队列ID
        
        Returns:
            dict: 结果
        """
        try:
            queue = Queue.query.get(queue_id)
            if not queue:
                return {'code': -1, 'msg': '队列记录不存在'}
            
            queue.state = 'complete'
            queue.end_time = datetime.now()
            db.session.commit()
            
            return {'code': 0, 'msg': '会话已结束'}
            
        except Exception as e:
            db.session.rollback()
            return {'code': -1, 'msg': f'结束会话失败: {str(e)}'}
    
    @staticmethod
    def get_waiting_list(business_id, page=1, per_page=20):
        """
        获取等待队列列表
        
        Args:
            business_id: 商户ID
            page: 页码
            per_page: 每页数量
        
        Returns:
            dict: 队列列表
        """
        try:
            query = Queue.query.filter_by(
                business_id=business_id,
                state='waiting'
            ).order_by(
                Queue.priority.desc(),
                Queue.created_at.asc()
            )
            
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            
            queue_list = []
            for queue in pagination.items:
                visitor = Visitor.query.filter_by(visitor_id=queue.visiter_id).first()
                queue_list.append({
                    'queue_id': queue.qid,
                    'visitor_id': queue.visiter_id,
                    'visitor_name': visitor.visitor_name if visitor else '未知',
                    'priority': queue.priority,
                    'wait_time': int((datetime.now() - queue.timestamp).total_seconds()),
                    'position': QueueService.get_queue_position(queue.visiter_id, business_id),
                    'timestamp': queue.timestamp.isoformat()
                })
            
            return {
                'code': 0,
                'data': {
                    'list': queue_list,
                    'total': pagination.total,
                    'pages': pagination.pages,
                    'page': page
                }
            }
            
        except Exception as e:
            return {'code': -1, 'msg': f'获取队列失败: {str(e)}'}
    
    @staticmethod
    def get_service_sessions(service_id):
        """
        获取客服当前会话列表
        
        Args:
            service_id: 客服ID
        
        Returns:
            dict: 会话列表
        """
        try:
            sessions = Queue.query.filter_by(
                service_id=service_id,
                state='chatting'
            ).all()
            
            session_list = []
            for session in sessions:
                visitor = Visitor.query.filter_by(visitor_id=session.visiter_id).first()
                
                # 获取最后一条消息
                last_msg = Chat.query.filter_by(
                    visiter_id=session.visiter_id
                ).order_by(Chat.timestamp.desc()).first()
                
                session_list.append({
                    'queue_id': session.qid,
                    'visitor_id': session.visiter_id,
                    'visitor_name': visitor.visitor_name if visitor else '未知',
                    'avatar': visitor.avatar if visitor else '',
                    'start_time': session.start_time.isoformat() if session.start_time else None,
                    'duration': int((datetime.now() - session.start_time).total_seconds()) if session.start_time else 0,
                    'last_message': last_msg.content if last_msg else '',
                    'last_message_time': last_msg.timestamp.isoformat() if last_msg else None
                })
            
            return {
                'code': 0,
                'data': session_list
            }
            
        except Exception as e:
            return {'code': -1, 'msg': f'获取会话列表失败: {str(e)}'}
    
    @staticmethod
    def get_queue_statistics(business_id):
        """
        获取队列统计数据（用于首页展示）
        
        Args:
            business_id: 商户ID
        
        Returns:
            dict: 统计数据
        """
        try:
            from mod.mysql.models import Visitor, Service
            
            # 今日访问量（今日创建的访客数）
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_visits = Visitor.query.filter(
                Visitor.business_id == business_id,
                Visitor.created_at >= today_start
            ).count()
            
            # 进行中会话（等待+服务中）
            waiting_count = Queue.query.filter_by(
                business_id=business_id,
                state='waiting'
            ).count()
            
            chatting_count = Queue.query.filter_by(
                business_id=business_id,
                state='chatting'
            ).count()
            
            active_chats = waiting_count + chatting_count
            
            # 在线客服数量
            online_services = Service.query.filter_by(
                business_id=business_id,
                state='online'
            ).count()
            
            # 今日完成数（用于其他统计）
            today_complete = Queue.query.filter(
                Queue.business_id == business_id,
                Queue.state == 'complete',
                Queue.updated_at >= today_start
            ).count()
            
            # 平均响应时间（暂时返回0，需要从Chat表计算）
            avg_response_time = 0
            
            return {
                'code': 0,
                'data': {
                    # 首页需要的字段
                    'today_visits': today_visits,
                    'active_chats': active_chats,
                    'online_services': online_services,
                    'avg_response_time': avg_response_time,
                    
                    # 额外的统计数据
                    'waiting_count': waiting_count,
                    'chatting_count': chatting_count,
                    'today_complete': today_complete
                }
            }
            
        except Exception as e:
            return {'code': -1, 'msg': f'获取统计数据失败: {str(e)}'}
    
    @staticmethod
    def get_queue_statistics_for_service(business_id):
        """
        获取队列统计信息（客服工作台）
        
        Args:
            business_id: 商户ID
        
        Returns:
            dict: 统计数据
        """
        try:
            # 等待中的访客数
            waiting_count = Queue.query.filter_by(
                business_id=business_id,
                service_id=0,
                state='normal'
            ).count()
            
            # 进行中的会话数
            active_count = Queue.query.filter(
                Queue.business_id == business_id,
                Queue.service_id > 0,
                Queue.state == 'normal'
            ).count()
            
            # 在线客服数
            online_service_count = Service.query.filter_by(
                business_id=business_id,
                state='online'
            ).count()
            
            # 平均等待时间（分钟）
            avg_wait_time = 0
            waiting_queues = Queue.query.filter_by(
                business_id=business_id,
                service_id=0,
                state='normal'
            ).all()
            
            if waiting_queues:
                total_seconds = 0
                for queue in waiting_queues:
                    if queue.created_at:
                        wait_seconds = (datetime.now() - queue.created_at).total_seconds()
                        total_seconds += wait_seconds
                avg_wait_time = int(total_seconds / len(waiting_queues) / 60)
            
            return {
                'waiting_count': waiting_count,
                'active_count': active_count,
                'online_service_count': online_service_count,
                'avg_wait_time': avg_wait_time
            }
            
        except Exception as e:
            raise Exception(f'获取队列统计失败: {str(e)}')
    
    @staticmethod
    def get_waiting_list_simple(business_id, limit=50):
        """
        获取等待队列列表（简化版）
        
        Args:
            business_id: 商户ID
            limit: 最大数量
        
        Returns:
            list: 等待队列列表
        """
        try:
            # 按优先级降序，同优先级按创建时间升序
            queues = Queue.query.filter_by(
                business_id=business_id,
                service_id=0,
                state='normal'
            ).order_by(
                Queue.priority.desc() if hasattr(Queue, 'priority') else Queue.created_at.asc(),
                Queue.created_at.asc()
            ).limit(limit).all()
            
            waiting_list = []
            for queue in queues:
                visitor = Visitor.query.filter_by(visitor_id=queue.visitor_id).first()
                if visitor:
                    wait_time = 0
                    if queue.created_at:
                        wait_time = int((datetime.now() - queue.created_at).total_seconds())
                    
                    waiting_list.append({
                        'queue_id': queue.qid,
                        'visitor_id': visitor.visitor_id,
                        'visitor_name': visitor.visitor_name,
                        'avatar': visitor.avatar,
                        'wait_time': wait_time,
                        'created_at': queue.created_at.isoformat() if queue.created_at else None
                    })
            
            return waiting_list
            
        except Exception as e:
            raise Exception(f'获取等待队列失败: {str(e)}')
    
    @staticmethod
    def get_service_active_sessions_count(service_id):
        """
        获取客服的活跃会话数（用于实时统计）
        
        Args:
            service_id: 客服ID
        
        Returns:
            int: 活跃会话数
        """
        try:
            from datetime import datetime, timedelta
            five_minutes_ago = datetime.now() - timedelta(minutes=5)
            
            # 统计活跃会话：state=normal 且 5分钟内有消息
            count = Queue.query.filter_by(
                service_id=service_id,
                state='normal'
            ).filter(
                Queue.last_message_time >= five_minutes_ago  # 5分钟内有消息活动
            ).count()
            
            return count
            
        except Exception as e:
            raise Exception(f'获取客服活跃会话数失败: {str(e)}')
    
    @staticmethod
    def get_service_statistics(service_id, business_id):
        """
        获取客服的完整统计信息（用于工作台显示）
        
        Args:
            service_id: 客服ID
            business_id: 商户ID
        
        Returns:
            dict: 统计信息
        """
        try:
            from datetime import datetime, timedelta
            five_minutes_ago = datetime.now() - timedelta(minutes=5)
            
            # 1. 在线访客（当前客服接待的所有会话）
            online_visitors = Queue.query.filter_by(
                service_id=service_id,
                state='normal'
            ).count()
            
            # 2. 当前接待（活跃会话：5分钟内有消息）
            active_sessions = Queue.query.filter_by(
                service_id=service_id,
                state='normal'
            ).filter(
                Queue.last_message_time >= five_minutes_ago
            ).count()
            
            # 3. 待处理（排队中的访客 - 商户维度）
            pending_count = Queue.query.filter_by(
                business_id=business_id,
                service_id=0,  # 未分配客服
                state='normal'
            ).count()
            
            # 如果 service_id 为 None 或 0，说明还没分配，则待处理为0
            if not service_id or service_id == 0:
                pending_count = 0
            
            return {
                'online_visitors': online_visitors,  # 在线访客（当前接待的所有会话）
                'active_sessions': active_sessions,  # 当前活跃接待数
                'pending_count': pending_count,      # 待处理（排队中）
            }
            
        except Exception as e:
            raise Exception(f'获取客服统计信息失败: {str(e)}')
    
    @staticmethod
    def get_service_sessions_by_state(service_id, state='normal'):
        """
        获取客服的会话列表（按状态）
        
        Args:
            service_id: 客服ID
            state: 状态
        
        Returns:
            list: 会话列表
        """
        try:
            queues = Queue.query.filter_by(
                service_id=service_id,
                state=state
            ).order_by(Queue.updated_at.desc()).all()
            
            sessions = []
            for queue in queues:
                visitor = Visitor.query.filter_by(visitor_id=queue.visitor_id).first()
                if visitor:
                    sessions.append({
                        'queue_id': queue.qid,
                        'visitor_id': visitor.visitor_id,
                        'visitor_name': visitor.visitor_name,
                        'avatar': visitor.avatar,
                        'state': queue.state,
                        'created_at': queue.created_at.isoformat() if queue.created_at else None,
                        'updated_at': queue.updated_at.isoformat() if queue.updated_at else None
                    })
            
            return sessions
            
        except Exception as e:
            raise Exception(f'获取客服会话失败: {str(e)}')
    
    @staticmethod
    def claim_visitor(service_id, visitor_id):
        """
        客服认领访客
        
        Args:
            service_id: 客服ID
            visitor_id: 访客ID
        
        Returns:
            bool: 是否成功
        """
        try:
            queue = Queue.query.filter_by(
                visitor_id=visitor_id,
                service_id=0,
                state='normal'
            ).first()
            
            if not queue:
                return False
            
            queue.service_id = service_id
            queue.updated_at = datetime.now()
            db.session.commit()
            
            return True
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f'认领访客失败: {str(e)}')
    
    @staticmethod
    def transfer_service(visitor_id, from_service_id, to_service_id):
        """
        转接会话
        
        Args:
            visitor_id: 访客ID
            from_service_id: 源客服ID
            to_service_id: 目标客服ID
        
        Returns:
            bool: 是否成功
        """
        try:
            queue = Queue.query.filter_by(
                visitor_id=visitor_id,
                service_id=from_service_id,
                state='normal'
            ).first()
            
            if not queue:
                return False
            
            queue.service_id = to_service_id
            queue.updated_at = datetime.now()
            db.session.commit()
            
            return True
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f'转接会话失败: {str(e)}')
    
    @staticmethod
    def close_session(visitor_id, service_id):
        """
        关闭会话
        
        Args:
            visitor_id: 访客ID
            service_id: 客服ID
        
        Returns:
            bool: 是否成功
        """
        try:
            queue = Queue.query.filter_by(
                visitor_id=visitor_id,
                service_id=service_id,
                state='normal'
            ).first()
            
            if not queue:
                return False
            
            queue.state = 'complete'
            queue.updated_at = datetime.now()
            db.session.commit()
            
            return True
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f'关闭会话失败: {str(e)}')
    
    @staticmethod
    def add_to_blacklist(visitor_id, service_id, reason=''):
        """
        添加访客到黑名单
        
        Args:
            visitor_id: 访客ID
            service_id: 操作客服ID
            reason: 原因
        
        Returns:
            bool: 是否成功
        """
        try:
            # 查找当前会话
            queue = Queue.query.filter_by(
                visitor_id=visitor_id,
                state='normal'
            ).first()
            
            if not queue:
                # 如果已在黑名单
                blacklist_queue = Queue.query.filter_by(
                    visitor_id=visitor_id,
                    state='blacklist'
                ).first()
                
                if blacklist_queue:
                    return True  # 已在黑名单
                
                # 获取访客信息创建新记录
                visitor = Visitor.query.filter_by(visitor_id=visitor_id).first()
                if not visitor:
                    raise Exception('访客不存在')
                
                new_blacklist = Queue(
                    visitor_id=visitor_id,
                    business_id=visitor.business_id,
                    service_id=service_id,
                    group_id=0,
                    state='blacklist',
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.session.add(new_blacklist)
            else:
                # 修改现有会话状态
                queue.state = 'blacklist'
                queue.updated_at = datetime.now()
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f'添加黑名单失败: {str(e)}')
    
    @staticmethod
    def remove_from_blacklist(visitor_id):
        """
        从黑名单移除访客
        
        Args:
            visitor_id: 访客ID
        
        Returns:
            bool: 是否成功
        """
        try:
            blacklist_queue = Queue.query.filter_by(
                visitor_id=visitor_id,
                state='blacklist'
            ).first()
            
            if not blacklist_queue:
                return False
            
            db.session.delete(blacklist_queue)
            db.session.commit()
            
            return True
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f'移除黑名单失败: {str(e)}')
    
    @staticmethod
    def get_queue_position_public(visitor_id, business_id):
        """
        获取访客排队位置（公开接口）
        
        Args:
            visitor_id: 访客ID
            business_id: 商户ID
        
        Returns:
            dict: 位置信息
        """
        try:
            # 查找当前访客的队列记录
            current = Queue.query.filter_by(
                visitor_id=visitor_id,
                business_id=business_id,
                state='normal'
            ).first()
            
            if not current or current.service_id > 0:
                position = 0
            else:
                # 统计排在前面的人数（考虑优先级）
                count = Queue.query.filter_by(
                    business_id=business_id,
                    service_id=0,
                    state='normal'
                ).filter(
                    or_(
                        Queue.priority > current.priority if hasattr(Queue, 'priority') else False,
                        and_(
                            Queue.priority == current.priority if hasattr(Queue, 'priority') else True,
                            Queue.created_at < current.created_at
                        )
                    )
                ).count()
                position = count + 1
            
            return {
                'position': position,
                'is_waiting': position > 0
            }
            
        except Exception as e:
            raise Exception(f'获取排队位置失败: {str(e)}')
    
    @staticmethod
    def check_blacklist_status(visitor_id):
        """
        检查访客是否在黑名单中
        
        Args:
            visitor_id: 访客ID
        
        Returns:
            dict: 黑名单状态信息
        """
        try:
            blacklist_queue = Queue.query.filter_by(
                visitor_id=visitor_id,
                state='blacklist'
            ).first()
            
            if blacklist_queue:
                return {
                    'is_blacklisted': True,
                    'blacklist_time': blacklist_queue.created_at.isoformat() if blacklist_queue.created_at else None,
                    'service_id': blacklist_queue.service_id
                }
            else:
                return {
                    'is_blacklisted': False
                }
            
        except Exception as e:
            logger.error(f'检查黑名单状态失败: {e}')
            return {
                'is_blacklisted': False
            }
    
    @staticmethod
    def get_blacklist(business_id, limit=50):
        """
        获取黑名单列表
        
        Args:
            business_id: 商户ID
            limit: 最大数量
        
        Returns:
            list: 黑名单列表
        """
        try:
            blacklist_queues = Queue.query.filter_by(
                business_id=business_id,
                state='blacklist'
            ).order_by(Queue.updated_at.desc()).limit(limit).all()
            
            blacklist = []
            for queue in blacklist_queues:
                visitor = Visitor.query.filter_by(visitor_id=queue.visitor_id).first()
                if visitor:
                    blacklist.append({
                        'visitor_id': visitor.visitor_id,
                        'visitor_name': visitor.visitor_name,
                        'avatar': visitor.avatar,
                        'blacklist_time': queue.updated_at.isoformat() if queue.updated_at else None,
                        'operator_id': queue.service_id
                    })
            
            return blacklist
            
        except Exception as e:
            raise Exception(f'获取黑名单列表失败: {str(e)}')


# 创建单例实例
queue_service = QueueService()
