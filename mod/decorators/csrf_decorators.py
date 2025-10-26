"""
CSRF装饰器
用于灵活控制CSRF验证
"""
from functools import wraps
from flask import g, request, jsonify
from flask_wtf.csrf import validate_csrf, generate_csrf, CSRFError
import logging

logger = logging.getLogger(__name__)


def csrf_exempt(func):
    """
    装饰器：豁免CSRF验证
    用于不需要CSRF验证的API路由
    
    使用示例：
    @app.route('/api/public/endpoint', methods=['POST'])
    @csrf_exempt
    def public_endpoint():
        return jsonify({'msg': 'success'})
    """
    @wraps(func)
    def decorated_function(*args, **kwargs):
        g._csrf_exempt = True
        return func(*args, **kwargs)
    return decorated_function


def csrf_required(func):
    """
    装饰器：强制要求CSRF验证
    即使是GET请求也需要CSRF Token
    
    使用示例：
    @app.route('/api/sensitive', methods=['GET'])
    @csrf_required
    def sensitive_endpoint():
        return jsonify({'msg': 'success'})
    """
    @wraps(func)
    def decorated_function(*args, **kwargs):
        try:
            # 从请求头或表单数据中获取CSRF Token
            token = (
                request.headers.get('X-CSRFToken') or
                request.headers.get('X-CSRF-Token') or
                request.form.get('csrf_token')
            )
            
            if not token:
                logger.warning(f"CSRF Token缺失 - {request.method} {request.path}")
                return jsonify({
                    'code': 403,
                    'msg': 'CSRF Token缺失'
                }), 403
            
            # 验证CSRF Token
            validate_csrf(token)
            
        except CSRFError as e:
            logger.warning(f"CSRF验证失败 - {request.method} {request.path}: {str(e)}")
            return jsonify({
                'code': 403,
                'msg': 'CSRF验证失败'
            }), 403
        
        return func(*args, **kwargs)
    return decorated_function


def get_csrf_token():
    """
    获取当前会话的CSRF Token
    用于手动获取Token
    """
    return generate_csrf()

