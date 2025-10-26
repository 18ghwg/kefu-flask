"""
操作日志API蓝图
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from mod.mysql.ModuleClass import operation_log_service
import log

operation_log_bp = Blueprint('operation_log', __name__, url_prefix='/api/operation-log')
logger = log.get_logger(__name__)


@operation_log_bp.route('/list', methods=['GET'])
@login_required
def get_operation_logs():
    """获取操作日志列表"""
    try:
        # 权限检查
        if current_user.level not in ['super_manager', 'manager']:
            return jsonify({'code': -1, 'msg': '权限不足'}), 403
        
        business_id = current_user.business_id
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # 过滤参数
        filters = {}
        if request.args.get('operator_type'):
            filters['operator_type'] = request.args.get('operator_type')
        if request.args.get('module'):
            filters['module'] = request.args.get('module')
        if request.args.get('action'):
            filters['action'] = request.args.get('action')
        if request.args.get('result'):
            filters['result'] = request.args.get('result')
        if request.args.get('keyword'):
            filters['keyword'] = request.args.get('keyword')
        if request.args.get('start_date'):
            filters['start_date'] = request.args.get('start_date')
        if request.args.get('end_date'):
            filters['end_date'] = request.args.get('end_date')
        
        result = operation_log_service.get_logs(business_id, page, per_page, filters)
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': result
        })
        
    except Exception as e:
        logger.error(f'获取操作日志列表失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@operation_log_bp.route('/get/<int:log_id>', methods=['GET'])
@login_required
def get_operation_log_detail(log_id):
    """获取操作日志详情"""
    try:
        # 权限检查
        if current_user.level not in ['super_manager', 'manager']:
            return jsonify({'code': -1, 'msg': '权限不足'}), 403
        
        log_detail = operation_log_service.get_log(log_id)
        
        if not log_detail:
            return jsonify({'code': -1, 'msg': '日志不存在'}), 404
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': log_detail
        })
        
    except Exception as e:
        logger.error(f'获取操作日志详情失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@operation_log_bp.route('/delete/<int:log_id>', methods=['DELETE'])
@login_required
def delete_single_operation_log(log_id):
    """删除单条操作日志"""
    try:
        # 权限检查
        if current_user.level not in ['super_manager']:
            return jsonify({'code': -1, 'msg': '权限不足，只有超级管理员可以删除日志'}), 403
        
        business_id = current_user.business_id
        success = operation_log_service.delete_logs(business_id, [log_id])
        
        if success:
            return jsonify({'code': 0, 'msg': '删除成功'})
        else:
            return jsonify({'code': -1, 'msg': '删除失败'}), 500
        
    except Exception as e:
        logger.error(f'删除操作日志失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@operation_log_bp.route('/delete', methods=['POST'])
@login_required
def delete_operation_logs():
    """批量删除操作日志"""
    try:
        # 权限检查
        if current_user.level not in ['super_manager']:
            return jsonify({'code': -1, 'msg': '权限不足，只有超级管理员可以删除日志'}), 403
        
        data = request.get_json()
        log_ids = data.get('log_ids', [])
        
        if not log_ids:
            return jsonify({'code': -1, 'msg': '请选择要删除的日志'}), 400
        
        business_id = current_user.business_id
        success = operation_log_service.delete_logs(business_id, log_ids)
        
        if success:
            return jsonify({'code': 0, 'msg': '删除成功'})
        else:
            return jsonify({'code': -1, 'msg': '删除失败'}), 500
        
    except Exception as e:
        logger.error(f'删除操作日志失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@operation_log_bp.route('/clear', methods=['POST'])
@login_required
def clear_old_logs():
    """清理旧日志"""
    try:
        # 权限检查
        if current_user.level not in ['super_manager']:
            return jsonify({'code': -1, 'msg': '权限不足'}), 403
        
        data = request.get_json()
        days = data.get('days', 90)
        
        business_id = current_user.business_id
        count = operation_log_service.clear_old_logs(business_id, days)
        
        return jsonify({
            'code': 0,
            'msg': f'成功清理{count}条日志',
            'data': {'count': count}
        })
        
    except Exception as e:
        logger.error(f'清理旧日志失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@operation_log_bp.route('/statistics', methods=['GET'])
@login_required
def get_log_statistics():
    """获取日志统计"""
    try:
        # 权限检查
        if current_user.level not in ['super_manager', 'manager']:
            return jsonify({'code': -1, 'msg': '权限不足'}), 403
        
        business_id = current_user.business_id
        days = request.args.get('days', 7, type=int)
        
        stats = operation_log_service.get_statistics(business_id, days)
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': stats
        })
        
    except Exception as e:
        logger.error(f'获取日志统计失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500

