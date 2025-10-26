"""
访客API蓝图
"""
from flask import Blueprint, request, jsonify
from exts import db
from mod.mysql.models import Visitor, Chat, Queue
from mod.mysql.ModuleClass import chat_service
from mod.mysql.ModuleClass.VisitorServiceClass import VisitorService
from mod.mysql.ModuleClass.QueueServiceClass import QueueService
# 性能优化：导入缓存服务
from mod.services.cache_service import FAQCache, SystemSettingsCache, VisitorCache
from mod.utils.performance_monitor import PerformanceMonitor
import log
import requests
import re

visitor_bp = Blueprint('visitor', __name__)
logger = log.get_logger(__name__)


@visitor_bp.route('/init', methods=['POST'])
def init():
    """初始化访客会话"""
    data = request.get_json()
    
    required_fields = ['visitor_id', 'visitor_name', 'business_id']
    if not all(field in data for field in required_fields):
        return jsonify({'code': 1000, 'msg': '参数不完整'}), 400
    
    visitor_id = data['visitor_id']
    visitor_name = data['visitor_name']
    business_id = data['business_id']
    avatar = data.get('avatar', '/static/images/visitor.png')
    from_url = data.get('from_url', '')
    ip = request.remote_addr
    
    # 使用服务类创建或更新访客
    visitor_data = {
        'visitor_id': visitor_id,
        'visitor_name': visitor_name,
        'business_id': business_id,
        'avatar': avatar,
        'from_url': from_url,
        'ip': ip,
        'user_agent': request.headers.get('User-Agent', ''),
        'referrer': request.referrer or ''
    }
    visitor = VisitorService.create_or_update_visitor(visitor_data)
    
    # 分配客服（使用QueueService）
    queue_result = QueueService.add_to_queue(visitor_id, business_id)
    service = queue_result.get('service')
    
    return jsonify({
        'code': 0,
        'msg': 'success',
        'data': {
            'visitor': visitor.to_dict() if visitor else {},
            'service': service.to_dict() if service else {}
        }
    })


