"""
操作日志服务类
"""
import json
from datetime import datetime
from exts import db
from mod.mysql.models import OperationLog
from flask import request
from flask_login import current_user
import log

logger = log.get_logger(__name__)


class OperationLogService:
    """
    操作日志服务类
    """
    
    @staticmethod
    def create_log(
        business_id,
        module,
        action,
        description,
        target_id='',
        target_type='',
        params=None,
        result='success',
        error_msg='',
        operator_id=None,
        operator_name=None,
        operator_type='admin'
    ):
        """
        创建操作日志
        """
        try:
            # 获取请求信息
            method = request.method if request else ''
            path = request.path if request else ''
            ip = request.remote_addr if request else ''
            user_agent = request.headers.get('User-Agent', '') if request else ''
            
            # 处理参数
            params_json = json.dumps(params, ensure_ascii=False) if params else ''
            
            # 创建日志
            log_entry = OperationLog(
                business_id=business_id,
                operator_id=operator_id or (current_user.id if hasattr(current_user, 'id') else 0),
                operator_name=operator_name or (current_user.username if hasattr(current_user, 'username') else 'System'),
                operator_type=operator_type,
                module=module,
                action=action,
                description=description,
                method=method,
                path=path,
                ip=ip,
                user_agent=user_agent[:500] if len(user_agent) > 500 else user_agent,
                target_id=str(target_id),
                target_type=target_type,
                params=params_json,
                result=result,
                error_msg=error_msg
            )
            
            db.session.add(log_entry)
            db.session.commit()
            
            logger.info(f"操作日志已记录: {operator_name or 'System'} {action} {module}")
            return log_entry
            
        except Exception as e:
            logger.error(f"创建操作日志失败: {e}")
            db.session.rollback()
            return None
    
    @staticmethod
    def get_logs(business_id, page=1, per_page=20, filters=None):
        """
        获取操作日志列表（分页）
        """
        try:
            query = OperationLog.query.filter_by(business_id=business_id)
            
            # 应用过滤器
            if filters:
                if filters.get('operator_type'):
                    query = query.filter_by(operator_type=filters['operator_type'])
                if filters.get('module'):
                    query = query.filter_by(module=filters['module'])
                if filters.get('action'):
                    query = query.filter_by(action=filters['action'])
                if filters.get('result'):
                    query = query.filter_by(result=filters['result'])
                if filters.get('keyword'):
                    keyword = f"%{filters['keyword']}%"
                    query = query.filter(
                        db.or_(
                            OperationLog.operator_name.like(keyword),
                            OperationLog.description.like(keyword)
                        )
                    )
                if filters.get('start_date'):
                    query = query.filter(OperationLog.created_at >= filters['start_date'])
                if filters.get('end_date'):
                    query = query.filter(OperationLog.created_at <= filters['end_date'])
            
            # 按时间倒序
            query = query.order_by(OperationLog.created_at.desc())
            
            # 分页
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            
            return {
                'logs': [log.to_dict() for log in pagination.items],
                'total': pagination.total,
                'pages': pagination.pages,
                'current_page': page,
                'per_page': per_page
            }
            
        except Exception as e:
            logger.error(f"获取操作日志列表失败: {e}")
            return {
                'logs': [],
                'total': 0,
                'pages': 0,
                'current_page': page,
                'per_page': per_page
            }
    
    @staticmethod
    def get_log(log_id):
        """
        获取单条日志详情
        """
        try:
            log_entry = OperationLog.query.get(log_id)
            return log_entry.to_dict() if log_entry else None
        except Exception as e:
            logger.error(f"获取日志详情失败: {e}")
            return None
    
    @staticmethod
    def delete_logs(business_id, log_ids):
        """
        批量删除日志
        """
        try:
            OperationLog.query.filter(
                OperationLog.business_id == business_id,
                OperationLog.id.in_(log_ids)
            ).delete(synchronize_session=False)
            
            db.session.commit()
            logger.info(f"已删除 {len(log_ids)} 条日志")
            return True
            
        except Exception as e:
            logger.error(f"删除日志失败: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def clear_old_logs(business_id, days=90):
        """
        清理N天前的日志
        """
        try:
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            count = OperationLog.query.filter(
                OperationLog.business_id == business_id,
                OperationLog.created_at < cutoff_date
            ).delete(synchronize_session=False)
            
            db.session.commit()
            logger.info(f"已清理 {count} 条旧日志（{days}天前）")
            return count
            
        except Exception as e:
            logger.error(f"清理旧日志失败: {e}")
            db.session.rollback()
            return 0
    
    @staticmethod
    def get_statistics(business_id, days=7):
        """
        获取日志统计
        """
        try:
            from datetime import timedelta
            from sqlalchemy import func
            
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # 按模块统计
            module_stats = db.session.query(
                OperationLog.module,
                func.count(OperationLog.id).label('count')
            ).filter(
                OperationLog.business_id == business_id,
                OperationLog.created_at >= start_date
            ).group_by(OperationLog.module).all()
            
            # 按操作类型统计
            action_stats = db.session.query(
                OperationLog.action,
                func.count(OperationLog.id).label('count')
            ).filter(
                OperationLog.business_id == business_id,
                OperationLog.created_at >= start_date
            ).group_by(OperationLog.action).all()
            
            # 按操作人统计
            operator_stats = db.session.query(
                OperationLog.operator_name,
                func.count(OperationLog.id).label('count')
            ).filter(
                OperationLog.business_id == business_id,
                OperationLog.created_at >= start_date
            ).group_by(OperationLog.operator_name).order_by(func.count(OperationLog.id).desc()).limit(10).all()
            
            # 失败操作统计
            failed_count = OperationLog.query.filter(
                OperationLog.business_id == business_id,
                OperationLog.created_at >= start_date,
                OperationLog.result == 'fail'
            ).count()
            
            return {
                'module_stats': [{'module': m, 'count': c} for m, c in module_stats],
                'action_stats': [{'action': a, 'count': c} for a, c in action_stats],
                'operator_stats': [{'operator': o, 'count': c} for o, c in operator_stats],
                'failed_count': failed_count,
                'days': days
            }
            
        except Exception as e:
            logger.error(f"获取日志统计失败: {e}")
            return {
                'module_stats': [],
                'action_stats': [],
                'operator_stats': [],
                'failed_count': 0,
                'days': days
            }


# 单例实例
operation_log_service = OperationLogService()

