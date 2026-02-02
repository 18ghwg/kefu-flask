"""
管理API蓝图
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from mod.mysql.ModuleClass import (
    service_management,
    chat_service,
    StatisticsService,
    system_setting_service
)
from mod.utils.operation_log_decorator import log_operation, log_operation_simple
import log

admin_bp = Blueprint('admin', __name__)
logger = log.get_logger(__name__)


@admin_bp.route('/services', methods=['GET'])
@login_required
def get_services():
    """获取客服列表"""
    if current_user.level not in ['super_manager', 'manager']:
        return jsonify({'code': 1002, 'msg': '权限不足'}), 403
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    result = service_management.get_all_services(current_user.business_id)
    
    if result['code'] == 0:
        return jsonify({
            'code': 0,
            'data': {
                'services': result['data']['services'],
                'total': result['data']['total'],
                'page': page,
                'per_page': per_page
            }
        })
    else:
        return jsonify(result), 500


@admin_bp.route('/services', methods=['POST'])
@login_required
@log_operation(
    module='客服管理',
    action='create',
    description_template='管理员{user}添加了新客服',
    success_msg='成功添加新客服',
    error_msg='添加客服失败'
)
def add_service():
    """添加客服"""
    if current_user.level not in ['super_manager', 'manager']:
        return jsonify({'code': 1002, 'msg': '权限不足'}), 403
    
    data = request.get_json()
    
    required_fields = ['user_name', 'nick_name', 'password']
    if not all(field in data for field in required_fields):
        return jsonify({'code': 1000, 'msg': '参数不完整'}), 400
    
    result = service_management.add_service(
        business_id=current_user.business_id,
        user_name=data['user_name'],
        nick_name=data['nick_name'],
        password=data['password'],
        level=data.get('level', 'service'),
        group_id=data.get('group_id', '0'),
        phone=data.get('phone', ''),
        email=data.get('email', '')
    )
    
    if result['code'] == 0:
        logger.info(f"添加客服: {data['user_name']}")
    
    return jsonify(result)


@admin_bp.route('/services/<service_id>', methods=['PUT'])
@login_required
@log_operation(
    module='客服管理',
    action='update',
    description_template='管理员{user}修改了客服信息',
    success_msg='客服信息修改成功',
    error_msg='客服信息修改失败'
)
def update_service(service_id):
    """更新客服"""
    if current_user.level not in ['super_manager', 'manager']:
        return jsonify({'code': 1002, 'msg': '权限不足'}), 403
    
    data = request.get_json()
    
    result = service_management.update_service(
        service_id=service_id,
        **data
    )
    
    if result['code'] == 0:
        logger.info(f"更新客服: {service_id}")
    
    return jsonify(result)


@admin_bp.route('/services/<service_id>', methods=['DELETE'])
@login_required
@log_operation(
    module='客服管理',
    action='delete',
    description_template='管理员{user}删除了客服',
    success_msg='客服删除成功',
    error_msg='客服删除失败'
)
def delete_service_route(service_id):
    """删除客服"""
    if current_user.level not in ['super_manager', 'manager']:
        return jsonify({'code': 1002, 'msg': '权限不足'}), 403
    
    result = service_management.delete_service(service_id)
    
    if result['code'] == 0:
        logger.info(f"删除客服: {service_id}")
    
    return jsonify(result)


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
    
    logger.info(f"添加机器人知识库: {data['keyword']}")
    
    return jsonify({
        'code': 0,
        'msg': '添加成功',
        'data': robot.to_dict()
    })


# ========== 聊天记录API ==========

@admin_bp.route('/chat-history', methods=['GET'])
@login_required
def get_chat_history():
    """获取聊天记录"""
    try:
        if current_user.level not in ['super_manager', 'manager']:
            return jsonify({'code': -1, 'msg': '权限不足'}), 403
        
        business_id = current_user.business_id
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        # 筛选条件
        visitor_id = request.args.get('visitor_id')
        service_id = request.args.get('service_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        keyword = request.args.get('keyword')
        
        result = chat_service.get_chat_history(
            business_id=business_id,
            visitor_id=visitor_id,
            service_id=service_id,
            start_date=start_date,
            end_date=end_date,
            keyword=keyword,
            page=page,
            per_page=per_page
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f'获取聊天记录失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@admin_bp.route('/chat-sessions', methods=['GET'])
@login_required
def get_chat_sessions():
    """获取会话列表"""
    try:
        if current_user.level not in ['super_manager', 'manager']:
            return jsonify({'code': -1, 'msg': '权限不足'}), 403
        
        business_id = current_user.business_id
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        state = request.args.get('state')  # waiting, chatting, complete
        
        result = chat_service.get_chat_sessions(
            business_id=business_id,
            state=state,
            page=page,
            per_page=per_page
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f'获取会话列表失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


# ========== 数据统计API ==========

@admin_bp.route('/statistics/overview', methods=['GET'])
@login_required
def get_statistics_overview():
    """获取概览统计"""
    try:
        if current_user.level not in ['super_manager', 'manager']:
            return jsonify({'code': -1, 'msg': '权限不足'}), 403
        
        business_id = current_user.business_id
        days = request.args.get('days', 7, type=int)  # 默认最近7天
        
        result = StatisticsService.get_overview_statistics(business_id, days)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f'获取统计数据失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@admin_bp.route('/statistics/trend', methods=['GET'])
@login_required
def get_statistics_trend():
    """获取趋势数据"""
    try:
        if current_user.level not in ['super_manager', 'manager']:
            return jsonify({'code': -1, 'msg': '权限不足'}), 403
        
        business_id = current_user.business_id
        days = request.args.get('days', 7, type=int)
        
        result = StatisticsService.get_trend_data(business_id, days)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f'获取趋势数据失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@admin_bp.route('/statistics/service-performance', methods=['GET'])
@login_required
def get_service_performance():
    """获取客服工作量统计"""
    try:
        if current_user.level not in ['super_manager', 'manager']:
            return jsonify({'code': -1, 'msg': '权限不足'}), 403
        
        business_id = current_user.business_id
        days = request.args.get('days', 7, type=int)
        
        result = StatisticsService.get_service_performance(business_id, days)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f'获取客服绩效失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


# ========== 聊天记录额外API ==========

@admin_bp.route('/chat-history/statistics', methods=['GET'])
@login_required
def get_chat_history_statistics():
    """获取聊天记录统计数据"""
    try:
        if current_user.level not in ['super_manager', 'manager']:
            return jsonify({'code': -1, 'msg': '权限不足'}), 403
        
        business_id = current_user.business_id
        days = request.args.get('days', 7, type=int)
        
        from mod.mysql.models import Chat, Queue
        from datetime import datetime, timedelta
        from sqlalchemy import func

        start_date = datetime.now() - timedelta(days=days)

        # 总消息数
        total_messages = Chat.query.filter(
            Chat.business_id == business_id,
            Chat.created_at >= start_date
        ).count()

        # 总会话数
        total_sessions = Queue.query.filter(
            Queue.business_id == business_id,
            Queue.created_at >= start_date
        ).count()

        # 平均时长（分钟）- 计算已完成会话的平均时长
        completed_sessions = Queue.query.filter(
            Queue.business_id == business_id,
            Queue.created_at >= start_date,
            Queue.state == 'complete',
            Queue.updated_at.isnot(None)
        ).all()

        avg_duration = 0
        if completed_sessions:
            total_duration = 0
            for session in completed_sessions:
                duration = (session.updated_at - session.created_at).total_seconds()
                total_duration += duration
            avg_duration = int(total_duration / len(completed_sessions) / 60)  # 转换为分钟

        # 平均响应时间（秒）- 计算客服首次响应时间
        avg_response_time = 0
        sessions_with_response = 0

        for session in Queue.query.filter(
            Queue.business_id == business_id,
            Queue.created_at >= start_date,
            Queue.service_id.isnot(None)
        ).limit(100).all():
            # 查找客服的第一条消息
            first_service_msg = Chat.query.filter_by(
                visitor_id=session.visitor_id,
                business_id=business_id,
                direction='to_visitor'
            ).filter(
                Chat.created_at >= session.created_at,
                Chat.service_id > 0  # 排除机器人
            ).order_by(Chat.created_at.asc()).first()

            if first_service_msg:
                response_time = (first_service_msg.created_at - session.created_at).total_seconds()
                avg_response_time += response_time
                sessions_with_response += 1

        if sessions_with_response > 0:
            avg_response_time = int(avg_response_time / sessions_with_response)
        
        return jsonify({
            'code': 0,
            'msg': '获取成功',
            'data': {
                'total_messages': total_messages,
                'total_sessions': total_sessions,
                'avg_duration': avg_duration,
                'avg_response_time': avg_response_time
            }
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f'获取聊天记录统计失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@admin_bp.route('/chat-history/session/<queue_id>', methods=['GET'])
@login_required
def get_session_detail(queue_id):
    """获取会话基本信息（不包含消息内容，消息请使用分页API）"""
    try:
        if current_user.level not in ['super_manager', 'manager']:
            return jsonify({'code': -1, 'msg': '权限不足'}), 403
        
        from mod.mysql.models import Chat, Visitor, Service
        from datetime import datetime
        from sqlalchemy import func
        from exts import db
        
        # queue_id实际上是visitor_id
        visitor_id = queue_id
        business_id = current_user.business_id
        
        # 获取访客信息
        visitor = Visitor.query.filter_by(
            visitor_id=visitor_id,
            business_id=business_id
        ).first()
        
        if not visitor:
            return jsonify({'code': -1, 'msg': '访客不存在'}), 404
        
        # 获取消息数量和时间范围（优化：使用聚合查询，只查一次）
        message_stats = db.session.query(
            func.count(Chat.cid).label('total'),
            func.min(Chat.created_at).label('start_time'),
            func.max(Chat.created_at).label('end_time')
        ).filter_by(
            visitor_id=visitor_id,
            business_id=business_id
        ).first()
        
        if not message_stats or message_stats.total == 0:
            return jsonify({'code': -1, 'msg': '没有聊天记录'}), 404
        
        # 获取客服信息（从最近的客服消息）
        latest_service_chat = Chat.query.filter_by(
            visitor_id=visitor_id,
            business_id=business_id
        ).filter(Chat.service_id > 0).order_by(Chat.created_at.desc()).first()
        
        service_id = latest_service_chat.service_id if latest_service_chat else 0
        service = Service.query.filter_by(service_id=service_id).first() if service_id > 0 else None

        # 计算会话时长
        start_time = message_stats.start_time
        end_time = message_stats.end_time
        duration = int((end_time - start_time).total_seconds()) if start_time and end_time else 0
        
        # 判断状态
        now = datetime.now()
        time_since_last = (now - end_time).total_seconds() if end_time else 9999
        state = 'chatting' if time_since_last < 1800 else 'complete'  # 30分钟内算正在进行

        return jsonify({
            'code': 0,
            'msg': '获取成功',
            'data': {
                'queue_id': visitor_id,
                'visitor_id': visitor_id,
                'visitor_name': visitor.name if visitor else f'访客{visitor_id}',
                'service_id': service_id,
                'service_name': service.nick_name if service else '机器人',
                'state': state,
                'start_time': start_time.isoformat() if start_time else None,
                'end_time': end_time.isoformat() if end_time else None,
                'duration': duration,
                'message_count': message_stats.total
            }
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f'获取会话详情失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@admin_bp.route('/chat-history/session/<visitor_id>/messages', methods=['GET'])
@login_required
def get_session_messages_paginated(visitor_id):
    """分页获取会话消息（性能优化版）"""
    try:
        if current_user.level not in ['super_manager', 'manager']:
            return jsonify({'code': -1, 'msg': '权限不足'}), 403
        
        from mod.mysql.models import Chat, Visitor, Service
        from datetime import datetime
        
        business_id = current_user.business_id
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        # 获取访客信息
        visitor = Visitor.query.filter_by(
            visitor_id=visitor_id,
            business_id=business_id
        ).first()
        
        if not visitor:
            return jsonify({'code': -1, 'msg': '访客不存在'}), 404
        
        # 获取消息总数
        total_count = Chat.query.filter_by(
            visitor_id=visitor_id,
            business_id=business_id
        ).count()
        
        if total_count == 0:
            return jsonify({'code': -1, 'msg': '没有聊天记录'}), 404
        
        # 分页查询消息
        offset = (page - 1) * per_page
        messages = Chat.query.filter_by(
            visitor_id=visitor_id,
            business_id=business_id
        ).order_by(Chat.created_at.asc()).offset(offset).limit(per_page).all()
        
        # 优化：一次性获取所有需要的客服信息
        service_ids = list(set([msg.service_id for msg in messages if msg.service_id is not None and msg.service_id > 0]))
        services = {}
        if service_ids:
            service_list = Service.query.filter(Service.service_id.in_(service_ids)).all()
            services = {s.service_id: s.nick_name for s in service_list}
        
        # 构建消息列表
        message_list = []
        for msg in messages:
            # 从预加载的字典中获取客服名称
            service_name = services.get(msg.service_id, '机器人') if msg.service_id is not None and msg.service_id > 0 else '机器人'
            
            # 判断消息类型
            msg_type = 'text'
            if hasattr(msg, 'msg_type') and msg.msg_type == 2:
                msg_type = 'image' if 'image' in msg.content or 'jpg' in msg.content or 'png' in msg.content else 'file'
            
            message_list.append({
                'id': msg.cid,
                'content': msg.content,
                'direction': msg.direction,
                'msg_type': msg_type,
                'service_id': msg.service_id,
                'service_name': service_name,
                'visitor_name': visitor.name if visitor else f'访客{visitor_id}',  # 添加访客名称
                'timestamp': msg.created_at.isoformat() if msg.created_at else None
            })
        
        # 计算总页数
        import math
        total_pages = math.ceil(total_count / per_page)
        
        return jsonify({
            'code': 0,
            'msg': '获取成功',
            'data': {
                'messages': message_list,
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'total_pages': total_pages,
                'has_more': page < total_pages
            }
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f'分页获取会话消息失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@admin_bp.route('/chat-history/export', methods=['GET'])
@login_required
def export_chat_history():
    """导出聊天记录"""
    try:
        if current_user.level not in ['super_manager', 'manager']:
            return jsonify({'code': -1, 'msg': '权限不足'}), 403
        
        # 获取筛选参数
        business_id = current_user.business_id
        visitor_id = request.args.get('visitor_id')
        service_id = request.args.get('service_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        keyword = request.args.get('keyword')
        export_format = request.args.get('format', 'json')  # json or csv
        
        # 获取聊天记录
        result = chat_service.get_chat_history(
            business_id=business_id,
            visitor_id=visitor_id,
            service_id=service_id,
            start_date=start_date,
            end_date=end_date,
            keyword=keyword,
            page=1,
            per_page=10000  # 导出所有记录
        )
        
        if result['code'] == 0:
            from flask import make_response
            import json
            from datetime import datetime
            
            if export_format == 'csv':
                # 生成CSV格式
                import csv
                import io
                
                output = io.StringIO()
                writer = csv.writer(output)
                
                # 写入表头
                writer.writerow(['消息ID', '访客', '客服', '消息内容', '消息方向', '消息类型', '时间'])
                
                # 写入数据
                for msg in result['data']['list']:
                    writer.writerow([
                        msg['id'],
                        msg['visitor_name'],
                        msg['service_name'],
                        msg['content'],
                        '访客→客服' if msg['direction'] == 'to_service' else '客服→访客',
                        msg.get('msg_type', 'text'),
                        msg['timestamp']
                    ])
                
                output.seek(0)
                response = make_response(output.getvalue())
                response.headers['Content-Type'] = 'text/csv; charset=utf-8-sig'
                filename = f'chat_history_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
                response.headers['Content-Disposition'] = f'attachment; filename={filename}'
                
            else:
                # 生成JSON格式
                export_data = {
                    'export_time': datetime.now().isoformat(),
                    'business_id': business_id,
                    'filters': {
                        'visitor_id': visitor_id,
                        'service_id': service_id,
                        'start_date': start_date,
                        'end_date': end_date,
                        'keyword': keyword
                    },
                    'total_records': result['data']['total'],
                    'records': result['data']['list']
                }
                
                response = make_response(json.dumps(export_data, ensure_ascii=False, indent=2))
                response.headers['Content-Type'] = 'application/json; charset=utf-8'
                filename = f'chat_history_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
                response.headers['Content-Disposition'] = f'attachment; filename={filename}'
            
            logger.info(f"管理员 {current_user.user_name} 导出了{result['data']['total']}条聊天记录（格式：{export_format}）")
            return response
        else:
            return jsonify(result), 500
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f'导出聊天记录失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@admin_bp.route('/business-info', methods=['GET'])
@login_required
def get_business_info():
    """获取商户信息"""
    try:
        if current_user.level not in ['super_manager', 'manager']:
            return jsonify({'code': -1, 'msg': '权限不足'}), 403
        
        from mod.mysql.models import Business
        business = Business.query.get(current_user.business_id)
        
        if business:
            return jsonify({
                'code': 0,
                'msg': 'success',
                'data': business.to_dict()
            })
        else:
            return jsonify({'code': -1, 'msg': '商户信息不存在'}), 404
        
    except Exception as e:
        logger.error(f'获取商户信息失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@admin_bp.route('/business-info', methods=['PUT'])
@login_required
@log_operation(
    module='系统设置',
    action='update',
    description_template='管理员{user}修改了商户信息',
    success_msg='商户信息修改成功',
    error_msg='商户信息修改失败'
)
def update_business_info():
    """更新商户信息"""
    try:
        if current_user.level not in ['super_manager', 'manager']:
            return jsonify({'code': -1, 'msg': '权限不足'}), 403
        
        from mod.mysql.models import Business
        from exts import db
        
        data = request.get_json()
        if not data:
            return jsonify({'code': -1, 'msg': '缺少参数'}), 400
        
        business = Business.query.get(current_user.business_id)
        if not business:
            return jsonify({'code': -1, 'msg': '商户信息不存在'}), 404
        
        # 更新商户信息
        allowed_fields = [
            'business_name', 'copyright', 'lang', 'distribution_rule',
            'voice_state', 'video_state', 'audio_state', 'template_state',
            'voice_address', 'push_url'
        ]
        
        for field in allowed_fields:
            if field in data:
                setattr(business, field, data[field])
        
        db.session.commit()
        
        logger.info(f"管理员 {current_user.user_name} 更新了商户信息")
        return jsonify({
            'code': 0,
            'msg': '更新成功'
        })
        
    except Exception as e:
        logger.error(f'更新商户信息失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@admin_bp.route('/system-settings', methods=['GET'])
@login_required
def get_system_settings():
    """获取系统设置"""
    try:
        if current_user.level not in ['super_manager', 'manager']:
            return jsonify({'code': -1, 'msg': '权限不足'}), 403
        
        settings = system_setting_service.get_or_create_settings(current_user.business_id)
        
        if settings:
            return jsonify({
                'code': 0,
                'msg': 'success',
                'data': settings.to_dict()
            })
        else:
            return jsonify({'code': -1, 'msg': '获取设置失败'}), 500
        
    except Exception as e:
        logger.error(f'获取系统设置失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@admin_bp.route('/system-settings', methods=['PUT'])
@login_required
@log_operation(
    module='系统设置',
    action='update',
    description_template='管理员{user}修改了系统设置',
    success_msg='系统设置修改成功',
    error_msg='系统设置修改失败'
)
def update_system_settings():
    """更新系统设置"""
    try:
        if current_user.level not in ['super_manager', 'manager']:
            return jsonify({'code': -1, 'msg': '权限不足'}), 403
        
        data = request.get_json()
        
        if not data:
            return jsonify({'code': -1, 'msg': '缺少参数'}), 400
        
        success = system_setting_service.update_settings(current_user.business_id, data)
        
        if success:
            logger.info(f"管理员 {current_user.user_name} 更新了系统设置")
            return jsonify({
                'code': 0,
                'msg': '更新成功'
            })
        else:
            return jsonify({'code': -1, 'msg': '更新失败'}), 500
        
    except Exception as e:
        logger.error(f'更新系统设置失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


# ========== 数据看板新增API ==========

@admin_bp.route('/comment/statistics', methods=['GET'])
@login_required
def get_comment_statistics():
    """获取评价统计"""
    try:
        if current_user.level not in ['super_manager', 'manager']:
            return jsonify({'code': -1, 'msg': '权限不足'}), 403
        
        business_id = current_user.business_id
        days = request.args.get('days', 7, type=int)
        
        result = StatisticsService.get_comment_statistics(business_id, days)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f'获取评价统计失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@admin_bp.route('/statistics/visitor-source', methods=['GET'])
@login_required
def get_visitor_source_stats():
    """获取访客来源统计"""
    try:
        if current_user.level not in ['super_manager', 'manager']:
            return jsonify({'code': -1, 'msg': '权限不足'}), 403
        
        business_id = current_user.business_id
        days = request.args.get('days', 7, type=int)
        
        result = StatisticsService.get_visitor_source_stats(business_id, days)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f'获取访客来源统计失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@admin_bp.route('/statistics/device-stats', methods=['GET'])
@login_required
def get_device_statistics():
    """获取设备统计"""
    try:
        if current_user.level not in ['super_manager', 'manager']:
            return jsonify({'code': -1, 'msg': '权限不足'}), 403
        
        business_id = current_user.business_id
        days = request.args.get('days', 7, type=int)
        
        result = StatisticsService.get_device_stats(business_id, days)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f'获取设备统计失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@admin_bp.route('/statistics/realtime-events', methods=['GET'])
@login_required
def get_realtime_events():
    """获取实时事件流"""
    try:
        if current_user.level not in ['super_manager', 'manager']:
            return jsonify({'code': -1, 'msg': '权限不足'}), 403
        
        business_id = current_user.business_id
        limit = request.args.get('limit', 10, type=int)
        
        result = StatisticsService.get_realtime_events(business_id, limit)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f'获取实时事件失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@admin_bp.route('/system-monitor', methods=['GET'])
@login_required
def get_system_monitor():
    """获取系统监控信息"""
    try:
        import psutil
        from exts import db
        
        # 获取内存信息
        memory = psutil.virtual_memory()
        process = psutil.Process()
        process_memory = process.memory_info()
        
        # 获取CPU信息
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count()
        
        # 获取数据库连接数
        try:
            # 获取当前活跃连接数
            result = db.session.execute(db.text("SHOW STATUS LIKE 'Threads_connected'"))
            threads_connected = int(result.fetchone()[1])
            
            # 获取最大连接数
            result = db.session.execute(db.text("SHOW VARIABLES LIKE 'max_connections'"))
            max_connections = int(result.fetchone()[1])
            
            db_connections = {
                'current': threads_connected,
                'max': max_connections,
                'percent': round((threads_connected / max_connections) * 100, 1)
            }
        except Exception as e:
            logger.error(f'获取数据库连接数失败: {e}')
            db_connections = {
                'current': 0,
                'max': 0,
                'percent': 0
            }
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {
                'memory': {
                    'total': memory.total,  # 总内存（字节）
                    'used': memory.used,  # 已用内存
                    'percent': memory.percent,  # 使用百分比
                    'process': process_memory.rss  # 当前进程占用内存
                },
                'cpu': {
                    'percent': cpu_percent,  # CPU使用率
                    'count': cpu_count  # CPU核心数
                },
                'db_connections': db_connections
            }
        })
        
    except Exception as e:
        logger.error(f'获取系统监控信息失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@admin_bp.route('/statistics/region-stats', methods=['GET'])
@login_required
def get_region_statistics():
    """获取访客地区分布统计"""
    try:
        if current_user.level not in ['super_manager', 'manager']:
            return jsonify({'code': -1, 'msg': '权限不足'}), 403
        
        business_id = current_user.business_id
        days = request.args.get('days', 7, type=int)
        
        result = StatisticsService.get_region_stats(business_id, days)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f'获取地区统计失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


# ========== 个人设置API ==========

@admin_bp.route('/profile', methods=['GET'])
@login_required
def get_profile():
    """获取当前用户个人信息"""
    try:
        user_data = {
            'service_id': current_user.service_id,
            'user_name': current_user.user_name,
            'nick_name': current_user.nick_name,
            'phone': current_user.phone or '',
            'email': current_user.email or '',
            'avatar': current_user.avatar or '/static/images/avatar.png',
            'level': current_user.level,
            'business_id': current_user.business_id
        }
        
        return jsonify({
            'code': 0,
            'msg': '获取成功',
            'data': user_data
        })
        
    except Exception as e:
        logger.error(f'获取个人信息失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@admin_bp.route('/profile', methods=['PUT'])
@login_required
@log_operation(
    module='个人设置',
    action='update',
    description_template='{user}修改了个人信息',
    success_msg='个人信息修改成功',
    error_msg='个人信息修改失败'
)
def update_profile():
    """更新当前用户个人信息"""
    try:
        from mod.mysql.models import Service
        from exts import db
        
        data = request.get_json()
        if not data:
            return jsonify({'code': -1, 'msg': '缺少参数'}), 400
        
        # 获取当前用户
        service = Service.query.get(current_user.service_id)
        if not service:
            return jsonify({'code': -1, 'msg': '用户不存在'}), 404
        
        # 允许更新的字段（YAGNI原则：只更新必要字段）
        allowed_fields = ['nick_name', 'phone', 'email', 'avatar']
        
        for field in allowed_fields:
            if field in data:
                setattr(service, field, data[field])
        
        db.session.commit()
        
        logger.info(f"用户 {current_user.user_name} 更新了个人信息")
        return jsonify({
            'code': 0,
            'msg': '更新成功',
            'data': {
                'service_id': service.service_id,
                'user_name': service.user_name,
                'nick_name': service.nick_name,
                'phone': service.phone,
                'email': service.email,
                'avatar': service.avatar
            }
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f'更新个人信息失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500