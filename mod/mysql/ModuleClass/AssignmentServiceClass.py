"""
智能客服分配服务
实现访客到客服的智能分配逻辑
"""
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
from exts import db
from mod.mysql.models import Service, Queue, Visitor, Business
import log

logger = log.get_logger(__name__)


class AssignmentService:
    """智能客服分配服务"""
    
    def assign_visitor(self, visitor_id: str, business_id: int, 
                      exclusive_service_id: Optional[int] = None,
                      priority: int = 0) -> Dict:
        """
        智能分配访客到客服
        
        Args:
            visitor_id: 访客ID
            business_id: 商户ID
            exclusive_service_id: 专属客服ID（如有）
            priority: 优先级 0=普通 1=VIP 2=紧急
            
        Returns:
            {
                'action': 'assigned' | 'queued' | 'error',
                'service_id': int or None,
                'service': dict or None,
                'position': int or None (排队位置),
                'estimated_wait_time': int or None,
                'message': str,
                'is_exclusive': bool
            }
        """
        try:
            # 1. 检查是否已有活跃会话
            existing = self._get_active_session(visitor_id, business_id)
            if existing:
                service = Service.query.get(existing.service_id)
                return {
                    'action': 'assigned',
                    'service_id': existing.service_id,
                    'service': service.to_dict() if service else None,
                    'message': '会话已存在',
                    'is_exclusive': bool(existing.is_exclusive),
                    'session': existing.to_dict()
                }
            
            # 2. 专属客服场景
            if exclusive_service_id:
                return self._handle_exclusive_assignment(
                    visitor_id, business_id, exclusive_service_id, priority
                )
            
            # 3. 智能分配场景
            return self._handle_auto_assignment(
                visitor_id, business_id, priority
            )
            
        except Exception as e:
            logger.error(f"分配客服失败: visitor={visitor_id}, error={str(e)}")
            return {
                'action': 'error',
                'message': '系统繁忙，请稍后再试'
            }
    
    def _handle_exclusive_assignment(self, visitor_id: str, business_id: int,
                                    exclusive_service_id: int, priority: int) -> Dict:
        """处理专属客服分配"""
        # 验证专属客服
        service = Service.query.filter_by(
            service_id=exclusive_service_id,
            business_id=business_id
        ).first()
        
        if not service:
            return {
                'action': 'error',
                'message': '指定的客服不存在'
            }
        
        # 创建会话（无论客服是否在线）
        queue = Queue(
            visitor_id=visitor_id,
            service_id=exclusive_service_id,
            business_id=business_id,
            exclusive_service_id=exclusive_service_id,
            is_exclusive=1,
            priority=priority,
            state='normal',
            assign_status='assigned'
        )
        
        db.session.add(queue)
        db.session.commit()
        
        # ✅ 使用统一的接待数管理器
        from mod.mysql.ModuleClass.ServiceWorkloadManager import workload_manager
        workload_manager.increment_workload(
            exclusive_service_id,
            f"专属访客接入: {visitor_id}"
        )
        
        # 返回结果
        return {
            'action': 'assigned',
            'service_id': exclusive_service_id,
            'service': service.to_dict(include_workload=True),
            'message': f'已为您分配专属客服 {service.nick_name}',
            'is_exclusive': True,
            'is_online': service.state == 'online',
            'offline_tip': None if service.state == 'online' else f'{service.nick_name} 当前不在线，上线后会立即回复您'
        }
    
    def _handle_auto_assignment(self, visitor_id: str, business_id: int,
                               priority: int) -> Dict:
        """处理自动分配"""
        # 1. 查找可用客服
        available_service = self._find_available_service(business_id)
        
        # 2. 如果有可用客服，直接分配
        if available_service:
            queue = Queue(
                visitor_id=visitor_id,
                service_id=available_service.service_id,
                business_id=business_id,
                priority=priority,
                state='normal',
                assign_status='assigned'
            )
            
            db.session.add(queue)
            db.session.commit()
            
            # ✅ 使用统一的接待数管理器
            from mod.mysql.ModuleClass.ServiceWorkloadManager import workload_manager
            workload_manager.increment_workload(
                available_service.service_id,
                f"访客接入: {visitor_id}"
            )
            
            return {
                'action': 'assigned',
                'service_id': available_service.service_id,
                'service': available_service.to_dict(include_workload=True),
                'message': f'已为您分配客服 {available_service.nick_name}',
                'is_exclusive': False
            }
        
        # 3. 没有可用客服，加入排队
        return self._add_to_queue(visitor_id, business_id, priority)
    
    def _find_available_service(self, business_id: int) -> Optional[Service]:
        """
        查找可用客服（负载最低）
        
        优先级规则：
        1. 优先分配给在线且空闲的普通客服（level='service'）
        2. 如果普通客服都忙或离线，分配给管理员
        3. 如果所有人都不可用，返回 None（由调用方决定是否分配给机器人）
        
        Returns:
            Service or None
        """
        # 1. 查找在线且未满载的普通客服（排除机器人）
        normal_services = Service.query.filter_by(
            business_id=business_id,
            state='online',
            level='service'  # 仅查询普通客服
        ).filter(
            Service.current_chat_count < Service.max_concurrent_chats,
            Service.user_name != 'robot'  # ⚡ 排除机器人账号
        ).order_by(
            Service.current_chat_count.asc(),  # 按接待数升序（优先分配给空闲的）
            Service.last_assign_time.asc()  # 最后分配时间升序（MySQL不支持NULLS FIRST）
        ).all()
        
        if normal_services:
            # 有可用的普通客服，返回负载最低的
            logger.info(f"✅ 分配给普通客服: {normal_services[0].nick_name} (ID: {normal_services[0].service_id})")
            return normal_services[0]
        
        # 2. 没有可用的普通客服，查找在线且未满载的管理员
        admin_services = Service.query.filter_by(
            business_id=business_id,
            state='online'
        ).filter(
            Service.level.in_(['manager', 'super_manager'])  # 仅查询管理员
        ).filter(
            Service.current_chat_count < Service.max_concurrent_chats
        ).order_by(
            Service.current_chat_count.asc(),  # 按接待数升序
            Service.last_assign_time.asc()  # 最后分配时间升序（MySQL不支持NULLS FIRST）
        ).all()
        
        if admin_services:
            # 有可用的管理员，返回负载最低的
            logger.info(f"⚠️ 普通客服都忙/离线，分配给管理员: {admin_services[0].nick_name} (ID: {admin_services[0].service_id})")
            return admin_services[0]
        
        # 3. 所有客服和管理员都不可用
        logger.warning(f"⚠️ 所有客服和管理员都不可用，将分配给机器人: business_id={business_id}")
        return None
    
    def _add_to_queue(self, visitor_id: str, business_id: int,
                     priority: int) -> Dict:
        """加入排队"""
        # 创建排队记录
        queue = Queue(
            visitor_id=visitor_id,
            service_id=None,  # ✅ NULL 表示未分配（避免外键约束冲突）
            business_id=business_id,
            priority=priority,
            state='normal',
            assign_status='waiting'
        )
        
        db.session.add(queue)
        db.session.commit()
        
        # 计算排队位置和预估时间
        position = self._calculate_queue_position(visitor_id, business_id)
        estimated_time = self._estimate_wait_time(business_id, position, priority)
        
        # 更新队列信息
        queue.wait_position = position
        queue.estimated_wait_time = estimated_time
        db.session.commit()
        
        return {
            'action': 'queued',
            'service_id': None,
            'position': position,
            'estimated_wait_time': estimated_time,
            'message': self._generate_queue_message(position, estimated_time),
            'is_exclusive': False
        }
    
    def _calculate_queue_position(self, visitor_id: str, business_id: int) -> int:
        """计算排队位置（考虑优先级）"""
        current = Queue.query.filter(
            Queue.visitor_id == visitor_id,
            Queue.business_id == business_id,
            (Queue.service_id == None) | (Queue.service_id == 0),  # ✅ 兼容旧数据
            state='normal'
        ).first()
        
        if not current:
            return 0
        
        # 统计排在前面的人数
        count = Queue.query.filter(
            Queue.business_id == business_id,
            (Queue.service_id == None) | (Queue.service_id == 0),  # ✅ 兼容旧数据
            Queue.state == 'normal'
        ).filter(
            db.or_(
                Queue.priority > current.priority,
                db.and_(
                    Queue.priority == current.priority,
                    Queue.created_at < current.created_at
                )
            )
        ).count()
        
        return count + 1
    
    def _estimate_wait_time(self, business_id: int, position: int,
                           priority: int) -> int:
        """预估等待时间（秒）"""
        # 获取在线客服数
        online_count = Service.query.filter_by(
            business_id=business_id,
            state='online'
        ).count()
        
        if online_count == 0:
            return -1  # 无客服在线
        
        # 获取平均处理时间
        avg_handle_time = self._get_avg_handle_time(business_id)
        
        # 优先级权重
        priority_factor = 1.0
        if priority == 2:  # 紧急
            priority_factor = 0.3
        elif priority == 1:  # VIP
            priority_factor = 0.6
        
        # 计算预估时间
        estimated = (position / online_count) * avg_handle_time * priority_factor
        return int(estimated)
    
    def _get_avg_handle_time(self, business_id: int) -> float:
        """获取平均处理时间（秒）"""
        # 查询最近完成的会话
        recent = Queue.query.filter_by(
            business_id=business_id,
            state='complete'
        ).filter(
            Queue.updated_at >= datetime.now() - timedelta(hours=2)
        ).order_by(Queue.updated_at.desc()).limit(20).all()
        
        if not recent:
            return 300.0  # 默认5分钟
        
        total_time = 0
        valid_count = 0
        
        for q in recent:
            if q.created_at and q.updated_at:
                duration = (q.updated_at - q.created_at).total_seconds()
                # 过滤异常值
                if 30 <= duration <= 3600:
                    total_time += duration
                    valid_count += 1
        
        if valid_count > 0:
            return total_time / valid_count
        return 300.0
    
    def _generate_queue_message(self, position: int, estimated_time: int) -> str:
        """生成排队提示消息"""
        if estimated_time < 0:
            return f'您前面还有 {position - 1} 位访客在等待'
        
        minutes = estimated_time // 60
        if minutes == 0:
            return f'您前面还有 {position - 1} 位访客，预计等待不到1分钟'
        elif minutes <= 5:
            return f'您前面还有 {position - 1} 位访客，预计等待约 {minutes} 分钟'
        else:
            return f'您前面还有 {position - 1} 位访客，预计等待约 {minutes} 分钟。您也可以先查看常见问题或留言'
    
    def _get_active_session(self, visitor_id: str, business_id: int) -> Optional[Queue]:
        """获取活跃会话"""
        return Queue.query.filter_by(
            visitor_id=visitor_id,
            business_id=business_id,
            state='normal'
        ).first()
    
    def process_queue(self, business_id: int) -> int:
        """
        处理排队队列，为等待的访客分配空闲客服
        
        Returns:
            成功分配的数量
        """
        assigned_count = 0
        
        try:
            # 获取等待队列（按优先级排序）
            waiting = Queue.query.filter(
                Queue.business_id == business_id,
                (Queue.service_id == None) | (Queue.service_id == 0),  # ✅ 兼容旧数据
                Queue.state == 'normal',
                Queue.assign_status == 'waiting'
            ).order_by(
                Queue.priority.desc(),
                Queue.created_at.asc()
            ).all()
            
            for queue in waiting:
                # 查找可用客服
                service = self._find_available_service(business_id)
                if not service:
                    break  # 没有可用客服，停止处理
                
                # 分配客服
                queue.service_id = service.service_id
                queue.assign_status = 'assigned'
                queue.wait_position = None
                queue.estimated_wait_time = 0
                service.last_assign_time = datetime.now()
                
                assigned_count += 1
            
            if assigned_count > 0:
                db.session.commit()
                logger.info(f"队列处理完成: business={business_id}, assigned={assigned_count}")
            
        except Exception as e:
            logger.error(f"处理队列失败: business={business_id}, error={str(e)}")
            db.session.rollback()
        
        return assigned_count
    
    def update_queue_positions(self, business_id: int):
        """更新所有排队访客的位置和预估时间"""
        try:
            waiting = Queue.query.filter(
                Queue.business_id == business_id,
                (Queue.service_id == None) | (Queue.service_id == 0),  # ✅ 兼容旧数据
                Queue.state == 'normal',
                Queue.assign_status == 'waiting'
            ).order_by(
                Queue.priority.desc(),
                Queue.created_at.asc()
            ).all()
            
            for idx, queue in enumerate(waiting):
                position = idx + 1
                estimated_time = self._estimate_wait_time(
                    business_id, position, queue.priority or 0
                )
                
                queue.wait_position = position
                queue.estimated_wait_time = estimated_time
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"更新队列位置失败: {str(e)}")
            db.session.rollback()
    
    def check_reply_permission(self, service_id: int, visitor_id: str,
                              business_id: int) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        检查客服是否可以回复访客
        
        Returns:
            (can_reply: bool, reason: str, assigned_service: dict)
        """
        # 获取服务和会话
        service = Service.query.get(service_id)
        if not service:
            return False, '客服不存在', None
        
        session = Queue.query.filter_by(
            visitor_id=visitor_id,
            business_id=business_id,
            state='normal'
        ).first()
        
        if not session:
            # 没有会话，允许回复（会创建新会话）
            return True, None, None
        
        # 管理员权限特殊处理
        if service.level in ['super_manager', 'manager']:
            # 如果访客已分配给其他客服
            if session.service_id and session.service_id != service_id:
                assigned_service = Service.query.get(session.service_id)
                return False, f'该访客正由客服 {assigned_service.nick_name} 接待', \
                       assigned_service.to_dict() if assigned_service else None
            # 管理员可以回复未分配或自己的访客
            return True, None, None
        
        # 普通客服只能回复自己的访客
        if session.service_id == service_id:
            return True, None, None
        elif session.service_id > 0:
            assigned_service = Service.query.get(session.service_id)
            return False, f'该访客已分配给其他客服', \
                   assigned_service.to_dict() if assigned_service else None
        
        # 访客在排队中，不允许回复
        return False, '访客正在排队中', None
    
    def get_service_visitors(self, service_id: int, include_all: bool = False) -> List[Dict]:
        """
        获取客服的访客列表
        
        Args:
            service_id: 客服ID
            include_all: 是否包含所有访客（管理员）
        """
        service = Service.query.get(service_id)
        if not service:
            return []
        
        # 管理员可以看到所有访客
        if include_all and service.level in ['super_manager', 'manager']:
            sessions = Queue.query.filter_by(
                business_id=service.business_id,
                state='normal'
            ).filter(
                Queue.service_id > 0
            ).order_by(Queue.updated_at.desc()).all()
        else:
            # 普通客服只看到自己的访客
            sessions = Queue.query.filter_by(
                service_id=service_id,
                state='normal'
            ).order_by(Queue.updated_at.desc()).all()
        
        result = []
        for session in sessions:
            visitor = Visitor.query.get(session.visitor_id)
            if visitor:
                # 检查是否可以回复
                can_reply = session.service_id == service_id or \
                           (service.level in ['super_manager', 'manager'] and not session.service_id)
                
                # 获取负责客服信息
                assigned_service = None
                if session.service_id and session.service_id != service_id:
                    assigned_service = Service.query.get(session.service_id)
                
                result.append({
                    'visitor': visitor.to_dict(),
                    'session': session.to_dict(),
                    'can_reply': can_reply,
                    'assigned_service': assigned_service.to_dict() if assigned_service else None,
                    'is_mine': session.service_id == service_id
                })
        
        return result


# 全局实例
assignment_service = AssignmentService()

