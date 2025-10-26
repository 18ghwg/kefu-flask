"""
认证API
"""
from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.service import Service

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    """客服登录"""
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'code': 1000, 'msg': '参数不完整'}), 400
    
    username = data['username']
    password = data['password']
    business_id = data.get('business_id', 1)
    
    # 查询客服
    service = Service.query.filter_by(
        user_name=username,
        business_id=business_id
    ).first()
    
    if not service or not service.verify_password(password):
        return jsonify({'code': 1001, 'msg': '用户名或密码错误'}), 401
    
    # 登录
    login_user(service, remember=True)
    
    # 更新在线状态
    service.state = 'online'
    db.session.commit()
    
    return jsonify({
        'code': 0,
        'msg': '登录成功',
        'data': {
            'service': service.to_dict()
        }
    })


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """客服登出"""
    # 更新离线状态
    current_user.state = 'offline'
    db.session.commit()
    
    logout_user()
    
    return jsonify({'code': 0, 'msg': '退出成功'})


@auth_bp.route('/check', methods=['GET'])
@login_required
def check():
    """检查登录状态"""
    return jsonify({
        'code': 0,
        'msg': 'success',
        'data': {
            'service': current_user.to_dict()
        }
    })


@auth_bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    """修改密码"""
    data = request.get_json()
    
    if not data or not data.get('old_password') or not data.get('new_password'):
        return jsonify({'code': 1000, 'msg': '参数不完整'}), 400
    
    old_password = data['old_password']
    new_password = data['new_password']
    
    # 验证旧密码
    if not current_user.verify_password(old_password):
        return jsonify({'code': 1001, 'msg': '旧密码不正确'}), 400
    
    # 设置新密码
    current_user.password = new_password
    db.session.commit()
    
    return jsonify({'code': 0, 'msg': '密码修改成功'})
