"""
客服API蓝图
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from exts import db
from mod.mysql.models import Queue, Visitor, Service, Chat
from mod.mysql.ModuleClass.QueueServiceClass import QueueService
from mod.mysql.ModuleClass import chat_service
from sqlalchemy import case, and_, or_, func
from datetime import datetime
import log
import re  # ⚡ 用于过滤HTML标签

service_bp = Blueprint('service', __name__)
logger = log.get_logger(__name__)


def strip_html_tags(text):
    """
    移除HTML标签，保留纯文本
    用于显示消息预览
    
    职责：
    - JSON格式消息：保留完整JSON（由前端formatLastMessage解析）
    - 普通文本消息：移除HTML标签（但不截断，由前端控制显示长度）
    
    ⚡ 优化（2025-10-26）：
    - 使用严格的JSON验证，避免误判
    """
    if not text:
        return ''
    
    # ⚡ 严格的JSON检测（避免误判普通文本）
    try:
        import json
        parsed = json.loads(text)
        # 确认是字典且包含type字段（文件/图片消息的标准格式）
        if isinstance(parsed, dict) and 'type' in parsed:
            return text  # 保留完整JSON，由前端解析
    except (json.JSONDecodeError, ValueError, TypeError):
        pass  # 不是有效JSON，继续处理为普通文本
    
    # 移除所有HTML标签
    clean = re.sub(r'<[^>]+>', '', text)
    # 移除多余空格
    clean = re.sub(r'\s+', ' ', clean).strip()
    # ⚠️ 不在后端截断长度，由前端formatLastMessage统一处理
    return clean


@service_bp.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    """工作台数据"""
    business_id = current_user.business_id
    
    # 使用新的队列服务获取统计
    result = QueueService.get_queue_statistics(business_id)
    
    return jsonify(result)


# ========== 队列管理API ==========

@service_bp.route('/queue/waiting', methods=['GET'])
@login_required
def get_waiting_queue():
    """获取等待队列列表"""
    try:
        business_id = current_user.business_id
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        result = QueueService.get_waiting_list(business_id, page, per_page)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f'获取等待队列失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@service_bp.route('/queue/my-sessions', methods=['GET'])
@login_required
def get_my_sessions():
    """获取我的会话列表"""
    try:
        service_id = current_user.service_id
        result = QueueService.get_service_sessions(service_id)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f'获取会话列表失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@service_bp.route('/visitors/list', methods=['GET'])
@login_required
def get_visitors_list():
    """
    获取访客列表（分页）
    - 普通客服：只能看到自己对接过的访客
    - 管理员：可以看到所有访客
    """
    try:
        service_id = current_user.service_id
        business_id = current_user.business_id
        level = current_user.level
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # ⚡ 性能优化（2025-10-26）：在SQL层面完成所有排序，避免Python端二次排序
        # 使用LEFT JOIN关联Queue表，一次查询完成排序
        # 排序优先级：活跃会话 > 在线访客 > 最后活动时间
        
        if level in ['super_manager', 'manager']:
            # 管理员可以看到所有访客
            visitors_query = Visitor.query.outerjoin(
                Queue,
                and_(
                    Queue.visitor_id == Visitor.visitor_id,
                    Queue.business_id == business_id,
                    Queue.state == 'normal'
                )
            ).filter(
                Visitor.business_id == business_id
            ).order_by(
                # 1️⃣ 活跃会话优先（Queue.state='normal'的排前面）
                case([(Queue.state == 'normal', 0)], else_=1).asc(),
                # 2️⃣ 在线访客优先
                case([(Visitor.state == 'online', 0)], else_=1).asc(),
                # 3️⃣ 最后活动时间倒序（优先使用Queue.updated_at，无则用Visitor.last_visit_time）
                func.coalesce(Queue.updated_at, Visitor.last_visit_time).desc()
            ).paginate(page=page, per_page=per_page, error_out=False)
        else:
            # 普通客服只能看到与自己有队列记录的访客
            # 先查询该客服的所有队列访客ID
            queue_visitor_ids = db.session.query(Queue.visitor_id).filter_by(
                business_id=business_id,
                service_id=service_id
            ).distinct().all()
            visitor_ids = [v[0] for v in queue_visitor_ids]
            
            visitors_query = Visitor.query.outerjoin(
                Queue,
                and_(
                    Queue.visitor_id == Visitor.visitor_id,
                    Queue.business_id == business_id,
                    Queue.service_id == service_id,
                    Queue.state == 'normal'
                )
            ).filter(
                Visitor.business_id == business_id,
                Visitor.visitor_id.in_(visitor_ids)
            ).order_by(
                # 1️⃣ 活跃会话优先
                case([(Queue.state == 'normal', 0)], else_=1).asc(),
                # 2️⃣ 在线访客优先
                case([(Visitor.state == 'online', 0)], else_=1).asc(),
                # 3️⃣ 最后活动时间倒序
                func.coalesce(Queue.updated_at, Visitor.last_visit_time).desc()
            ).paginate(page=page, per_page=per_page, error_out=False)
        
        # ⚡ 性能优化：批量查询，避免N+1问题
        visitors_list = []
        visitor_ids = [v.visitor_id for v in visitors_query.items]
        logger.info(f"📋 查询到 {len(visitor_ids)} 个访客，总计 {visitors_query.total} 个")
        
        if not visitor_ids:
            # 没有访客，直接返回
            return jsonify({
                'code': 0,
                'msg': '获取成功',
                'data': {
                    'visitors': [],
                    'total': 0,
                    'page': page,
                    'per_page': per_page,
                    'pages': 0
                }
            })
        
        # ⚡ 批量查询1：获取所有访客的最新队列记录
        # ⚠️ func已在文件开头导入，无需重复导入
        subquery = db.session.query(
            Queue.visitor_id,
            func.max(Queue.updated_at).label('max_updated_at')
        ).filter(
            Queue.visitor_id.in_(visitor_ids),
            Queue.business_id == business_id
        ).group_by(Queue.visitor_id).subquery()
        
        queues_query = db.session.query(Queue).join(
            subquery,
            and_(
                Queue.visitor_id == subquery.c.visitor_id,
                Queue.updated_at == subquery.c.max_updated_at
            )
        ).all()
        queues_dict = {q.visitor_id: q for q in queues_query}
        
        # ⚡ 批量查询2：获取所有访客的最后一条消息
        last_chats_subquery = db.session.query(
            Chat.visitor_id,
            func.max(Chat.created_at).label('max_created_at')
        ).filter(
            Chat.visitor_id.in_(visitor_ids)
        ).group_by(Chat.visitor_id).subquery()
        
        last_chats_query = db.session.query(Chat).join(
            last_chats_subquery,
            and_(
                Chat.visitor_id == last_chats_subquery.c.visitor_id,
                Chat.created_at == last_chats_subquery.c.max_created_at
            )
        ).all()
        last_chats_dict = {c.visitor_id: c for c in last_chats_query}
        
        # ⚡ 批量查询3：统计所有访客的未读消息数
        # ⚡ 修复：只统计活跃会话(Queue.state='normal')的未读消息，与全局未读数保持一致
        # 先查询所有活跃会话的访客ID
        active_visitor_ids = db.session.query(Queue.visitor_id).filter(
            Queue.visitor_id.in_(visitor_ids),
            Queue.business_id == business_id,
            Queue.state == 'normal'
        )
        
        # 如果是普通客服，只查询分配给自己的活跃会话
        if level not in ['super_manager', 'manager']:
            active_visitor_ids = active_visitor_ids.filter(Queue.service_id == service_id)
        
        active_visitor_id_list = [v[0] for v in active_visitor_ids.all()]
        
        # 统计这些活跃会话访客的未读消息
        if active_visitor_id_list:
            unread_filter_conditions = [
                Chat.visitor_id.in_(active_visitor_id_list),
                Chat.direction == 'to_service',
                Chat.state == 'unread'
            ]
            
            # 如果是普通客服，只统计发给自己的未读消息
            if level not in ['super_manager', 'manager']:
                unread_filter_conditions.append(Chat.service_id == service_id)
            
            unread_counts_query = db.session.query(
                Chat.visitor_id,
                func.count(Chat.cid).label('unread_count')
            ).filter(
                *unread_filter_conditions
            ).group_by(Chat.visitor_id).all()
            unread_counts_dict = {row.visitor_id: row.unread_count for row in unread_counts_query}
        else:
            unread_counts_dict = {}
        
        # ⚡ 现在构建访客列表，使用预查询的数据
        for visitor in visitors_query.items:
            logger.info(f"  - Visitor: {visitor.visitor_name} ({visitor.visitor_id}), state={visitor.state}")
            
            # 从预查询的字典中获取数据
            queue = queues_dict.get(visitor.visitor_id)
            last_chat = last_chats_dict.get(visitor.visitor_id)
            unread_count = unread_counts_dict.get(visitor.visitor_id, 0)
            
            # 组合地理位置信息
            location_parts = []
            if visitor.country:
                location_parts.append(visitor.country)
            if visitor.province:
                location_parts.append(visitor.province)
            if visitor.city:
                location_parts.append(visitor.city)
            location = ' '.join(location_parts) if location_parts else '未知'
            
            is_active = queue.state == 'normal' if queue else False
            
            # ✅ 处理最后一条消息：如果是机器人发送，添加🤖图标
            last_message_text = ''
            if last_chat:
                last_message_text = strip_html_tags(last_chat.content)
                # 如果是机器人消息（service_id为NULL或0且方向是to_visitor），添加emoji图标
                if last_chat.direction == 'to_visitor' and (last_chat.service_id is None or last_chat.service_id == 0):
                    last_message_text = '🤖 ' + last_message_text
            
            visitors_list.append({
                'visitor_id': visitor.visitor_id,
                'visitor_name': visitor.visitor_name,
                'ip': visitor.ip or '',
                'location': location,
                'country': visitor.country or '',
                'province': visitor.province or '',
                'city': visitor.city or '',
                'browser': visitor.browser or '',
                'os': visitor.os or '',
                'device': visitor.device or '',
                'service_id': queue.service_id if queue else 0,  # ⚡ 没有队列时默认0
                'queue_id': queue.qid if queue else None,  # ⚡ 没有队列时为None
                'queue_state': queue.state if queue else 'closed',  # ⚡ 没有队列时默认closed
                'is_active': is_active,  # ⚡ 没有队列时不活跃
                'last_message': last_message_text,  # ⚡ 智能处理：JSON保留完整，文本过滤HTML，机器人消息加🤖
                'last_message_time': last_chat.created_at.isoformat() if last_chat else visitor.last_visit_time.isoformat(),
                'unread_count': unread_count,  # ⚡ 真实的未读消息计数
                'updated_at': queue.updated_at.isoformat() if queue else visitor.updated_at.isoformat()
            })
        
        # ⚡ 性能优化（2025-10-26）：移除Python端排序
        # 原因：SQL查询已经按 活跃会话 > 在线状态 > 最后活动时间 排序
        # 移除重复排序可提升性能50%+（特别是访客数量>100时）
        
        logger.info(f"📦 最终构建的访客列表: {len(visitors_list)} 个访客（已按活跃度排序）")
        logger.info(f"📦 访客列表详情: {visitors_list}")
        
        return jsonify({
            'code': 0,
            'msg': '获取成功',
            'data': {
                'visitors': visitors_list,
                'total': visitors_query.total,  # ⚡ 修改为访客总数
                'page': page,
                'per_page': per_page,
                'pages': visitors_query.pages  # ⚡ 修改为访客分页数
            }
        })
        
    except Exception as e:
        logger.error(f'获取访客列表失败: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'code': -1, 'msg': str(e)}), 500


@service_bp.route('/queue/assign', methods=['POST'])
@login_required
def manual_assign():
    """手动分配客服"""
    try:
        data = request.get_json()
        queue_id = data.get('queue_id')
        service_id = data.get('service_id')
        
        if not queue_id or not service_id:
            return jsonify({'code': -1, 'msg': '参数不完整'}), 400
        
        # 检查权限（只有管理员可以分配）
        if current_user.level not in ['super_manager', 'manager']:
            return jsonify({'code': -1, 'msg': '权限不足'}), 403
        
        result = QueueService.manual_assign_service(queue_id, service_id)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f'手动分配失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@service_bp.route('/queue/claim/<int:queue_id>', methods=['POST'])
@login_required
def claim_session(queue_id):
    """客服主动领取会话"""
    try:
        service_id = current_user.service_id
        result = QueueService.manual_assign_service(queue_id, service_id)
        
        if result['code'] == 0:
            logger.info(f"客服 {current_user.user_name} 领取了会话 {queue_id}")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f'领取会话失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@service_bp.route('/queue/transfer', methods=['POST'])
@login_required
def transfer_session():
    """转接会话（带权限验证）"""
    try:
        data = request.get_json()
        queue_id = data.get('queue_id')
        to_service_id = data.get('to_service_id')
        
        if not queue_id or not to_service_id:
            return jsonify({'code': -1, 'msg': '参数不完整'}), 400
        
        # ✅ 权限验证：普通客服只能转接给同级别客服
        if current_user.level == 'service':
            target_service = Service.query.get(to_service_id)
            if not target_service:
                return jsonify({'code': -1, 'msg': '目标客服不存在'}), 400
            
            if target_service.level != 'service':
                return jsonify({'code': -1, 'msg': '权限不足，普通客服只能转接给其他普通客服'}), 403
        
        # 管理员可以转接给任何人，无需额外验证
        
        result = QueueService.transfer_session(queue_id, to_service_id)
        
        if result['code'] == 0:
            logger.info(f"✅ 客服 {current_user.nick_name} 将会话 {queue_id} 转接到客服 {to_service_id}")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f'转接会话失败: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'code': -1, 'msg': str(e)}), 500


@service_bp.route('/queue/transfer-to-me', methods=['POST'])
@login_required
def transfer_to_me():
    """管理员转接访客到自己（一键接管）"""
    try:
        # 检查权限：仅管理员可用
        if current_user.level not in ['super_manager', 'manager']:
            return jsonify({'code': -1, 'msg': '权限不足，仅管理员可用'}), 403
        
        data = request.get_json()
        visitor_id = data.get('visitor_id')
        
        if not visitor_id:
            return jsonify({'code': -1, 'msg': '访客ID不能为空'}), 400
        
        # 查找该访客的队列
        queue = Queue.query.filter_by(
            visitor_id=visitor_id,
            business_id=current_user.business_id,
            state='normal'
        ).first()
        
        if not queue:
            return jsonify({'code': -1, 'msg': '未找到该访客的会话'}), 404
        
        old_service_id = queue.service_id
        new_service_id = current_user.service_id
        
        # 如果已经是当前管理员接待，无需转接
        if old_service_id == new_service_id:
            return jsonify({'code': 0, 'msg': '该访客已由您接待'})
        
        # 更新队列分配
        queue.service_id = new_service_id
        from datetime import datetime
        queue.updated_at = datetime.now()
        db.session.commit()
        
        # ✅ 使用统一的接待数管理器进行转移
        from mod.mysql.ModuleClass.ServiceWorkloadManager import workload_manager
        workload_manager.transfer_workload(
            old_service_id,
            new_service_id,
            f"管理员转接到自己: {visitor_id}"
        )
        
        logger.info(f"✅ 管理员 {current_user.nick_name} 转接访客 {visitor_id}: {old_service_id} -> {new_service_id}")
        
        # 🔔 广播转接事件（通过Socket.IO）
        from socketio_events import socketio
        
        # 获取访客信息
        visitor = Visitor.query.filter_by(visitor_id=visitor_id).first()
        
        # 广播给所有在线客服（使用 visitor_assignment_updated 事件）
        socketio.emit('visitor_assignment_updated', {
            'visitor_id': visitor_id,
            'visitor_name': visitor.visitor_name if visitor else visitor_id,
            'old_service_id': old_service_id,
            'new_service_id': new_service_id,
            'new_service_name': current_user.nick_name,
            'assigned_to_me': False,  # 会根据接收者的service_id判断
            'can_reply': False,
            'can_view': True,
            'reason': 'transferred',
            'message': f'访客已转接到 {current_user.nick_name}'
        }, room='service_room', namespace='/')
        
        return jsonify({
            'code': 0,
            'msg': '转接成功',
            'data': {
                'visitor_id': visitor_id,
                'old_service_id': old_service_id,
                'new_service_id': new_service_id
            }
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'转接访客到自己失败: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'code': -1, 'msg': str(e)}), 500


@service_bp.route('/queue/end/<int:queue_id>', methods=['POST'])
@login_required
def end_session(queue_id):
    """结束会话"""
    try:
        result = QueueService.end_session(queue_id)
        
        if result['code'] == 0:
            logger.info(f"客服 {current_user.user_name} 结束了会话 {queue_id}")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f'结束会话失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@service_bp.route('/queue/statistics', methods=['GET'])
@login_required
def get_queue_statistics():
    """获取队列统计数据"""
    try:
        business_id = current_user.business_id
        result = QueueService.get_queue_statistics(business_id)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f'获取统计数据失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


# ========== 客服管理API ==========

@service_bp.route('/list', methods=['GET'])
@login_required
def get_service_list():
    """获取客服列表（带权限过滤）"""
    try:
        business_id = current_user.business_id
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        state = request.args.get('state', '')  # online, offline, busy
        
        # ✅ 权限过滤逻辑
        level_filter = None
        if current_user.level == 'service':
            # 普通客服只能看到其他普通客服
            level_filter = 'service'
        elif current_user.level in ['manager', 'super_manager']:
            # 管理员可以看到所有客服
            level_filter = None
        
        # 构建查询
        query = Service.query.filter_by(business_id=business_id)
        
        # 状态过滤
        if state:
            query = query.filter_by(state=state)
        
        # 权限过滤
        if level_filter:
            query = query.filter_by(level=level_filter)
        
        # 分页
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        services_list = []
        for service in pagination.items:
            services_list.append({
                'service_id': service.service_id,
                'nick_name': service.nick_name,
                'email': service.email,
                'level': service.level,
                'state': service.state,
                'current_chat_count': service.current_chat_count or 0,
                'max_concurrent_chats': service.max_concurrent_chats or 5,
                'auto_accept': service.auto_accept
            })
        
        return jsonify({
            'code': 0,
            'msg': '获取成功',
            'data': services_list,
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        })
        
    except Exception as e:
        logger.error(f'获取客服列表失败: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'code': -1, 'msg': str(e)}), 500


@service_bp.route('/update-state', methods=['POST'])
@login_required
def update_service_state():
    """更新客服在线状态"""
    try:
        data = request.get_json()
        state = data.get('state')  # online, offline, busy
        
        from mod.mysql.ModuleClass import service_management
        result = service_management.update_service_state(current_user.service_id, state)
        
        if result['code'] == 0:
            logger.info(f"客服 {current_user.user_name} 状态更新为 {state}")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f'更新状态失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


# ========== 客服分组管理API ==========

@service_bp.route('/groups', methods=['GET'])
@login_required
def get_service_groups():
    """获取客服分组列表"""
    try:
        if current_user.level not in ['super_manager', 'manager']:
            return jsonify({'code': -1, 'msg': '权限不足'}), 403
        
        business_id = current_user.business_id
        
        from mod.mysql.models import ServiceGroup
        groups = ServiceGroup.query.filter_by(
            business_id=business_id,
            status=1
        ).order_by(ServiceGroup.add_time.desc()).all()
        
        # 统计每个分组的成员数
        result_data = []
        for group in groups:
            group_dict = group.to_dict()
            member_count = Service.query.filter_by(
                business_id=business_id,
                group_id=group.id
            ).count()
            group_dict['member_count'] = member_count
            result_data.append(group_dict)
        
        return jsonify({
            'code': 0,
            'msg': '获取成功',
            'data': result_data
        })
        
    except Exception as e:
        logger.error(f'获取分组列表失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@service_bp.route('/groups', methods=['POST'])
@login_required
def create_service_group():
    """创建客服分组"""
    try:
        if current_user.level not in ['super_manager', 'manager']:
            return jsonify({'code': -1, 'msg': '权限不足'}), 403
        
        data = request.get_json()
        group_name = data.get('group_name')
        
        if not group_name:
            return jsonify({'code': -1, 'msg': '分组名称不能为空'}), 400
        
        business_id = current_user.business_id
        bgcolor = data.get('bgcolor', '#667eea')
        description = data.get('description', '')
        
        from mod.mysql.models import ServiceGroup
        from datetime import datetime
        
        group = ServiceGroup(
            business_id=business_id,
            group_name=group_name,
            bgcolor=bgcolor,
            description=description,
            add_time=datetime.utcnow(),
            status=1
        )
        
        db.session.add(group)
        db.session.commit()
        
        logger.info(f"创建客服分组: {group_name}")
        
        return jsonify({
            'code': 0,
            'msg': '创建成功',
            'data': group.to_dict()
        })
        
    except Exception as e:
        logger.error(f'创建分组失败: {e}')
        db.session.rollback()
        return jsonify({'code': -1, 'msg': str(e)}), 500


@service_bp.route('/groups/<int:group_id>', methods=['PUT'])
@login_required
def update_service_group(group_id):
    """更新客服分组"""
    try:
        if current_user.level not in ['super_manager', 'manager']:
            return jsonify({'code': -1, 'msg': '权限不足'}), 403
        
        from mod.mysql.models import ServiceGroup
        
        group = ServiceGroup.query.filter_by(
            id=group_id,
            business_id=current_user.business_id
        ).first()
        
        if not group:
            return jsonify({'code': -1, 'msg': '分组不存在'}), 404
        
        data = request.get_json()
        
        if 'group_name' in data:
            group.group_name = data['group_name']
        if 'bgcolor' in data:
            group.bgcolor = data['bgcolor']
        if 'description' in data:
            group.description = data['description']
        
        db.session.commit()
        
        logger.info(f"更新客服分组: {group_id}")
        
        return jsonify({
            'code': 0,
            'msg': '更新成功',
            'data': group.to_dict()
        })
        
    except Exception as e:
        logger.error(f'更新分组失败: {e}')
        db.session.rollback()
        return jsonify({'code': -1, 'msg': str(e)}), 500


@service_bp.route('/groups/<int:group_id>', methods=['DELETE'])
@login_required
def delete_service_group(group_id):
    """删除客服分组"""
    try:
        if current_user.level not in ['super_manager', 'manager']:
            return jsonify({'code': -1, 'msg': '权限不足'}), 403
        
        from mod.mysql.models import ServiceGroup
        
        group = ServiceGroup.query.filter_by(
            id=group_id,
            business_id=current_user.business_id
        ).first()
        
        if not group:
            return jsonify({'code': -1, 'msg': '分组不存在'}), 404
        
        # 将该分组的客服移到未分组（group_id=0）
        Service.query.filter_by(
            business_id=current_user.business_id,
            group_id=group_id
        ).update({'group_id': 0})
        
        # 删除分组（软删除）
        group.status = 0
        db.session.commit()
        
        logger.info(f"删除客服分组: {group_id}")
        
        return jsonify({
            'code': 0,
            'msg': '删除成功'
        })
        
    except Exception as e:
        logger.error(f'删除分组失败: {e}')
        db.session.rollback()
        return jsonify({'code': -1, 'msg': str(e)}), 500


# ========== 聊天记录API ==========

@service_bp.route('/chat/history', methods=['GET'])
@login_required
def get_chat_history():
    """获取与访客的聊天历史"""
    try:
        visitor_id = request.args.get('visitor_id')
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        if not visitor_id:
            return jsonify({'code': -1, 'msg': '缺少访客ID参数'}), 400
        
        # ✅ 先倒序获取最新的limit条记录，然后反转成正序
        # 倒序查询最新的记录
        messages = Chat.query.filter_by(
            visitor_id=visitor_id,
            business_id=current_user.business_id
        ).order_by(Chat.created_at.desc()).offset(offset).limit(limit).all()
        
        # ✅ 反转成正序（最早的在前，最新的在后）
        messages.reverse()
        
        # ⚡ 批量更新未读消息为已读（性能优化：使用update()而不是逐条更新）
        try:
            updated_count = Chat.query.filter_by(
                visitor_id=visitor_id,
                business_id=current_user.business_id,
                direction='to_service',  # 访客发给客服的消息
                state='unread'
            ).update({'state': 'read'}, synchronize_session=False)
            
            if updated_count > 0:
                db.session.commit()
                logger.info(f"✅ 批量标记已读: 访客 {visitor_id} 的 {updated_count} 条消息")
        except Exception as e:
            logger.error(f"标记已读失败: {e}")
            db.session.rollback()
        
        # 获取总数
        total = Chat.query.filter_by(
            visitor_id=visitor_id,
            business_id=current_user.business_id
        ).count()
        
        # 转换为字典格式
        result = []
        for msg in messages:
            # 根据方向和service_id判断发送者类型
            if msg.direction == 'to_service':
                from_type = 'visitor'
            elif msg.service_id is None:
                from_type = 'robot'  # service_id=None 表示机器人
            else:
                from_type = 'service'
            
            result.append({
                'id': msg.cid,
                'visitor_id': msg.visitor_id,
                'service_id': msg.service_id,
                'content': msg.content,
                'msg_type': msg.msg_type,
                'direction': msg.direction,
                'from_type': from_type,  # ✅ 添加发送者类型
                'state': msg.state,
                'timestamp': msg.timestamp,
                'created_at': msg.created_at.isoformat() if msg.created_at else None
            })
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': result,
            'total': total,
            'has_more': (offset + limit) < total
        })
        
    except Exception as e:
        logger.error(f'获取聊天历史失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@service_bp.route('/info/<int:service_id>', methods=['GET'])
@login_required
def get_service_info(service_id):
    """获取客服详细信息（包含工作负载）"""
    try:
        service = Service.query.get(service_id)
        
        if not service:
            return jsonify({
                'code': 404,
                'msg': '客服不存在'
            }), 404
        
        # 权限检查：只能查看自己的信息或管理员可以查看所有
        if current_user.level not in ['super_manager', 'manager'] and current_user.service_id != service_id:
            return jsonify({
                'code': 403,
                'msg': '无权限查看此客服信息'
            }), 403
        
        # 返回包含工作负载的详细信息
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': service.to_dict(include_workload=True)
        })
        
    except Exception as e:
        logger.error(f'获取客服信息失败: {e}')
        return jsonify({
            'code': 500,
            'msg': f'服务器错误: {str(e)}'
        }), 500


@service_bp.route('/mark_visitor_read', methods=['POST'])
@login_required
def mark_visitor_read():
    """
    标记指定访客的所有未读消息为已读（客服打开会话时调用）
    """
    try:
        data = request.get_json()
        visitor_id = data.get('visitor_id')
        
        if not visitor_id:
            return jsonify({
                'code': 400,
                'msg': '缺少访客ID'
            }), 400
        
        # ⚡ 批量标记该访客发给客服的所有未读消息为已读
        updated_count = Chat.query.filter_by(
            visitor_id=visitor_id,
            business_id=current_user.business_id,
            direction='to_service',  # 访客发给客服的消息
            state='unread'
        ).update({'state': 'read'}, synchronize_session=False)
        
        if updated_count > 0:
            db.session.commit()
            logger.info(f"✅ 客服{current_user.service_id}打开会话，标记已读: 访客 {visitor_id} 的 {updated_count} 条消息")
        
        return jsonify({
            'code': 0,
            'msg': '标记成功',
            'data': {
                'updated_count': updated_count
            }
        })
        
    except Exception as e:
        logger.error(f"标记已读失败: {e}")
        db.session.rollback()
        return jsonify({
            'code': 500,
            'msg': f'标记失败: {str(e)}'
        }), 500


@service_bp.route('/unread_messages', methods=['GET'])
@login_required
def get_unread_messages():
    """
    获取客服的未读消息数（用于导航栏提示）
    返回：所有分配给该客服的访客中，未读的消息总数
    """
    try:
        service_id = current_user.service_id
        level = current_user.level
        
        # 管理员可以看到所有未读消息，普通客服只看自己的
        business_id = current_user.business_id
        
        if level in ['super_manager', 'manager']:
            # ✅ 管理员：查询所有未读消息（只统计当前在会话中的访客）
            active_visitor_ids = db.session.query(Queue.visitor_id).filter(
                Queue.business_id == business_id,
                Queue.state == 'normal'
            ).all()
            active_visitor_id_list = [v[0] for v in active_visitor_ids]
            
            if active_visitor_id_list:
                unread_count = db.session.query(func.count(Chat.cid)).filter(
                    and_(
                        Chat.business_id == business_id,
                        Chat.state == 'unread',  # ✅ 未读状态
                        Chat.direction == 'to_service',  # 访客发送给客服的
                        Chat.visitor_id.in_(active_visitor_id_list)  # ✅ 只统计在会话中的访客
                    )
                ).scalar() or 0
            else:
                unread_count = 0
        else:
            # ⚡ 修复：普通客服只统计发给自己的未读消息（添加service_id筛选）
            unread_count = db.session.query(func.count(Chat.cid)).join(
                Queue,
                and_(
                    Queue.visitor_id == Chat.visitor_id,
                    Queue.service_id == service_id,
                    Queue.state == 'normal'
                )
            ).filter(
                and_(
                    Chat.business_id == business_id,
                    Chat.service_id == service_id,  # ⚡ 修复：只统计发给当前客服的消息
                    Chat.state == 'unread',
                    Chat.direction == 'to_service'  # ⚡ 修复：使用direction而不是msg_type
                )
            ).scalar() or 0
        
        return jsonify({
            'code': 0,
            'msg': '成功',
            'data': {
                'unread_count': unread_count,
                'timestamp': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f'获取未读消息数失败: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'code': -1, 'msg': str(e)}), 500