"""
操作日志装饰器
用于自动记录关键操作日志
"""
from functools import wraps
from flask import request, jsonify
from flask_login import current_user
from mod.mysql.ModuleClass import operation_log_service
import json
import log

logger = log.get_logger(__name__)


def log_operation(module, action, description_template=None, success_msg=None, error_msg=None):
    """
    操作日志装饰器
    
    Args:
        module: 模块名称（如 'system_settings', 'service_management'）
        action: 操作类型（如 'update', 'create', 'delete'）
        description_template: 描述模板，支持占位符 {user}, {result}
        success_msg: 成功时的描述（可选，会覆盖template）
        error_msg: 失败时的描述（可选，会覆盖template）
    
    使用示例:
        @log_operation(
            module='system_settings',
            action='update',
            description_template='管理员{user}修改了系统设置',
            success_msg='系统设置修改成功',
            error_msg='系统设置修改失败'
        )
        def update_settings():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 执行原函数
            response = f(*args, **kwargs)
            
            # 记录日志
            try:
                # 获取当前用户信息
                user_name = getattr(current_user, 'user_name', 'System')
                user_id = getattr(current_user, 'id', 0)
                business_id = getattr(current_user, 'business_id', 1)
                operator_type = 'admin' if hasattr(current_user, 'level') else 'system'
                
                # 判断操作是否成功
                result = 'success'
                final_description = description_template or f'{user_name} {action} {module}'
                error_message = ''
                
                # 解析响应判断结果
                if isinstance(response, tuple):
                    response_data, status_code = response[0], response[1] if len(response) > 1 else 200
                else:
                    response_data = response
                    status_code = 200
                
                # 尝试解析JSON响应
                try:
                    if hasattr(response_data, 'get_json'):
                        json_data = response_data.get_json()
                    elif hasattr(response_data, 'json'):
                        json_data = response_data.json
                    else:
                        json_data = None
                    
                    if json_data and json_data.get('code') != 0:
                        result = 'fail'
                        error_message = json_data.get('msg', '操作失败')
                        if error_msg:
                            final_description = error_msg
                    elif success_msg:
                        final_description = success_msg
                except:
                    # 如果无法解析JSON，根据状态码判断
                    if status_code >= 400:
                        result = 'fail'
                        if error_msg:
                            final_description = error_msg
                    elif success_msg:
                        final_description = success_msg
                
                # 格式化描述
                final_description = final_description.format(
                    user=user_name,
                    result='成功' if result == 'success' else '失败'
                )
                
                # 获取请求参数
                params = {}
                if request.method in ['POST', 'PUT', 'PATCH']:
                    try:
                        params = request.get_json() or {}
                        # 过滤敏感信息
                        if 'password' in params:
                            params['password'] = '******'
                        if 'old_password' in params:
                            params['old_password'] = '******'
                        if 'new_password' in params:
                            params['new_password'] = '******'
                    except:
                        params = {}
                elif request.method == 'GET':
                    params = dict(request.args)
                
                # 获取目标ID（从路由参数或请求体）
                target_id = kwargs.get('id') or kwargs.get('service_id') or kwargs.get('visitor_id') or ''
                if not target_id and params:
                    target_id = params.get('id') or params.get('service_id') or params.get('visitor_id') or ''
                
                # 创建日志
                operation_log_service.create_log(
                    business_id=business_id,
                    module=module,
                    action=action,
                    description=final_description,
                    target_id=str(target_id),
                    target_type=module,
                    params=params,
                    result=result,
                    error_msg=error_message,
                    operator_id=user_id,
                    operator_name=user_name,
                    operator_type=operator_type
                )
                
            except Exception as e:
                logger.error(f"记录操作日志失败: {e}")
            
            return response
        
        return decorated_function
    return decorator


def log_operation_simple(module, action):
    """
    简化版操作日志装饰器
    自动根据操作类型生成描述
    
    使用示例:
        @log_operation_simple('service_management', 'create')
        def create_service():
            ...
    """
    action_cn_map = {
        'create': '创建',
        'update': '更新',
        'delete': '删除',
        'view': '查看',
        'export': '导出',
        'import': '导入',
        'login': '登录',
        'logout': '登出'
    }
    
    action_cn = action_cn_map.get(action, action)
    
    return log_operation(
        module=module,
        action=action,
        description_template=f'{{user}} {action_cn}了 {module}',
        success_msg=f'{module} {action_cn}成功',
        error_msg=f'{module} {action_cn}失败'
    )

