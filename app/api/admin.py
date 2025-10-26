"""
管理API
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.service import Service
from app.models.robot import Robot

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/services', methods=['GET'])
@login_required
def get_services():
    """获取客服列表（排除机器人）"""
    if current_user.level not in ['super_manager', 'manager']:
        return jsonify({'code': 1002, 'msg': '权限不足'}), 403
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # ⚡ 排除机器人客服（service_id=0 或 user_name='robot'）
    pagination = Service.query.filter(
        Service.business_id == current_user.business_id,
        Service.service_id != 0,
        Service.user_name != 'robot'
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    services = [s.to_dict() for s in pagination.items]
    
    return jsonify({
        'code': 0,
        'data': {
            'services': services,
            'total': pagination.total,
            'page': page,
            'per_page': per_page
        }
    })


@admin_bp.route('/services', methods=['POST'])
@login_required
def add_service():
    """添加客服"""
    if current_user.level not in ['super_manager', 'manager']:
        return jsonify({'code': 1002, 'msg': '权限不足'}), 403
    
    data = request.get_json()
    
    required_fields = ['user_name', 'nick_name', 'password']
    if not all(field in data for field in required_fields):
        return jsonify({'code': 1000, 'msg': '参数不完整'}), 400
    
    # 检查用户名是否已存在
    if Service.query.filter_by(user_name=data['user_name']).first():
        return jsonify({'code': 3000, 'msg': '用户名已存在'}), 400
    
    # 创建客服
    service = Service(
        user_name=data['user_name'],
        nick_name=data['nick_name'],
        business_id=current_user.business_id,
        level=data.get('level', 'service'),
        group_id=data.get('group_id', '0'),
        phone=data.get('phone', ''),
        email=data.get('email', '')
    )
    service.password = data['password']
    
    db.session.add(service)
    db.session.commit()
    
    return jsonify({
        'code': 0,
        'msg': '添加成功',
        'data': service.to_dict()
    })


@admin_bp.route('/robots', methods=['GET'])
@login_required
def get_robots():
    """获取机器人知识库"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    pagination = Robot.query.filter_by(
        business_id=current_user.business_id
    ).order_by(Robot.sort.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    robots = [r.to_dict() for r in pagination.items]
    
    return jsonify({
        'code': 0,
        'data': {
            'robots': robots,
            'total': pagination.total,
            'page': page,
            'per_page': per_page
        }
    })


@admin_bp.route('/robots', methods=['POST'])
@login_required
def add_robot():
    """添加机器人知识库"""
    if current_user.level not in ['super_manager', 'manager']:
        return jsonify({'code': 1002, 'msg': '权限不足'}), 403
    
    data = request.get_json()
    
    required_fields = ['keyword', 'reply']
    if not all(field in data for field in required_fields):
        return jsonify({'code': 1000, 'msg': '参数不完整'}), 400
    
    robot = Robot(
        business_id=current_user.business_id,
        keyword=data['keyword'],
        reply=data['reply'],
        sort=data.get('sort', 0),
        status=data.get('status', 1)
    )
    
    db.session.add(robot)
    db.session.commit()
    
    return jsonify({
        'code': 0,
        'msg': '添加成功',
        'data': robot.to_dict()
    })
