"""
客服分配相关API
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from mod.mysql.models import Service
import log

logger = log.get_logger(__name__)

assignment_bp = Blueprint('assignment', __name__)

# 延迟导入，避免循环导入
def get_assignment_service():
    from mod.mysql.ModuleClass.AssignmentServiceClass import assignment_service
    return assignment_service


@assignment_bp.route('/request-service', methods=['POST'])
def request_service():
    """
    访客请求分配客服
    
    请求参数:
        visitor_id: 访客ID
        business_id: 商户ID
        exclusive_service_id: 专属客服ID（可选）
        priority: 优先级 0=普通 1=VIP 2=紧急
    """
    try:
        data = request.get_json()
        
        visitor_id = data.get('visitor_id')
        business_id = data.get('business_id', 1)
        exclusive_service_id = data.get('exclusive_service_id')
        priority = data.get('priority', 0)
        
        if not visitor_id:
            return jsonify({'code': 1000, 'msg': '访客ID不能为空'}), 400
        
        # 调用分配服务
        result = get_assignment_service().assign_visitor(
            visitor_id=visitor_id,
            business_id=business_id,
            exclusive_service_id=exclusive_service_id,
            priority=priority
        )
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': result
        })
        
    except Exception as e:
        logger.error(f"请求客服失败: {str(e)}")
        return jsonify({'code': 5000, 'msg': '系统错误'}), 500


@assignment_bp.route('/queue-status', methods=['GET'])
def queue_status():
    """
    查询排队状态
    
    参数:
        visitor_id: 访客ID
        business_id: 商户ID
    """
    try:
        visitor_id = request.args.get('visitor_id')
        business_id = request.args.get('business_id', 1, type=int)
        
        if not visitor_id:
            return jsonify({'code': 1000, 'msg': '访客ID不能为空'}), 400
        
        from mod.mysql.models import Queue
        queue = Queue.query.filter_by(
            visitor_id=visitor_id,
            business_id=business_id,
            state='normal'
        ).first()
        
        if not queue:
            return jsonify({
                'code': 0,
                'data': {
                    'in_queue': False,
                    'message': '未在队列中'
                }
            })
        
        # 已分配客服
        if queue.service_id > 0:
            service = Service.query.get(queue.service_id)
            return jsonify({
                'code': 0,
                'data': {
                    'in_queue': False,
                    'assigned': True,
                    'service': service.to_dict() if service else None,
                    'message': '已分配客服'
                }
            })
        
        # 排队中
        return jsonify({
            'code': 0,
            'data': {
                'in_queue': True,
                'position': queue.wait_position or 0,
                'estimated_wait_time': queue.estimated_wait_time or 0,
                'priority': queue.priority or 0,
                'message': f'您前面还有 {(queue.wait_position or 1) - 1} 位访客'
            }
        })
        
    except Exception as e:
        logger.error(f"查询排队状态失败: {str(e)}")
        return jsonify({'code': 5000, 'msg': '系统错误'}), 500


@assignment_bp.route('/check-reply-permission', methods=['POST'])
@login_required
def check_reply_permission():
    """
    检查客服是否可以回复访客
    
    请求参数:
        visitor_id: 访客ID
    """
    try:
        data = request.get_json()
        visitor_id = data.get('visitor_id')
        
        if not visitor_id:
            return jsonify({'code': 1000, 'msg': '访客ID不能为空'}), 400
        
        can_reply, reason, assigned_service = get_assignment_service().check_reply_permission(
            service_id=current_user.service_id,
            visitor_id=visitor_id,
            business_id=current_user.business_id
        )
        
        return jsonify({
            'code': 0,
            'data': {
                'can_reply': can_reply,
                'reason': reason,
                'assigned_service': assigned_service
            }
        })
        
    except Exception as e:
        logger.error(f"检查回复权限失败: {str(e)}")
        return jsonify({'code': 5000, 'msg': '系统错误'}), 500


@assignment_bp.route('/service-visitors', methods=['GET'])
@login_required
def get_service_visitors():
    """
    获取客服的访客列表
    
    参数:
        include_all: 是否包含所有访客（管理员）
    """
    try:
        include_all = request.args.get('include_all', 'false').lower() == 'true'
        
        visitors = get_assignment_service().get_service_visitors(
            service_id=current_user.service_id,
            include_all=include_all
        )
        
        return jsonify({
            'code': 0,
            'data': {
                'visitors': visitors,
                'count': len(visitors)
            }
        })
        
    except Exception as e:
        logger.error(f"获取访客列表失败: {str(e)}")
        return jsonify({'code': 5000, 'msg': '系统错误'}), 500


@assignment_bp.route('/process-queue', methods=['POST'])
@login_required
def process_queue():
    """
    处理排队队列（手动触发）
    需要管理员权限
    """
    try:
        if current_user.level not in ['super_manager', 'manager']:
            return jsonify({'code': 403, 'msg': '权限不足'}), 403
        
        assigned_count = get_assignment_service().process_queue(
            business_id=current_user.business_id
        )
        
        return jsonify({
            'code': 0,
            'msg': f'成功分配 {assigned_count} 个访客',
            'data': {
                'assigned_count': assigned_count
            }
        })
        
    except Exception as e:
        logger.error(f"处理队列失败: {str(e)}")
        return jsonify({'code': 5000, 'msg': '系统错误'}), 500


@assignment_bp.route('/update-queue-positions', methods=['POST'])
@login_required
def update_queue_positions():
    """
    更新排队位置（手动触发）
    需要管理员权限
    """
    try:
        if current_user.level not in ['super_manager', 'manager']:
            return jsonify({'code': 403, 'msg': '权限不足'}), 403
        
        get_assignment_service().update_queue_positions(
            business_id=current_user.business_id
        )
        
        return jsonify({
            'code': 0,
            'msg': '排队位置更新成功'
        })
        
    except Exception as e:
        logger.error(f"更新排队位置失败: {str(e)}")
        return jsonify({'code': 5000, 'msg': '系统错误'}), 500


@assignment_bp.route('/service-workload', methods=['GET'])
@login_required
def get_service_workload():
    """
    获取客服工作负载信息
    """
    try:
        service = Service.query.get(current_user.service_id)
        if not service:
            return jsonify({'code': 404, 'msg': '客服不存在'}), 404
        
        return jsonify({
            'code': 0,
            'data': service.to_dict(include_workload=True)
        })
        
    except Exception as e:
        logger.error(f"获取工作负载失败: {str(e)}")
        return jsonify({'code': 5000, 'msg': '系统错误'}), 500


@assignment_bp.route('/all-services-workload', methods=['GET'])
@login_required
def get_all_services_workload():
    """
    获取所有客服的工作负载（管理员）
    """
    try:
        if current_user.level not in ['super_manager', 'manager']:
            return jsonify({'code': 403, 'msg': '权限不足'}), 403
        
        services = Service.query.filter_by(
            business_id=current_user.business_id
        ).all()
        
        workloads = [s.to_dict(include_workload=True) for s in services]
        
        return jsonify({
            'code': 0,
            'data': {
                'services': workloads,
                'total_count': len(services),
                'online_count': len([s for s in services if s.state == 'online']),
                'available_count': len([s for s in services if s.is_available])
            }
        })
        
    except Exception as e:
        logger.error(f"获取所有客服负载失败: {str(e)}")
        return jsonify({'code': 5000, 'msg': '系统错误'}), 500

