"""
操作日志装饰器
"""
from functools import wraps
from flask import request
from flask_login import current_user
from mod.mysql.ModuleClass import operation_log_service
import json
import log

logger = log.get_logger(__name__)


def log_operation(module, action, description_template=''):
    """
    操作日志装饰器
    
    用法:
    @log_operation('visitor', 'create', '创建访客 {visitor_id}')
    def create_visitor():
        ...
    
    参数:
        module: 操作模块（如：visitor, service, robot等）
        action: 操作动作（如：create, update, delete等）
        description_template: 描述模板，可使用{param}引用参数或返回值
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 执行原函数
            try:
                result = func(*args, **kwargs)
                is_success = True
                error_msg = ''
            except Exception as e:
                result = None
                is_success = False
                error_msg = str(e)
                raise  # 重新抛出异常
            finally:
                try:
                    # 记录日志
                    business_id = current_user.business_id if hasattr(current_user, 'business_id') else 1
                    operator_id = current_user.id if hasattr(current_user, 'id') else 0
                    operator_name = current_user.username if hasattr(current_user, 'username') else 'System'
                    operator_type = current_user.level if hasattr(current_user, 'level') else 'system'
                    
                    # 构建描述
                    description = description_template
                    
                    # 获取请求参数
                    params = {}
                    if request.method in ['POST', 'PUT', 'PATCH']:
                        try:
                            if request.is_json:
                                params = request.get_json() or {}
                            else:
                                params = request.form.to_dict()
                        except:
                            pass
                    elif request.method == 'GET':
                        params = request.args.to_dict()
                    
                    # 从kwargs获取参数（如路由参数）
                    params.update(kwargs)
                    
                    # 格式化描述（替换模板变量）
                    try:
                        if description_template and params:
                            description = description_template.format(**params)
                    except:
                        pass
                    
                    # 获取目标对象信息
                    target_id = kwargs.get('id') or kwargs.get('visitor_id') or kwargs.get('service_id') or ''
                    target_type = module
                    
                    # 创建日志
                    operation_log_service.create_log(
                        business_id=business_id,
                        module=module,
                        action=action,
                        description=description or f'{action} {module}',
                        target_id=target_id,
                        target_type=target_type,
                        params=params,
                        result='success' if is_success else 'fail',
                        error_msg=error_msg,
                        operator_id=operator_id,
                        operator_name=operator_name,
                        operator_type=operator_type
                    )
                    
                except Exception as log_error:
                    logger.error(f"记录操作日志失败: {log_error}")
            
            return result
        
        return wrapper
    return decorator

