"""
队列管理API
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from mod.mysql.ModuleClass.QueueServiceClass import QueueService
import log

queue_bp = Blueprint('queue_api', __name__, url_prefix='/api/queue')

logger = log.get_logger(__name__)


# ========== 队列统计API ==========

@queue_bp.route('/statistics', methods=['GET'])
@login_required
def get_queue_statistics():
    """获取队列统计信息"""
    try:
        if current_user.level not in ['super_manager', 'manager']:
            return jsonify({'code': -1, 'msg': '权限不足'}), 403

        business_id = getattr(current_user, 'business_id', 1)
        stats = QueueService.get_queue_statistics_for_service(business_id)
        
        return jsonify({
            'code': 0,
            'msg': '获取成功',
            'data': stats
        })
    
    except Exception as e:
        logger.error(f'获取队列统计失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@queue_bp.route('/list', methods=['GET'])
@login_required
def get_queue_list():
    """
    获取队列列表（支持status参数过滤）
    参数:
        status: 队列状态 (waiting=等待中, chatting=会话中, complete=已完成, all=全部)
        limit: 数量限制
    """
    try:
        business_id = getattr(current_user, 'business_id', 1)
        status = request.args.get('status', 'waiting')
        limit = request.args.get('limit', 50, type=int)
        
        # 根据status参数获取对应的队列
        if status == 'waiting':
            # 获取等待中的队列（未分配客服的）
            queue_list = QueueService.get_waiting_list_simple(business_id, limit)
        else:
            # 其他状态暂时返回空列表，可根据需求扩展
            queue_list = []
        
        return jsonify({
            'code': 0,
            'msg': '获取成功',
            'data': queue_list
        })
    
    except Exception as e:
        logger.error(f'获取队列列表失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@queue_bp.route('/waiting-list', methods=['GET'])
@login_required
def get_waiting_list():
    """获取等待队列列表"""
    try:
        business_id = getattr(current_user, 'business_id', 1)
        limit = request.args.get('limit', 50, type=int)
        
        waiting_list = QueueService.get_waiting_list_simple(business_id, limit)
        
        return jsonify({
            'code': 0,
            'msg': '获取成功',
            'data': waiting_list
        })
    
    except Exception as e:
        logger.error(f'获取等待队列失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


# ========== 客服会话管理API ==========

@queue_bp.route('/my-sessions-count', methods=['GET'])
@login_required
def get_my_sessions_count():
    """获取当前客服的活跃会话数（用于实时统计）"""
    try:
        service_id = current_user.service_id
        if not service_id:
            return jsonify({'code': -1, 'msg': '客服ID不存在'}), 400
        
        # 获取活跃会话数（5分钟内有消息的会话）
        count = QueueService.get_service_active_sessions_count(service_id)
        
        return jsonify({
            'code': 0,
            'msg': '获取成功',
            'data': {
                'count': count
            }
        })
    
    except Exception as e:
        logger.error(f'获取活跃会话数失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@queue_bp.route('/my-statistics', methods=['GET'])
@login_required
def get_my_statistics():
    """获取当前客服的完整统计信息（工作台显示）"""
    try:
        service_id = current_user.service_id
        business_id = getattr(current_user, 'business_id', 1)
        
        if not service_id:
            return jsonify({'code': -1, 'msg': '客服ID不存在'}), 400
        
        # 获取统计信息
        stats = QueueService.get_service_statistics(service_id, business_id)
        
        return jsonify({
            'code': 0,
            'msg': '获取成功',
            'data': stats
        })
    
    except Exception as e:
        logger.error(f'获取客服统计信息失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@queue_bp.route('/service-sessions/<int:service_id>', methods=['GET'])
@login_required
def get_service_sessions(service_id):
    """获取客服的会话列表"""
    try:
        # 权限检查
        if current_user.level not in ['super_manager', 'manager']:
            if current_user.service_id != service_id:
                return jsonify({'code': -1, 'msg': '权限不足'}), 403
        
        state = request.args.get('state', 'normal')
        sessions = QueueService.get_service_sessions_by_state(service_id, state)
        
        return jsonify({
            'code': 0,
            'msg': '获取成功',
            'data': sessions
        })
    
    except Exception as e:
        logger.error(f'获取客服会话失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


# ========== 会话操作API ==========

@queue_bp.route('/claim', methods=['POST'])
@login_required
def claim_visitor():
    """客服认领访客"""
    try:
        data = request.get_json()
        visitor_id = data.get('visitor_id')
        
        if not visitor_id:
            return jsonify({'code': -1, 'msg': '缺少参数'}), 400
        
        service_id = current_user.service_id
        success = QueueService.claim_visitor(service_id, visitor_id)
        
        if success:
            logger.info(f"客服 {service_id} 认领了访客 {visitor_id}")
            return jsonify({
                'code': 0,
                'msg': '认领成功'
            })
        else:
            return jsonify({'code': -1, 'msg': '认领失败，访客可能已被其他客服认领'}), 400
    
    except Exception as e:
        logger.error(f'认领访客失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@queue_bp.route('/transfer', methods=['POST'])
@login_required
def transfer_session():
    """转接会话"""
    try:
        data = request.get_json()
        visitor_id = data.get('visitor_id')
        to_service_id = data.get('to_service_id')
        
        if not visitor_id or not to_service_id:
            return jsonify({'code': -1, 'msg': '缺少参数'}), 400
        
        from_service_id = current_user.service_id
        success = QueueService.transfer_service(visitor_id, from_service_id, to_service_id)
        
        if success:
            logger.info(f"会话转接: 访客 {visitor_id} 从客服 {from_service_id} 转接到 {to_service_id}")
            return jsonify({
                'code': 0,
                'msg': '转接成功'
            })
        else:
            return jsonify({'code': -1, 'msg': '转接失败'}), 400
    
    except Exception as e:
        logger.error(f'转接会话失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@queue_bp.route('/close', methods=['POST'])
@login_required
def close_session():
    """关闭会话"""
    try:
        data = request.get_json()
        visitor_id = data.get('visitor_id')
        
        if not visitor_id:
            return jsonify({'code': -1, 'msg': '缺少参数'}), 400
        
        service_id = current_user.service_id
        success = QueueService.close_session(visitor_id, service_id)
        
        if success:
            logger.info(f"客服 {service_id} 关闭了与访客 {visitor_id} 的会话")
            return jsonify({
                'code': 0,
                'msg': '会话已关闭'
            })
        else:
            return jsonify({'code': -1, 'msg': '未找到会话或会话已结束'}), 400
    
    except Exception as e:
        logger.error(f'关闭会话失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@queue_bp.route('/blacklist/add', methods=['POST'])
@login_required
def add_to_blacklist():
    """添加访客到黑名单"""
    try:
        data = request.get_json()
        visitor_id = data.get('visitor_id')
        reason = data.get('reason', '')
        
        if not visitor_id:
            return jsonify({'code': -1, 'msg': '缺少参数'}), 400
        
        service_id = current_user.service_id
        success = QueueService.add_to_blacklist(visitor_id, service_id, reason)
        
        if success:
            logger.info(f"客服 {service_id} 将访客 {visitor_id} 添加到黑名单，原因: {reason}")
            return jsonify({
                'code': 0,
                'msg': '已添加到黑名单'
            })
        else:
            return jsonify({'code': -1, 'msg': '添加失败'}), 400
    
    except Exception as e:
        logger.error(f'添加黑名单失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@queue_bp.route('/blacklist/remove', methods=['POST'])
@login_required
def remove_from_blacklist():
    """从黑名单移除访客"""
    try:
        data = request.get_json()
        visitor_id = data.get('visitor_id')
        
        if not visitor_id:
            return jsonify({'code': -1, 'msg': '缺少参数'}), 400
        
        service_id = current_user.service_id
        success = QueueService.remove_from_blacklist(visitor_id)
        
        if success:
            logger.info(f"客服 {service_id} 将访客 {visitor_id} 从黑名单移除")
            return jsonify({
                'code': 0,
                'msg': '已从黑名单移除'
            })
        else:
            return jsonify({'code': -1, 'msg': '该访客不在黑名单中'}), 400
    
    except Exception as e:
        logger.error(f'移除黑名单失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@queue_bp.route('/blacklist/check/<visitor_id>', methods=['GET'])
@login_required
def check_blacklist_status(visitor_id):
    """查询访客黑名单状态"""
    try:
        blacklist_status = QueueService.check_blacklist_status(visitor_id)
        
        return jsonify({
            'code': 0,
            'msg': '查询成功',
            'data': blacklist_status
        })
    
    except Exception as e:
        logger.error(f'查询黑名单状态失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@queue_bp.route('/blacklist/list', methods=['GET'])
@login_required
def get_blacklist():
    """获取黑名单列表"""
    try:
        business_id = getattr(current_user, 'business_id', 1)
        limit = request.args.get('limit', 50, type=int)
        
        blacklist = QueueService.get_blacklist(business_id, limit)
        
        return jsonify({
            'code': 0,
            'msg': '获取成功',
            'data': blacklist
        })
    
    except Exception as e:
        logger.error(f'获取黑名单列表失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


# ========== 访客排队查询API ==========

@queue_bp.route('/position/<visitor_id>', methods=['GET'])
def get_queue_position(visitor_id):
    """获取访客的排队位置（公开接口）"""
    try:
        business_id = request.args.get('business_id', type=int)
        if not business_id:
            return jsonify({'code': -1, 'msg': '缺少商户ID'}), 400
        
        position_data = QueueService.get_queue_position_public(visitor_id, business_id)
        
        return jsonify({
            'code': 0,
            'msg': '获取成功',
            'data': position_data
        })
    
    except Exception as e:
        logger.error(f'获取排队位置失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500

