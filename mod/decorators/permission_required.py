"""
权限验证装饰器
"""
from functools import wraps
from flask import abort, jsonify, request
from flask_login import current_user


def permission_required(*allowed_levels):
    """
    权限验证装饰器
    
    Args:
        *allowed_levels: 允许访问的权限级别，如 'super_manager', 'manager', 'service'
    
    Usage:
        @permission_required('super_manager')
        def admin_only_view():
            pass
        
        @permission_required('super_manager', 'manager')
        def manager_view():
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 检查用户是否登录
            if not current_user.is_authenticated:
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'code': 401, 'msg': '未登录'}), 401
                abort(401)
            
            # 检查用户权限
            if current_user.level not in allowed_levels:
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'code': 403, 'msg': '权限不足'}), 403
                abort(403)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def manager_required(func):
    """管理员及以上权限"""
    return permission_required('super_manager', 'manager')(func)


def super_manager_required(func):
    """超级管理员权限"""
    return permission_required('super_manager')(func)

