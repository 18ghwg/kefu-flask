"""
队列服务
"""
import time
from exts import db
from mod.mysql.models import Queue, Service, Business


class QueueService:
    """队列管理服务"""
    
    def add_to_queue(self, visitor_id, business_id, group_id=0, priority=0):
        """添加访客到队列（支持优先级）
        
        Args:
            visitor_id: 访客ID
            business_id: 商户ID
            group_id: 分组ID
            priority: 优先级 (0=普通, 1=VIP, 2=紧急)
        """
        # 检查是否已在队列中
        existing = Queue.query.filter_by(
            visitor_id=visitor_id,
            business_id=business_id,
            state='normal'
        ).first()
        
        if existing:
            # 更新优先级（如果新的优先级更高）
            if priority > existing.priority:
                existing.priority = priority
                db.session.commit()
            return existing
        
        # 创建新队列记录
        queue = Queue(
            visitor_id=visitor_id,
            service_id=0,  # 0表示排队中
            business_id=business_id,
            group_id=group_id,
            priority=priority,
            state='normal'
        )
        
        db.session.add(queue)
        db.session.commit()
        
        # 计算预计等待时间
        position = self.get_queue_position(visitor_id, business_id)
        estimated_time = self.estimate_wait_time(business_id, position, priority)
        if estimated_time >= 0:
            queue.estimated_wait_time = estimated_time
            db.session.commit()
        
        # 如果是高优先级，立即尝试分配
        if priority > 0:
            self._try_assign_immediately(queue)
        
        return queue
    
    def assign_service(self, visitor_id, business_id, group_id=0):
        """分配客服（智能分配算法）"""
        # 获取商户配置
        business = Business.query.get(business_id)
        if not business:
            return None
        
        # 添加到队列
        queue = self.add_to_queue(visitor_id, business_id, group_id)
        
        # 如果是自动分配模式
        if business.distribution_rule == 'auto':
            # 使用智能分配算法
            service = self._find_best_service(business_id, group_id)
            
            if service:
                queue.service_id = service.service_id
                db.session.commit()
                return service
        
        # 认领模式或没有在线客服，返回None
        return None
    
    def _find_best_service(self, business_id, group_id=0):
        """查找最佳客服（负载均衡算法）
        
        优先级规则：
        1. 优先分配给普通客服（level='service'）
        2. 如果所有普通客服都繁忙或离线，才分配给管理员
        """
        from sqlalchemy import func
        
        # 1. 先查找在线的普通客服
        normal_query = Service.query.filter_by(
            business_id=business_id,
            state='online',
            level='service'  # 仅查询普通客服
        )
        
        # 如果指定了分组，优先分配该分组的普通客服
        if group_id > 0:
            group_normal_services = normal_query.filter_by(group_id=str(group_id)).all()
            if group_normal_services:
                selected = self._select_by_load(group_normal_services)
                if selected:
                    return selected
        
        # 否则从所有在线普通客服中选择
        all_normal_services = normal_query.all()
        if all_normal_services:
            selected = self._select_by_load(all_normal_services)
            if selected:
                return selected
        
        # 2. 没有可用的普通客服，查找管理员
        admin_query = Service.query.filter_by(
            business_id=business_id,
            state='online'
        ).filter(
            Service.level.in_(['manager', 'super_manager'])
        )
        
        # 如果指定了分组，优先分配该分组的管理员
        if group_id > 0:
            group_admin_services = admin_query.filter_by(group_id=str(group_id)).all()
            if group_admin_services:
                selected = self._select_by_load(group_admin_services)
                if selected:
                    return selected
        
        # 否则从所有在线管理员中选择
        all_admin_services = admin_query.all()
        if all_admin_services:
            return self._select_by_load(all_admin_services)
        
        return None
    
    def _select_by_load(self, services):
        """根据负载选择客服（考虑并发限制）"""
        if not services:
            return None
        
        # 计算每个客服当前的会话数
        service_loads = []
        for service in services:
            # 统计当前会话数
            session_count = Queue.query.filter_by(
                service_id=service.service_id,
                state='normal'
            ).count()
            
            # 检查是否超过最大并发数
            max_concurrent = service.max_concurrent if hasattr(service, 'max_concurrent') else 10
            if session_count >= max_concurrent:
                continue  # 跳过已满的客服
            
            service_loads.append({
                'service': service,
                'load': session_count,
                'max': max_concurrent
            })
        
        if not service_loads:
            return None  # 所有客服都已满
        
        # 按负载排序，选择负载最小的
        service_loads.sort(key=lambda x: x['load'])
        return service_loads[0]['service']
    
    def claim_visitor(self, service_id, visitor_id):
        """客服认领访客"""
        queue = Queue.query.filter_by(
            visitor_id=visitor_id,
            service_id=0,
            state='normal'
        ).first()
        
        if not queue:
            return False
        
        queue.service_id = service_id
        db.session.commit()
        
        return True
    
    def transfer_service(self, visitor_id, from_service_id, to_service_id):
        """转接客服"""
        queue = Queue.query.filter_by(
            visitor_id=visitor_id,
            service_id=from_service_id,
            state='normal'
        ).first()
        
        if not queue:
            return False
        
        queue.service_id = to_service_id
        db.session.commit()
        
        return True
    
    def close_session(self, visitor_id, service_id):
        """关闭会话"""
        queue = Queue.query.filter_by(
            visitor_id=visitor_id,
            service_id=service_id,
            state='normal'
        ).first()
        
        if not queue:
            return False
        
        queue.state = 'complete'
        db.session.commit()
        
        return True
    
    def get_queue_position(self, visitor_id, business_id):
        """获取排队位置（考虑优先级）"""
        # 查找当前访客的队列记录
        current = Queue.query.filter_by(
            visitor_id=visitor_id,
            business_id=business_id,
            state='normal'
        ).first()
        
        if not current or current.service_id > 0:
            return 0
        
        # 统计排在前面的人数（考虑优先级）
        # 优先级高的排在前面，同优先级按创建时间排序
        count = Queue.query.filter_by(
            business_id=business_id,
            service_id=0,
            state='normal'
        ).filter(
            db.or_(
                Queue.priority > current.priority,  # 优先级更高
                db.and_(
                    Queue.priority == current.priority,  # 同优先级
                    Queue.created_at < current.created_at  # 但时间更早
                )
            )
        ).count()
        
        return count + 1
    
    def get_waiting_list(self, business_id, limit=50):
        """获取等待队列列表（按优先级排序）"""
        from mod.mysql.models import Visitor
        
        # 按优先级降序，同优先级按创建时间升序
        queues = Queue.query.filter_by(
            business_id=business_id,
            service_id=0,
            state='normal'
        ).order_by(
            Queue.priority.desc(),
            Queue.created_at.asc()
        ).limit(limit).all()
        
        result = []
        for queue in queues:
            visitor = Visitor.query.get(queue.visitor_id)
            if visitor:
                result.append({
                    'queue_id': queue.qid,
                    'visitor_id': visitor.visitor_id,
                    'visitor_name': visitor.visitor_name,
                    'avatar': visitor.avatar,
                    'wait_time': self._calculate_wait_time(queue.created_at),
                    'created_at': queue.created_at.isoformat()
                })
        
        return result
    
    def get_service_sessions(self, service_id, state='normal'):
        """获取客服的会话列表"""
        from mod.mysql.models import Visitor
        
        queues = Queue.query.filter_by(
            service_id=service_id,
            state=state
        ).order_by(Queue.updated_at.desc()).all()
        
        result = []
        for queue in queues:
            visitor = Visitor.query.get(queue.visitor_id)
            if visitor:
                result.append({
                    'queue_id': queue.qid,
                    'visitor_id': visitor.visitor_id,
                    'visitor_name': visitor.visitor_name,
                    'avatar': visitor.avatar,
                    'state': queue.state,
                    'created_at': queue.created_at.isoformat() if queue.created_at else None,
                    'updated_at': queue.updated_at.isoformat() if queue.updated_at else None
                })
        
        return result
    
    def get_queue_statistics(self, business_id):
        """获取队列统计信息"""
        from sqlalchemy import func
        
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
        from datetime import datetime
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
                    wait_seconds = (datetime.utcnow() - queue.created_at).total_seconds()
                    total_seconds += wait_seconds
            avg_wait_time = int(total_seconds / len(waiting_queues) / 60)
        
        return {
            'waiting_count': waiting_count,
            'active_count': active_count,
            'online_service_count': online_service_count,
            'avg_wait_time': avg_wait_time
        }
    
    def _calculate_wait_time(self, created_at):
        """计算等待时间（秒）"""
        from datetime import datetime
        if not created_at:
            return 0
        return int((datetime.utcnow() - created_at).total_seconds())
    
    def estimate_wait_time(self, business_id, position, priority=0):
        """预计等待时间（秒）
        
        Args:
            business_id: 商户ID
            position: 当前排队位置
            priority: 优先级
            
        Returns:
            预计等待时间（秒），-1表示无法估算
        """
        from datetime import datetime, timedelta
        
        # 1. 获取在线客服数
        online_count = Service.query.filter_by(
            business_id=business_id,
            state='online'
        ).count()
        
        if online_count == 0:
            return -1  # 无客服在线
        
        # 2. 获取最近10个已完成会话的平均处理时间
        recent_sessions = Queue.query.filter_by(
            business_id=business_id,
            state='complete'
        ).filter(
            Queue.updated_at >= datetime.utcnow() - timedelta(hours=2)
        ).order_by(Queue.updated_at.desc()).limit(20).all()
        
        if not recent_sessions:
            # 没有历史数据，根据优先级给出默认值
            if priority == 2:  # 紧急
                avg_handle_time = 120  # 2分钟
            elif priority == 1:  # VIP
                avg_handle_time = 180  # 3分钟
            else:  # 普通
                avg_handle_time = 300  # 5分钟
        else:
            total_time = 0
            valid_count = 0
            for session in recent_sessions:
                if session.created_at and session.updated_at:
                    duration = (session.updated_at - session.created_at).total_seconds()
                    # 过滤异常值（小于30秒或大于1小时）
                    if 30 <= duration <= 3600:
                        total_time += duration
                        valid_count += 1
            
            if valid_count > 0:
                avg_handle_time = total_time / valid_count
            else:
                avg_handle_time = 300  # 默认5分钟
        
        # 3. 计算预计等待时间
        # 考虑优先级的加权因子
        priority_factor = 1.0
        if priority == 2:  # 紧急
            priority_factor = 0.3  # 减少70%等待时间
        elif priority == 1:  # VIP
            priority_factor = 0.6  # 减少40%等待时间
        
        # 公式: (排队位置 / 在线客服数) * 平均处理时间 * 优先级因子
        estimated_seconds = (position / online_count) * avg_handle_time * priority_factor
        
        return int(estimated_seconds)
    
    def _try_assign_immediately(self, queue):
        """尝试立即分配客服（用于高优先级访客）"""
        service = self._find_best_service(queue.business_id, queue.group_id)
        if service:
            queue.service_id = service.service_id
            queue.estimated_wait_time = 0  # 已分配，无需等待
            db.session.commit()
            return True
        return False
    
    def update_estimated_wait_times(self, business_id):
        """更新所有排队访客的预计等待时间"""
        waiting_queues = Queue.query.filter_by(
            business_id=business_id,
            service_id=0,
            state='normal'
        ).order_by(
            Queue.priority.desc(),
            Queue.created_at.asc()
        ).all()
        
        for idx, queue in enumerate(waiting_queues):
            position = idx + 1
            estimated_time = self.estimate_wait_time(business_id, position, queue.priority)
            if estimated_time >= 0:
                queue.estimated_wait_time = estimated_time
        
        db.session.commit()
        return len(waiting_queues)