@visitor_bp.route('/message', methods=['POST'])
def send_message():
    """访客发送消息"""
    try:
        data = request.get_json()
        visitor_id = data.get('visitor_id')
        
        # 🚫 检查访客是否在黑名单中
        if visitor_id:
            from mod.mysql.models import Queue
            blacklist_check = Queue.query.filter_by(
                visitor_id=visitor_id,
                state='blacklist'
            ).first()
            
            if blacklist_check:
                logger.warning(f"🚫 拦截黑名单访客的API消息请求: {visitor_id}")
                return jsonify({
                    'code': -1,
                    'msg': '您已被限制发送消息'
                }), 403
        
        result = chat_service.handle_visitor_message(data)
        return jsonify(result)
    except Exception as e:
        logger.error(f'发送消息失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@visitor_bp.route('/history', methods=['GET'])
def get_history():
    """获取历史消息"""
    try:
        visitor_id = request.args.get('visitor_id')
        service_id = request.args.get('service_id', type=int)
        business_id = request.args.get('business_id', type=int)
        offset = request.args.get('offset', 0, type=int)
        limit = request.args.get('limit', 50, type=int)
        
        logger.info(f'获取历史消息: visitor_id={visitor_id}, service_id={service_id}, business_id={business_id}, offset={offset}, limit={limit}')
        
        if not visitor_id:
            return jsonify({'code': 1000, 'msg': '缺少visitor_id参数'}), 400
        
        # 构建查询条件（如果没有service_id，就查询该访客的所有消息）
        query = Chat.query.filter_by(visitor_id=visitor_id)
        
        # 如果提供了service_id，则过滤
        if service_id:
            query = query.filter_by(service_id=service_id)
        
        # 如果提供了business_id，也可以作为额外过滤（虽然Chat表可能没有这个字段）
        # business_id 主要用于权限验证
        
        query = query.order_by(Chat.created_at.desc())
        
        # 分页
        total = query.count()
        messages = query.offset(offset).limit(limit).all()
        
        # 转换为字典列表（注意：需要反转顺序，因为是DESC查询）
        message_list = []
        for msg in reversed(messages):
            msg_dict = {
                'cid': msg.cid,
                'content': msg.content,
                'msg_type': msg.msg_type,
                'direction': msg.direction,
                'created_at': msg.created_at.isoformat() if msg.created_at else None,
                'timestamp': msg.timestamp,
                'service_id': msg.service_id,  # 添加service_id字段，None表示机器人
                'visitor_id': msg.visitor_id   # 添加visitor_id字段
            }
            message_list.append(msg_dict)
        
        logger.info(f'查询到 {len(message_list)} 条历史消息，总数: {total}')
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {
                'messages': message_list,
                'offset': offset,
                'limit': limit,
                'total': total,
                'has_more': (offset + limit) < total
            }
        })
        
    except Exception as e:
        logger.error(f'获取历史消息失败: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'code': -1, 'msg': str(e)}), 500


# ========== 访客管理API ==========
from flask_login import login_required, current_user
from mod.mysql.ModuleClass.VisitorServiceClass import VisitorService


@visitor_bp.route('/list', methods=['GET'])
@login_required
def get_visitor_list():
    """获取访客列表"""
    try:
        # 获取参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        state = request.args.get('state', '')
        group_id = request.args.get('group_id', type=int)
        keyword = request.args.get('keyword', '')
        
        # 处理黑名单参数：空字符串表示全部，"0"表示正常，"1"表示黑名单
        is_blacklist_str = request.args.get('is_blacklist', '')
        is_blacklist = None
        if is_blacklist_str != '':
            is_blacklist = int(is_blacklist_str)
        
        # 获取商户ID
        business_id = 1  # TODO: 从current_user获取
        
        # 构建过滤条件
        filters = {}
        if state:
            filters['state'] = state
        if group_id:
            filters['group_id'] = group_id
        if keyword:
            filters['keyword'] = keyword
        if is_blacklist is not None:
            filters['is_blacklist'] = is_blacklist
        
        # 查询访客列表
        pagination = VisitorService.get_visitor_list(
            business_id=business_id,
            page=page,
            per_page=per_page,
            **filters
        )
        
        # 转换分页结果
        visitors_data = []
        for visitor in pagination.items:
            visitor_dict = visitor.to_dict()
            
            # 添加队列信息
            queue = Queue.query.filter_by(
                visitor_id=visitor.visitor_id,
                business_id=business_id
            ).order_by(Queue.created_at.desc()).first()
            
            if queue:
                visitor_dict['queue'] = {
                    'qid': queue.qid,
                    'state': queue.state,
                    'service_id': queue.service_id,
                    'created_at': queue.created_at.isoformat() if queue.created_at else None
                }
            else:
                visitor_dict['queue'] = None
            
            # 🚫 添加黑名单状态
            blacklist_queue = Queue.query.filter_by(
                visitor_id=visitor.visitor_id,
                state='blacklist'
            ).first()
            visitor_dict['is_blacklisted'] = blacklist_queue is not None
            
            visitors_data.append(visitor_dict)
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {
                'list': visitors_data,
                'total': pagination.total,
                'page': pagination.page,
                'per_page': pagination.per_page,
                'pages': pagination.pages
            }
        })
        
    except Exception as e:
        logger.error(f'获取访客列表失败: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'code': -1, 'msg': str(e)}), 500


@visitor_bp.route('/<visitor_id>/group', methods=['PUT'])
@login_required
def update_visitor_group(visitor_id):
    """更新访客分组"""
    try:
        data = request.get_json()
        group_id = data.get('group_id')
        
        if group_id is None:
            return jsonify({'code': 1000, 'msg': '参数不完整'}), 400
        
        business_id = 1  # TODO: 从current_user获取
        
        visitor = Visitor.query.filter_by(
            visitor_id=visitor_id,
            business_id=business_id
        ).first()
        
        if not visitor:
            return jsonify({'code': -1, 'msg': '访客不存在'}), 404
        
        visitor.group_id = group_id
        db.session.commit()
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': visitor.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'更新访客分组失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


# ========== 获取客户端IP API ==========
@visitor_bp.route('/get-client-ip', methods=['GET'])
def get_client_ip():
    """
    获取访客的真实IP地址
    优先级：X-Forwarded-For > X-Real-IP > CF-Connecting-IP > remote_addr
    对于本地IP，尝试获取公网IP
    """
    try:
        # 1. 检查常见的代理头
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            # X-Forwarded-For 可能包含多个IP，取第一个
            ip = forwarded_for.split(',')[0].strip()
            return jsonify({
                'code': 0,
                'data': {
                    'ip': ip,
                    'source': 'X-Forwarded-For',
                    'is_local': False
                }
            })
        
        # 2. 检查 X-Real-IP（Nginx代理常用）
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return jsonify({
                'code': 0,
                'data': {
                    'ip': real_ip,
                    'source': 'X-Real-IP',
                    'is_local': False
                }
            })
        
        # 3. 检查 CF-Connecting-IP（Cloudflare）
        cf_ip = request.headers.get('CF-Connecting-IP')
        if cf_ip:
            return jsonify({
                'code': 0,
                'data': {
                    'ip': cf_ip,
                    'source': 'CF-Connecting-IP',
                    'is_local': False
                }
            })
        
        # 4. 使用 remote_addr
        ip = request.remote_addr
        
        # 5. 判断是否为本地/内网IP
        is_local = (
            ip == '127.0.0.1' or
            ip == 'localhost' or
            ip.startswith('192.168.') or
            ip.startswith('10.') or
            ip.startswith('172.')
        )
        
        # 6. 如果是本地IP，尝试获取公网IP
        if is_local:
            try:
                import time
                start_time = time.time()
                max_total_timeout = 4  # ✅ 总体超时控制：4秒（留1秒给其他处理）
                
                # 尝试多个公网IP查询服务（按速度排序）
                services = [
                    'https://icanhazip.com',  # ✅ 最快
                    'https://ifconfig.me/ip'
                ]
                
                for service_url in services:
                    # ✅ 检查总体超时
                    if time.time() - start_time > max_total_timeout:
                        logger.warning(f'⏰ 获取公网IP总体超时（>{max_total_timeout}秒），停止尝试')
                        break
                    
                    try:
                        # ✅ 单个服务超时：2秒 → 1秒
                        response = requests.get(service_url, timeout=1)
                        if response.status_code == 200:
                            if 'ipify' in service_url:
                                public_ip = response.json().get('ip')
                            else:
                                public_ip = response.text.strip()
                            
                            elapsed = time.time() - start_time
                            logger.info(f'✅ 本地环境获取到公网IP: {public_ip} (耗时 {elapsed:.2f}s)')
                            return jsonify({
                                'code': 0,
                                'data': {
                                    'ip': public_ip,
                                    'source': 'public_ip_service',
                                    'is_local': True,
                                    'local_ip': ip
                                }
                            })
                    except Exception as e:
                        logger.warning(f'⚠️ 从 {service_url} 获取公网IP失败: {e}')
                        continue
                
                # 所有服务都失败，返回本地IP
                logger.warning('⚠️ 无法获取公网IP，返回本地IP')
                
            except Exception as e:
                logger.error(f'获取公网IP异常: {e}')
        
        # 返回最终IP
        return jsonify({
            'code': 0,
            'data': {
                'ip': ip,
                'source': 'remote_addr',
                'is_local': is_local
            }
        })
        
    except Exception as e:
        logger.error(f'获取客户端IP失败: {e}')
        return jsonify({
            'code': -1,
            'msg': f'获取IP失败: {str(e)}'
        }), 500


# ========== 数据统计API ==========
from datetime import datetime, timedelta


@visitor_bp.route('/stats/source', methods=['GET'])
def get_source_stats():
    """获取访问来源统计"""
    try:
        days = request.args.get('days', 7, type=int)
        start_date = datetime.now() - timedelta(days=days)
        
        # 这里返回模拟数据，实际应该从Visitor表的from_url字段统计
        # TODO: 从数据库统计实际来源数据
        
        return jsonify({
            'code': 0,
            'data': {
                'labels': ['PC网页', '移动网页', 'APP', '小程序', '其他'],
                'values': [45, 30, 15, 8, 2]
            }
        })
        
    except Exception as e:
        logger.error(f'获取来源统计失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@visitor_bp.route('/stats/device', methods=['GET'])
def get_device_stats():
    """获取设备统计"""
    try:
        days = request.args.get('days', 7, type=int)
        start_date = datetime.now() - timedelta(days=days)
        
        # 这里返回模拟数据，实际应该从Visitor表的user_agent字段解析统计
        # TODO: 从数据库统计实际设备数据
        
        return jsonify({
            'code': 0,
            'data': {
                'labels': ['PC', '移动端', '平板'],
                'values': [55, 40, 5]
            }
        })
        
    except Exception as e:
        logger.error(f'获取设备统计失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


# ========== 常见问题API ==========
@visitor_bp.route('/greeting', methods=['GET'])
def get_greeting():
    """获取问候语"""
    try:
        business_id = request.args.get('business_id', 1, type=int)
        
        # 从系统设置中获取问候语
        from mod.mysql.models import SystemSetting
        setting = SystemSetting.query.filter_by(business_id=business_id).first()
        
        if setting and setting.greeting_message:
            return jsonify({
                'code': 0,
                'data': {
                    'greeting': setting.greeting_message
                }
            })
        
        # 返回默认问候语
        return jsonify({
            'code': 0,
            'data': {
                'greeting': '您好！欢迎咨询，我是智能助手，很高兴为您服务！'
            }
        })
        
    except Exception as e:
        logger.error(f"获取问候语失败: {str(e)}")
        return jsonify({'code': 5000, 'msg': '系统错误'}), 500


@visitor_bp.route('/faq', methods=['GET'])
@PerformanceMonitor.monitor_api(threshold=0.5)  # 性能优化：监控慢接口
def get_faq():
    """获取常见问题列表（带缓存）"""
    try:
        business_id = request.args.get('business_id', 1, type=int)
        limit = request.args.get('limit', 6, type=int)
        
        # 性能优化：使用缓存获取FAQ列表
        faq_list = FAQCache.get_faq_list(business_id, limit)
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {
                'faqs': faq_list
            }
        })
        
    except Exception as e:
        logger.error(f'获取常见问题失败: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'code': -1, 'msg': str(e)}), 500


@visitor_bp.route('/statistics', methods=['GET'])
def get_visitor_statistics():
    """获取访客统计数据"""
    try:
        from datetime import datetime, timedelta
        from sqlalchemy import func
        
        # 获取查询天数参数
        days = request.args.get('days', 7, type=int)
        business_id = request.args.get('business_id', 1, type=int)
        
        # 计算时间范围
        start_date = datetime.now() - timedelta(days=days)
        
        # 总访客数
        total_visitors = Visitor.query.filter_by(business_id=business_id).count()
        
        # 在线访客数（有正常状态的队列记录）
        online_visitors = db.session.query(func.count(func.distinct(Queue.visitor_id))).filter(
            Queue.business_id == business_id,
            Queue.state == 'normal'
        ).scalar() or 0
        
        # 新访客数（指定天数内创建的）
        new_visitors = Visitor.query.filter(
            Visitor.business_id == business_id,
            Visitor.created_at >= start_date
        ).count()
        
        # 回访访客数（login_times > 1）
        returning_visitors = Visitor.query.filter(
            Visitor.business_id == business_id,
            Visitor.login_times > 1
        ).count()
        
        # 黑名单数量
        blacklist_count = Queue.query.filter_by(
            business_id=business_id,
            state='blacklist'
        ).count()
        
        return jsonify({
            'code': 0,
            'msg': '获取成功',
            'data': {
                'total_visitors': total_visitors,
                'online_visitors': online_visitors,
                'new_visitors': new_visitors,
                'returning_visitors': returning_visitors,
                'blacklist_count': blacklist_count
            }
        })
        
    except Exception as e:
        logger.error(f'获取访客统计失败: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'code': -1, 'msg': str(e)}), 500


@visitor_bp.route('/update/<visitor_id>', methods=['PUT'])
@login_required
def update_visitor(visitor_id):
    """更新访客信息"""
    try:
        business_id = getattr(current_user, 'business_id', 1)
        
        visitor = Visitor.query.filter_by(
            visitor_id=visitor_id,
            business_id=business_id
        ).first()
        
        if not visitor:
            return jsonify({'code': -1, 'msg': '访客不存在'}), 404
        
        data = request.get_json()
        
        # 更新字段
        if 'name' in data:
            visitor.name = data['name']
        if 'tel' in data:
            visitor.tel = data['tel']
        if 'connect' in data:
            visitor.connect = data['connect']
        if 'tags' in data:
            # tags字段是字符串类型，存储逗号分隔的标签
            tags_str = data['tags'].strip()
            # 清理并规范化标签字符串
            if tags_str:
                tags_list = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
                visitor.tags = ','.join(tags_list)
            else:
                visitor.tags = ''
        if 'group_id' in data:
            visitor.group_id = data['group_id']
        if 'comment' in data:
            visitor.comment = data['comment']
        
        visitor.updated_at = datetime.now()
        db.session.commit()
        
        logger.info(f"更新访客信息: {visitor_id}")
        
        return jsonify({
            'code': 0,
            'msg': '更新成功'
        })
        
    except Exception as e:
        logger.error(f'更新访客失败: {e}')
        db.session.rollback()
        return jsonify({'code': -1, 'msg': str(e)}), 500


@visitor_bp.route('/group/list', methods=['GET'])
@login_required
def get_group_list():
    """获取访客分组列表"""
    try:
        # 暂时返回空列表，后续可以扩展分组功能
        return jsonify({
            'code': 0,
            'msg': '获取成功',
            'data': []
        })
    except Exception as e:
        logger.error(f'获取分组列表失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@visitor_bp.route('/detail/<visitor_id>', methods=['GET'])
@login_required
def get_visitor_detail(visitor_id):
    """获取访客详情"""
    try:
        business_id = getattr(current_user, 'business_id', 1)
        
        visitor_detail = VisitorService.get_visitor_detail(visitor_id, business_id)
        
        if not visitor_detail:
            return jsonify({'code': -1, 'msg': '访客不存在'}), 404
        
        # 检查黑名单状态
        from mod.mysql.ModuleClass.QueueServiceClass import QueueService
        blacklist_status = QueueService.check_blacklist_status(visitor_id)
        visitor_detail['is_blacklisted'] = blacklist_status['is_blacklisted']
        if blacklist_status['is_blacklisted']:
            visitor_detail['blacklist_time'] = blacklist_status.get('blacklist_time', '')
        
        return jsonify({
            'code': 0,
            'msg': '获取成功',
            'data': visitor_detail
        })
        
    except Exception as e:
        logger.error(f'获取访客详情失败: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'code': -1, 'msg': str(e)}), 500


@visitor_bp.route('/blacklist/<visitor_id>', methods=['POST'])
@login_required
def toggle_blacklist(visitor_id):
    """切换访客黑名单状态"""
    try:
        business_id = getattr(current_user, 'business_id', 1)
        service_id = getattr(current_user, 'service_id', None)
        
        if not service_id:
            return jsonify({'code': -1, 'msg': '无效的客服ID'}), 403
        
        data = request.get_json() or {}
        is_blacklist = data.get('is_blacklist', 0)
        
        from mod.mysql.ModuleClass.QueueServiceClass import QueueService
        
        if is_blacklist == 1:
            # 添加到黑名单
            reason = data.get('reason', '违规操作')
            success = QueueService.add_to_blacklist(visitor_id, service_id, reason)
            
            if success:
                logger.info(f"访客 {visitor_id} 被客服 {service_id} 加入黑名单，原因：{reason}")
                return jsonify({
                    'code': 0,
                    'msg': '已加入黑名单'
                })
            else:
                return jsonify({'code': -1, 'msg': '添加黑名单失败'}), 500
        else:
            # 移出黑名单
            success = QueueService.remove_from_blacklist(visitor_id)
            
            if success:
                logger.info(f"访客 {visitor_id} 被移出黑名单")
                return jsonify({
                    'code': 0,
                    'msg': '已移出黑名单'
                })
            else:
                return jsonify({'code': -1, 'msg': '移出黑名单失败'}), 500
        
    except Exception as e:
        logger.error(f'切换黑名单状态失败: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'code': -1, 'msg': str(e)}), 500
