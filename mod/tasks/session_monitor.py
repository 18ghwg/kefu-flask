"""
会话监控定时任务
- 检测会话超时
- 自动关闭超时会话
"""

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from mod.mysql.models import Queue, SystemSetting
from exts import db
import log

logger = log.get_logger(__name__)

# 全局调度器和应用实例
scheduler = None
_app = None
_socketio = None


def check_session_timeout():
    """检查会话超时"""
    global _app, _socketio
    
    # 使用应用上下文
    with _app.app_context():
        try:
            # 获取所有进行中的会话 (service_id > 0 表示正在会话)
            active_sessions = Queue.query.filter(
                Queue.state == 'normal',
                Queue.service_id > 0
            ).all()
        
            timeout_count = 0
            
            for session in active_sessions:
                try:
                    # 获取系统设置
                    settings = SystemSetting.query.filter_by(
                        business_id=session.business_id
                    ).first()
                    
                    # 超时时间（秒），默认30分钟
                    timeout_seconds = settings.session_timeout if settings else 1800
                    
                    # 检查最后消息时间
                    if session.last_message_time:
                        time_diff = (datetime.now() - session.last_message_time).total_seconds()
                        
                        if time_diff > timeout_seconds:
                            # 会话超时
                            logger.info(f'会话超时: visitor_id={session.visitor_id}, 超时{int(time_diff)}秒')
                            
                            # 更新状态为完成
                            session.state = 'complete'
                            session.updated_at = datetime.now()
                            db.session.commit()
                            
                            # 通知访客和客服
                            _socketio.emit('session_timeout', {
                                'visitor_id': session.visitor_id,
                                'service_id': session.service_id,
                                'message': '会话已超时自动结束'
                            })
                            
                            timeout_count += 1
                            
                except Exception as e:
                    logger.error(f'检查单个会话超时失败: {e}')
                    continue
            
            if timeout_count > 0:
                logger.info(f'本次检查完成，共{timeout_count}个会话超时')
                
        except Exception as e:
            logger.error(f'检查会话超时失败: {e}')


def check_auto_close():
    """检查自动关闭超时"""
    global _app
    
    # 使用应用上下文
    with _app.app_context():
        try:
            # 获取所有已完成的会话
            completed_sessions = Queue.query.filter_by(state='complete').all()
            
            close_count = 0
            
            for session in completed_sessions:
                try:
                    # 获取系统设置
                    settings = SystemSetting.query.filter_by(
                        business_id=session.business_id
                    ).first()
                    
                    # 自动关闭超时（秒），默认5分钟
                    close_timeout = settings.auto_close_timeout if settings else 300
                    
                    # 检查更新时间
                    if session.updated_at:
                        time_diff = (datetime.now() - session.updated_at).total_seconds()
                        
                        if time_diff > close_timeout:
                            # 自动关闭（删除记录）
                            logger.info(f'自动关闭会话: qid={session.qid}, visitor_id={session.visitor_id}')
                            
                            db.session.delete(session)
                            db.session.commit()
                            
                            close_count += 1
                            
                except Exception as e:
                    logger.error(f'检查单个会话自动关闭失败: {e}')
                    db.session.rollback()
                    continue
            
            if close_count > 0:
                logger.info(f'本次检查完成，共{close_count}个会话自动关闭')
                
        except Exception as e:
            logger.error(f'检查自动关闭失败: {e}')


def start_session_monitor(app, socketio):
    """启动会话监控定时任务"""
    global scheduler, _app, _socketio
    
    # 保存app和socketio实例
    _app = app
    _socketio = socketio
    
    if scheduler is not None:
        logger.warning('会话监控任务已经启动，跳过重复启动')
        return scheduler
    
    try:
        scheduler = BackgroundScheduler()
        
        # 每分钟检查一次会话超时
        scheduler.add_job(
            check_session_timeout,
            'interval',
            minutes=1,
            id='check_session_timeout',
            name='检查会话超时'
        )
        
        # 每分钟检查一次自动关闭
        scheduler.add_job(
            check_auto_close,
            'interval',
            minutes=1,
            id='check_auto_close',
            name='检查自动关闭'
        )
        
        scheduler.start()
        logger.info('✅ 会话监控定时任务已启动')
        
        return scheduler
        
    except Exception as e:
        logger.error(f'启动会话监控任务失败: {e}')
        return None


def stop_session_monitor():
    """停止会话监控定时任务"""
    global scheduler
    
    if scheduler:
        scheduler.shutdown()
        scheduler = None
        logger.info('会话监控定时任务已停止')

