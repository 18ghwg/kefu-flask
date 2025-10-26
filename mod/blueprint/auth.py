"""
认证API蓝图
"""
from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from mod.mysql.ModuleClass import service_management
import log

auth_bp = Blueprint('auth', __name__)
logger = log.get_logger(__name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    """客服登录"""
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'code': 1000, 'msg': '参数不完整'}), 400
    
    username = data['username']
    password = data['password']
    business_id = data.get('business_id', 1)
    
    # 验证客服登录
    result = service_management.authenticate(username, password, business_id)
    
    if result['code'] != 0:
        logger.warning(f"登录失败: {username}")
        return jsonify(result), 401
    
    # 登录
    service = result['data']
    login_user(service, remember=True)
    
    logger.info(f"用户登录: {username}")
    
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
    result = service_management.logout_service(current_user.service_id)
    
    logger.info(f"用户登出: {current_user.user_name}")
    
    logout_user()
    
    return jsonify(result)


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


@auth_bp.route('/current-user', methods=['GET'])
@login_required
def get_current_user():
    """获取当前登录用户信息"""
    try:
        user_data = current_user.to_dict()
        # 添加额外需要的字段
        user_data['business_id'] = current_user.business_id
        user_data['level'] = current_user.level
        
        return jsonify({
            'code': 0,
            'msg': '成功',
            'data': user_data
        })
    except Exception as e:
        logger.error(f"获取用户信息失败: {e}")
        return jsonify({
            'code': -1,
            'msg': '获取用户信息失败'
        }), 500


@auth_bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    """修改密码"""
    data = request.get_json()
    
    if not data or not data.get('old_password') or not data.get('new_password'):
        return jsonify({'code': 1000, 'msg': '参数不完整'}), 400
    
    old_password = data['old_password']
    new_password = data['new_password']
    
    # 修改密码
    result = service_management.change_password(
        service_id=current_user.service_id,
        old_password=old_password,
        new_password=new_password
    )
    
    if result['code'] == 0:
        logger.info(f"密码修改: {current_user.user_name}")
    
    return jsonify(result)
