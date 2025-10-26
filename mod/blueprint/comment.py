"""
评价系统API蓝图
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from mod.mysql.ModuleClass.CommentServiceClass import CommentService
import log

comment_bp = Blueprint('comment', __name__)
logger = log.get_logger(__name__)


@comment_bp.route('/submit', methods=['POST'])
def submit_comment():
    """
    提交评价（访客功能，无需登录）
    """
    try:
        data = request.get_json()
        
        # 验证必填参数
        required_fields = ['queue_id', 'visitor_id', 'service_id', 'level']
        if not all(field in data for field in required_fields):
            return jsonify({'code': -1, 'msg': '参数不完整'}), 400
        
        result = CommentService.submit_comment(
            queue_id=data['queue_id'],
            visitor_id=data['visitor_id'],
            service_id=data['service_id'],
            level=data['level'],
            content=data.get('content', '')
        )
        
        if result['code'] == 0:
            logger.info(f"访客 {data['visitor_id']} 提交了评价")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f'提交评价失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@comment_bp.route('/list', methods=['GET'])
@login_required
def get_comment_list():
    """
    获取评价列表（管理员功能）
    """
    try:
        if current_user.level not in ['super_manager', 'manager']:
            return jsonify({'code': -1, 'msg': '权限不足'}), 403
        
        business_id = current_user.business_id
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # 筛选条件
        service_id = request.args.get('service_id')
        level = request.args.get('level', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        result = CommentService.get_comment_list(
            business_id=business_id,
            service_id=service_id,
            level=level,
            start_date=start_date,
            end_date=end_date,
            page=page,
            per_page=per_page
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f'获取评价列表失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@comment_bp.route('/statistics', methods=['GET'])
@login_required
def get_comment_statistics():
    """
    获取评价统计（管理员功能）
    """
    try:
        if current_user.level not in ['super_manager', 'manager']:
            return jsonify({'code': -1, 'msg': '权限不足'}), 403
        
        business_id = current_user.business_id
        days = request.args.get('days', 7, type=int)
        service_id = request.args.get('service_id')
        
        result = CommentService.get_comment_statistics(
            business_id=business_id,
            service_id=service_id,
            days=days
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f'获取评价统计失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@comment_bp.route('/ranking', methods=['GET'])
@login_required
def get_service_ranking():
    """
    获取客服评价排行（管理员功能）
    """
    try:
        if current_user.level not in ['super_manager', 'manager']:
            return jsonify({'code': -1, 'msg': '权限不足'}), 403
        
        business_id = current_user.business_id
        days = request.args.get('days', 7, type=int)
        limit = request.args.get('limit', 10, type=int)
        
        result = CommentService.get_service_comment_ranking(
            business_id=business_id,
            days=days,
            limit=limit
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f'获取排行失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@comment_bp.route('/trend', methods=['GET'])
@login_required
def get_comment_trend():
    """
    获取评价趋势（管理员功能）
    """
    try:
        if current_user.level not in ['super_manager', 'manager']:
            return jsonify({'code': -1, 'msg': '权限不足'}), 403
        
        business_id = current_user.business_id
        days = request.args.get('days', 7, type=int)
        
        result = CommentService.get_comment_trend(
            business_id=business_id,
            days=days
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f'获取趋势失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@comment_bp.route('/delete/<int:comment_id>', methods=['DELETE'])
@login_required
def delete_comment(comment_id):
    """
    删除评价（管理员功能）
    """
    try:
        if current_user.level not in ['super_manager', 'manager']:
            return jsonify({'code': -1, 'msg': '权限不足'}), 403
        
        result = CommentService.delete_comment(comment_id)
        
        if result['code'] == 0:
            logger.info(f"管理员 {current_user.user_name} 删除了评价 {comment_id}")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f'删除评价失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500

