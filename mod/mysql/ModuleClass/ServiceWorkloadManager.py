"""
客服接待负载统一管理器
所有客服接待计数的变更都必须通过这个管理器进行，确保数据一致性
"""
from exts import db
from mod.mysql.models import Service, Queue
from datetime import datetime
import log

logger = log.get_logger(__name__)


class ServiceWorkloadManager:
    """客服接待负载管理器（单例模式）"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @staticmethod
    def _is_manager(service):
        """判断是否为管理员"""
        return service and service.level in ['super_manager', 'manager']
    
    def increment_workload(self, service_id: int, reason: str = '') -> dict:
        """
        增加客服接待数 +1
        
        Args:
            service_id: 客服ID
            reason: 变更原因（用于日志）
            
        Returns:
            {'success': bool, 'current_count': int, 'message': str}
        """
        try:
            service = Service.query.get(service_id)
            if not service:
                logger.error(f"❌ 增加接待数失败：客服{service_id}不存在")
                return {'success': False, 'message': '客服不存在'}
            
            # 管理员不计入接待数
            if self._is_manager(service):
                logger.info(f"⚪ 管理员 {service.nick_name} 不计入接待数")
                return {'success': True, 'current_count': 0, 'message': '管理员不计入'}
            
            # 增加计数
            old_count = service.current_chat_count or 0
            service.current_chat_count = old_count + 1
            service.last_assign_time = datetime.now()
            db.session.commit()
            
            logger.info(f"✅ 客服 {service.nick_name} (ID:{service_id}) 接待数增加: {old_count} -> {service.current_chat_count} | 原因: {reason or '未指定'}")
            
            # 广播工作负载更新
            self._broadcast_workload_update(service)
            
            return {
                'success': True,
                'current_count': service.current_chat_count,
                'message': '接待数已增加'
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ 增加接待数失败: {e}")
            return {'success': False, 'message': str(e)}
    
    def decrement_workload(self, service_id: int, reason: str = '') -> dict:
        """
        减少客服接待数 -1
        
        Args:
            service_id: 客服ID
            reason: 变更原因（用于日志）
            
        Returns:
            {'success': bool, 'current_count': int, 'message': str}
        """
        try:
            service = Service.query.get(service_id)
            if not service:
                logger.error(f"❌ 减少接待数失败：客服{service_id}不存在")
                return {'success': False, 'message': '客服不存在'}
            
            # 管理员不计入接待数
            if self._is_manager(service):
                logger.info(f"⚪ 管理员 {service.nick_name} 不计入接待数")
                return {'success': True, 'current_count': 0, 'message': '管理员不计入'}
            
            # 减少计数（不能小于0）
            old_count = service.current_chat_count or 0
            service.current_chat_count = max(0, old_count - 1)
            db.session.commit()
            
            logger.info(f"✅ 客服 {service.nick_name} (ID:{service_id}) 接待数减少: {old_count} -> {service.current_chat_count} | 原因: {reason or '未指定'}")
            
            # 广播工作负载更新
            self._broadcast_workload_update(service)
            
            return {
                'success': True,
                'current_count': service.current_chat_count,
                'message': '接待数已减少'
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ 减少接待数失败: {e}")
            return {'success': False, 'message': str(e)}
    
    def sync_workload(self, service_id: int, reason: str = '') -> dict:
        """
        同步客服接待数（从Queue表实时统计）
        这是最准确的方法，用于修复计数错误
        
        Args:
            service_id: 客服ID
            reason: 同步原因（用于日志）
            
        Returns:
            {'success': bool, 'current_count': int, 'old_count': int, 'message': str}
        """
        try:
            service = Service.query.get(service_id)
            if not service:
                logger.error(f"❌ 同步接待数失败：客服{service_id}不存在")
                return {'success': False, 'message': '客服不存在'}
            
            old_count = service.current_chat_count or 0
            
            # 管理员接待数始终为0
            if self._is_manager(service):
                service.current_chat_count = 0
                actual_count = 0
            else:
                # 从Queue表统计实际进行中的会话数
                actual_count = Queue.query.filter_by(
                    service_id=service_id,
                    state='normal'
                ).count()
                service.current_chat_count = actual_count
            
            db.session.commit()
            
            if old_count != actual_count:
                logger.info(f"🔄 客服 {service.nick_name} (ID:{service_id}) 接待数已同步: {old_count} -> {actual_count} | 原因: {reason or '未指定'}")
            else:
                logger.info(f"✅ 客服 {service.nick_name} (ID:{service_id}) 接待数准确: {actual_count}")
            
            # 广播工作负载更新
            self._broadcast_workload_update(service)
            
            return {
                'success': True,
                'current_count': actual_count,
                'old_count': old_count,
                'message': '接待数已同步'
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ 同步接待数失败: {e}")
            return {'success': False, 'message': str(e)}
    
    def transfer_workload(self, from_service_id: int, to_service_id: int, reason: str = '') -> dict:
        """
        转移访客（一个客服转给另一个客服）
        原客服 -1，新客服 +1
        
        Args:
            from_service_id: 原客服ID
            to_service_id: 新客服ID
            reason: 转移原因
            
        Returns:
            {'success': bool, 'message': str}
        """
        try:
            # 减少原客服接待数
            if from_service_id and from_service_id > 0:
                self.decrement_workload(from_service_id, f"转出访客 | {reason}")
            
            # 增加新客服接待数
            if to_service_id and to_service_id > 0:
                self.increment_workload(to_service_id, f"接收访客 | {reason}")
            
            logger.info(f"🔄 访客转移: 客服{from_service_id} -> 客服{to_service_id} | 原因: {reason or '未指定'}")
            
            return {'success': True, 'message': '转移成功'}
            
        except Exception as e:
            logger.error(f"❌ 转移访客失败: {e}")
            return {'success': False, 'message': str(e)}
    
    def sync_all_workloads(self, business_id: int = None) -> dict:
        """
        同步所有客服的接待数
        用于系统启动或批量修复
        
        Args:
            business_id: 商户ID（None表示所有商户）
            
        Returns:
            {'success': bool, 'synced_count': int, 'details': list}
        """
        try:
            query = Service.query
            if business_id:
                query = query.filter_by(business_id=business_id)
            
            services = query.all()
            synced_count = 0
            details = []
            
            for service in services:
                result = self.sync_workload(service.service_id, '批量同步')
                if result['success']:
                    synced_count += 1
                    if result['old_count'] != result['current_count']:
                        details.append({
                            'service_id': service.service_id,
                            'nick_name': service.nick_name,
                            'old_count': result['old_count'],
                            'new_count': result['current_count']
                        })
            
            logger.info(f"📊 批量同步完成: 共{len(services)}个客服, {synced_count}个成功, {len(details)}个有变化")
            
            return {
                'success': True,
                'synced_count': synced_count,
                'total_count': len(services),
                'details': details
            }
            
        except Exception as e:
            logger.error(f"❌ 批量同步失败: {e}")
            return {'success': False, 'message': str(e)}
    
    def _broadcast_workload_update(self, service):
        """
        广播工作负载更新到客服端（Socket.IO）
        仅对非管理员客服广播
        """
        try:
            # 管理员不需要广播
            if self._is_manager(service):
                return
            
            # 导入socketio和online_users（延迟导入避免循环依赖）
            from socketio_events import socketio, online_users
            
            # 查找该客服的所有在线连接
            for user_key, user_info in list(online_users.items()):
                if user_info.get('type') == 'service' and user_info.get('service_id') == service.service_id:
                    sids = user_info.get('sids', [])
                    for sid in sids:
                        socketio.emit('workload_update', {
                            'current': service.current_chat_count,
                            'max': service.max_concurrent_chats,
                            'utilization': round(service.current_chat_count / service.max_concurrent_chats * 100, 0) if service.max_concurrent_chats > 0 else 0
                        }, room=sid)
                        
            logger.debug(f"📡 已广播工作负载更新: {service.nick_name} -> {service.current_chat_count}")
            
        except Exception as e:
            logger.error(f"⚠️ 广播工作负载更新失败: {e}")


# 创建全局单例
workload_manager = ServiceWorkloadManager()

