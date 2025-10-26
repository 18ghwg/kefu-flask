"""
SocketIO 事件处理
处理WebSocket实时通信事件
"""
from flask import request, session
from flask_socketio import emit, join_room, leave_room, rooms
from exts import socketio, db, app, redis_client
from mod.mysql.models import Service, Visitor, Chat, Queue, SystemSetting
from mod.mysql.ModuleClass import ip_location_service
from mod.mysql.ModuleClass.RobotServiceClass import RobotService
from mod.utils.security_filter import SecurityFilter, sanitize_message
from sqlalchemy import func, and_  # ✅ 添加SQL函数导入
from datetime import datetime, timedelta
from threading import Thread
import json
import log

logger = log.get_logger(__name__)


def strip_html_tags_for_preview(text):
    """
    移除HTML标签，保留纯文本（用于消息预览）
    注意：这不会修改数据库中的原始消息，只是在Socket推送时过滤显示
    """
    import re
    if not text:
        return ''
    # 移除所有HTML标签
    clean = re.sub(r'<[^>]+>', '', text)
    # 移除多余空格
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


# 在线用户字典 {user_id: {'sid': session_id, 'type': 'service/visitor', 'room': room_id}}
# 🆕 改为支持多连接：{user_id: {'sids': [sid1, sid2], 'type': 'service/visitor', ...}}
online_users = {}

# IP位置缓存（5分钟过期）{ip: {'data': {...}, 'time': datetime}}
ip_location_cache = {}

# 队列服务实例（延迟导入，避免循环导入）
queue_service = None

def get_queue_service():
    """获取队列服务实例"""
    global queue_service
    if queue_service is None:
        from app.services.queue_service import QueueService
        queue_service = QueueService()
    return queue_service


def get_location_with_cache(ip_address):
    """
    带缓存的IP地理位置查询
    
    Args:
        ip_address: IP地址
        
    Returns:
        dict: 位置信息
    """
    global ip_location_cache
    
    # 检查缓存
    now = datetime.now()
    if ip_address in ip_location_cache:
        cached = ip_location_cache[ip_address]
        # 缓存5分钟内有效
        if now - cached['time'] < timedelta(minutes=5):
            logger.debug(f"IP位置缓存命中: {ip_address}")
            return cached['data']
    
    # 缓存未命中，执行查询
    location_info = ip_location_service.get_location(ip_address)
    
    # 存入缓存
    ip_location_cache[ip_address] = {
        'data': location_info,
        'time': now
    }
    
    # 清理过期缓存（超过100条时清理）
    if len(ip_location_cache) > 100:
        expired_ips = [
            ip for ip, cached in ip_location_cache.items()
            if now - cached['time'] > timedelta(minutes=5)
        ]
        for ip in expired_ips:
            del ip_location_cache[ip]
        logger.info(f"清理过期IP缓存: {len(expired_ips)}条")
    
    return location_info


@socketio.on('connect')
def handle_connect():
    """客户端连接事件"""
    sid = request.sid
    logger.info(f"Client connected: {sid}")
    emit('connect_response', {'status': 'connected', 'sid': sid})


@socketio.on('disconnect')
def handle_disconnect():
    """客户端断开连接事件（支持多连接）"""
    sid = request.sid
    
    # 查找并移除离线用户
    user_id = None
    user_type = None
    
    for uid, info in list(online_users.items()):
        # 🆕 支持sids列表（多连接）
        if 'sids' in info:
            if sid in info['sids']:
                user_id = uid
                user_type = info['type']
                # 从列表中移除这个sid
                info['sids'].remove(sid)
                
                # 如果还有其他连接，保留该用户
                if len(info['sids']) > 0:
                    logger.info(f"User {user_type}_{uid} 断开一个连接 (剩余{len(info['sids'])}个连接)")
                    return  # 还有其他连接，不删除用户
                else:
                    # 所有连接都断开了，删除该用户
                    del online_users[user_id]
                    logger.info(f"User {user_type}_{uid} 所有连接已断开，离线")
                    
                    # ✅ 如果是客服或管理员，更新数据库状态并广播统计更新
                    if user_type in ['service', 'admin']:
                        try:
                            service_id = info.get('service_id')
                            business_id = info.get('business_id', 1)
                            if service_id:
                                service = Service.query.get(service_id)
                                if service:
                                    service.state = 'offline'
                                    # ✅ 不要清零计数！保持实际的队列数量
                                    # 管理员的计数应该始终为0，普通客服保持实际队列数
                                    if service.level in ['super_manager', 'manager']:
                                        service.current_chat_count = 0
                                    # 普通客服保持当前计数不变，等待重新上线或转接
                                    
                                    db.session.commit()
                                    logger.info(f"✅ 客服{service_id}离线，状态已更新")
                                    
                                    # ⚡ 广播统计更新（客服数量变化）
                                    broadcast_statistics_update(business_id)
                        except Exception as e:
                            logger.error(f"更新客服离线状态失败: {e}")
                    
                    # 如果是访客，关闭会话并减少对应客服的接待计数
                    elif user_type == 'visitor':
                        try:
                            visitor_id = info.get('visitor_id')
                            if visitor_id:
                                # 查找访客的队列
                                queue = Queue.query.filter_by(
                                    visitor_id=visitor_id,
                                    state='normal'
                                ).first()
                                
                                if queue:
                                    # 1. 关闭会话（访客离线）
                                    queue.state = 'complete'  # 使用complete而不是closed
                                    queue.updated_at = datetime.now()
                                    db.session.commit()
                                    logger.info(f"🔒 访客{visitor_id}离线，会话已自动关闭")
                                    
                                    # 2. 减少客服接待计数
                                    if queue.service_id and queue.service_id > 0:
                                        # ✅ 使用统一的接待数管理器
                                        from mod.mysql.ModuleClass.ServiceWorkloadManager import workload_manager
                                        workload_manager.decrement_workload(
                                            queue.service_id,
                                            f"访客离线: {visitor_id}"
                                        )
                                        logger.info(f"✅ 访客{visitor_id}离线，客服{queue.service_id}接待数已减少")
                                        
                                        # 3. 广播统计更新
                                        business_id = queue.business_id
                                        broadcast_statistics_update(business_id)
                                        
                                        # 4. 通知客服访客已离线
                                        socketio.emit('visitor_offline', {
                                            'visitor_id': visitor_id,
                                            'message': '访客已离线，会话自动关闭',
                                            'timestamp': datetime.now().isoformat()
                                        }, room='service_room')
                                        
                        except Exception as e:
                            logger.error(f"访客离线时处理会话失败: {e}")
                            import traceback
                            logger.error(traceback.format_exc())
                break
        # 兼容旧格式（单个sid）
        elif info.get('sid') == sid:
            user_id = uid
            user_type = info['type']
            del online_users[user_id]
            logger.info(f"User {user_type}_{user_id} disconnected (旧格式)")
            break
    
    if user_id and user_type:
        # 通知其他用户该用户离线
        emit('user_offline', {
            'user_id': user_id,
            'user_type': user_type
        }, broadcast=True)


@socketio.on('visitor_join')
def handle_visitor_join(data):
    """
    访客加入
    data: {
        'visitor_id': 访客ID,
        'visitor_name': 访客名称,
        'avatar': 头像
    }
    """
    try:
        visitor_id = data.get('visitor_id')
        visitor_name = data.get('visitor_name', '访客')
        avatar = data.get('avatar', '👤')
        sid = request.sid
        business_id = data.get('business_id', 1)
        special = data.get('special', '')  # 🆕 专属客服ID
        
        # 获取设备信息和访问信息
        device_info = data.get('device_info', {})
        visit_info = data.get('visit_info', {})
        
        # 获取真实IPv4地址（考虑多种来源，优先IPv4）
        def extract_ipv4(ip_str):
            """从IP字符串中提取IPv4地址，过滤IPv6"""
            if not ip_str:
                return None
            # 如果是IPv6地址（包含冒号），返回None
            if ':' in ip_str and '.' not in ip_str:
                return None
            # 如果是IPv4地址，返回
            import re
            ipv4_pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            match = re.search(ipv4_pattern, ip_str)
            if match:
                return match.group(1)
            return None
        
        real_ip = None
        
        # 1. 尝试从HTTP头获取（可能包含多个IP）
        for header in ['X-Forwarded-For', 'X-Real-IP', 'CF-Connecting-IP']:
            ip_header = request.headers.get(header)
            if ip_header:
                # X-Forwarded-For可能包含多个IP，逐个尝试找IPv4
                if ',' in ip_header:
                    for ip_part in ip_header.split(','):
                        ipv4 = extract_ipv4(ip_part.strip())
                        if ipv4 and ipv4 != '127.0.0.1':
                            real_ip = ipv4
                            logger.info(f"从{header}获取IPv4: {real_ip}")
                            break
                else:
                    ipv4 = extract_ipv4(ip_header)
                    if ipv4 and ipv4 != '127.0.0.1':
                        real_ip = ipv4
                        logger.info(f"从{header}获取IPv4: {real_ip}")
                        break
            
            if real_ip:
                break
        
        # 2. 尝试从environ获取
        if not real_ip:
            from flask import request as flask_request
            environ_ip = flask_request.environ.get('REMOTE_ADDR')
            ipv4 = extract_ipv4(environ_ip)
            if ipv4 and ipv4 != '127.0.0.1':
                real_ip = ipv4
                logger.info(f"从environ获取IPv4: {real_ip}")
        
        # 3. 使用remote_addr
        if not real_ip:
            remote_addr = request.remote_addr
            ipv4 = extract_ipv4(remote_addr)
            if ipv4 and ipv4 != '127.0.0.1':
                real_ip = ipv4
                logger.info(f"从remote_addr获取IPv4: {real_ip}")
        
        # 4. 开发环境：使用客户端传递的IP
        if not real_ip:
            client_ip = device_info.get('client_ip')
            if client_ip:
                ipv4 = extract_ipv4(client_ip)
                if ipv4 and ipv4 != '127.0.0.1':
                    real_ip = ipv4
                    logger.info(f"使用客户端传递的IPv4: {real_ip}")
        
        # 5. 最终默认值
        if not real_ip:
            real_ip = '127.0.0.1 (本地)'
            logger.info("开发环境，IP为本地地址")
        
        # ⚡ 不要在这里同步解析IP位置，使用默认值，后续异步更新
        location_info = {
            'formatted': '定位中...',
            'country': '',
            'province': '',
            'city': ''
        }
        
        # 记录在线用户（保存完整信息，支持多连接）
        user_key = f'visitor_{visitor_id}'
        
        # 🆕 支持多连接
        if user_key in online_users:
            # 已存在，添加新的sid
            if 'sids' not in online_users[user_key]:
                # 兼容旧格式
                old_sid = online_users[user_key].get('sid')
                online_users[user_key]['sids'] = [old_sid] if old_sid else []
                if 'sid' in online_users[user_key]:
                    del online_users[user_key]['sid']
            
            if sid not in online_users[user_key]['sids']:
                online_users[user_key]['sids'].append(sid)
                logger.info(f"Visitor {visitor_id} 添加新连接 (共{len(online_users[user_key]['sids'])}个连接)")
            
            # 更新其他信息（使用最新的）
            online_users[user_key].update({
                'visitor_name': visitor_name,
                'name': visitor_name,
                'avatar': avatar,
                'ip': real_ip,
                'location': location_info.get('formatted', '未知'),
                'country': location_info.get('country', ''),
                'province': location_info.get('province', ''),
                'city': location_info.get('city', ''),
                'browser': device_info.get('browser', 'Unknown'),
                'os': device_info.get('os', 'Unknown'),
                'device': device_info.get('device', 'Desktop'),
                'screen_resolution': device_info.get('screen_resolution', ''),
                'visit_count': visit_info.get('visit_count', 1),
                'first_visit': visit_info.get('first_visit', '')
            })
        else:
            # 不存在，创建新entry
            online_users[user_key] = {
                'sids': [sid],  # 🆕 使用列表
                'type': 'visitor',
                'visitor_id': visitor_id,
                'visitor_name': visitor_name,
                'name': visitor_name,
                'avatar': avatar,
                'ip': real_ip,
                'location': location_info.get('formatted', '未知'),
                'country': location_info.get('country', ''),
                'province': location_info.get('province', ''),
                'city': location_info.get('city', ''),
                'browser': device_info.get('browser', 'Unknown'),
                'os': device_info.get('os', 'Unknown'),
                'device': device_info.get('device', 'Desktop'),
                'screen_resolution': device_info.get('screen_resolution', ''),
                'visit_count': visit_info.get('visit_count', 1),
                'first_visit': visit_info.get('first_visit', '')
            }
            logger.info(f"Visitor {visitor_id} joined (新用户)")
        
        # ⚡ 修复：visitor_id本身已包含'visitor_'前缀，直接使用
        # 访客前端生成格式：visitor_${timestamp}_${random}
        room = visitor_id if visitor_id.startswith('visitor_') else f'visitor_{visitor_id}'
        join_room(room)
        
        # ⚡ 在异步函数外先获取request相关数据（避免在异步线程中访问request对象）
        try:
            referrer_url = request.referrer or ''
        except:
            referrer_url = ''
        
        # ⚡ 数据库操作异步化（不阻塞响应）
        def async_save_visitor():
            """后台异步保存访客信息"""
            try:
                with app.app_context():
                    # 保存或更新访客信息到数据库
                    visitor = Visitor.query.filter_by(visitor_id=visitor_id, business_id=business_id).first()
                    
                    if not visitor:
                        # 新访客
                        visitor = Visitor(
                            visitor_id=visitor_id,
                            visitor_name=visitor_name,
                            business_id=business_id,
                            channel='web',
                            avatar=avatar,
                            ip=real_ip,
                            from_url=device_info.get('from_url', referrer_url),  # 使用预先保存的referrer_url
                            user_agent=device_info.get('user_agent', ''),
                            browser=device_info.get('browser', ''),
                            os=device_info.get('os', ''),
                            device=device_info.get('device', 'Desktop'),
                            referrer=device_info.get('referrer', ''),
                            login_times=visit_info.get('visit_count', 1),
                            extends=json.dumps({
                                'device_fingerprint': visit_info.get('device_fingerprint', ''),
                                'screen_resolution': device_info.get('screen_resolution', ''),
                                'language': device_info.get('language', ''),
                                'first_visit': visit_info.get('first_visit', ''),
                                'last_visit': visit_info.get('last_visit', '')
                            })
                        )
                        db.session.add(visitor)
                    else:
                        # 老访客，更新信息
                        visitor.visitor_name = visitor_name
                        visitor.ip = real_ip
                        visitor.login_times = visit_info.get('visit_count', visitor.login_times + 1)
                        visitor.user_agent = device_info.get('user_agent', visitor.user_agent)
                        visitor.browser = device_info.get('browser', visitor.browser)
                        visitor.os = device_info.get('os', visitor.os)
                        visitor.device = device_info.get('device', visitor.device)
                        visitor.from_url = device_info.get('from_url', visitor.from_url)
                        
                        # 更新扩展信息
                        try:
                            extends = json.loads(visitor.extends) if visitor.extends else {}
                        except:
                            extends = {}
                        extends.update({
                            'screen_resolution': device_info.get('screen_resolution', ''),
                            'language': device_info.get('language', ''),
                            'last_visit': visit_info.get('last_visit', datetime.now().isoformat())
                        })
                        visitor.extends = json.dumps(extends)
                    
                    db.session.commit()
                    logger.info(f"✅ 访客信息已保存: {visitor_id}")
                    
            except Exception as e:
                logger.error(f"❌ 异步保存访客信息失败: {visitor_id}, 错误: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        # ⚠️ 已禁用在线IP查询（性能优化）
        # 仅保留基本的本地IP识别，不调用外部API
        def async_resolve_location():
            """后台异步保存IP基本信息（不调用在线API）"""
            try:
                # 简单的本地IP识别
                if real_ip.startswith('127.') or real_ip == 'localhost':
                    location_text = '本地'
                elif real_ip.startswith('192.168.') or real_ip.startswith('10.') or real_ip.startswith('172.'):
                    location_text = '内网'
                else:
                    location_text = '未知'  # 外网IP不查询，直接显示未知
                
                # 更新online_users中的位置信息
                if user_key in online_users:
                    online_users[user_key]['location'] = location_text
                
                logger.debug(f"访客{visitor_id}位置识别: {real_ip} -> {location_text}")
                
            except Exception as e:
                logger.error(f"❌ IP基本识别失败: {visitor_id}, {real_ip}, 错误: {e}")
        
        # ⚡ 启动后台线程（数据库保存 + IP解析，不等待完成）
        Thread(target=async_save_visitor, daemon=True).start()
        Thread(target=async_resolve_location, daemon=True).start()
        
        logger.info(f"⚡ Visitor {visitor_id} 快速加入 - IP: {real_ip}, Browser: {device_info.get('browser')}, 访问次数: {visit_info.get('visit_count', 1)}")
        
        # 🚫 检查访客是否在黑名单中
        blacklist_check = Queue.query.filter_by(
            visitor_id=visitor_id,
            state='blacklist'
        ).first()
        
        if blacklist_check:
            logger.info(f"🚫 访客 {visitor_id} 在黑名单中，拒绝加入")
            # 发送黑名单提示给访客
            emit('blacklisted', {
                'message': '您已被限制访问，如有疑问请联系管理员'
            }, room=request.sid)
            return
        
        # 🆕 检查并创建Queue记录（如果不存在）
        queue_info = None
        try:
            existing_queue = Queue.query.filter_by(
                visitor_id=visitor_id,
                business_id=business_id,
                state='normal'  # 查找进行中的队列
            ).first()
            
            if not existing_queue:
                # 没有进行中的队列，创建新队列
                # 🆕 优先使用special参数指定的客服
                available_service = None
                exclusive_service_id = None
                is_exclusive = False
                
                if special:
                    # 验证指定的客服是否存在
                    try:
                        special_service_id = int(special)
                        special_service = Service.query.filter_by(
                            service_id=special_service_id,
                            business_id=business_id
                        ).first()
                        
                        if special_service:
                            exclusive_service_id = special_service_id
                            is_exclusive = True
                            
                            # 检查专属客服是否在线
                            if special_service.state == 'online':
                                available_service = special_service
                                logger.info(f"✅ 专属客服在线，立即分配: service_id={special_service_id}")
                            else:
                                logger.info(f"⚠️ 专属客服离线，访客等待专属客服上线: service_id={special_service_id}")
                                # 专属会话：即使客服离线也不分配给其他客服
                        else:
                            logger.warning(f"⚠️ 指定的专属客服不存在: service_id={special_service_id}")
                    except (ValueError, TypeError):
                        logger.warning(f"⚠️ 无效的special参数: {special}")
                
                # 如果不是专属会话，且没有分配到客服，则使用智能分配（优先普通客服）
                if not is_exclusive and not available_service:
                    from mod.mysql.ModuleClass.AssignmentServiceClass import assignment_service
                    available_service = assignment_service._find_available_service(business_id)
                
                service_id = available_service.service_id if available_service else None  # ✅ 未分配时使用 NULL
                
                new_queue = Queue(
                    visitor_id=visitor_id,
                    business_id=business_id,
                    service_id=service_id,
                    exclusive_service_id=exclusive_service_id,  # 专属客服ID
                    is_exclusive=1 if is_exclusive else 0,      # 是否专属会话
                    state='normal',  # 正常状态
                    priority=0,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    last_message_time=datetime.now()
                )
                db.session.add(new_queue)
                db.session.commit()
                
                queue_info = {
                    'queue_id': new_queue.qid,
                    'service_id': service_id,
                    'service_name': available_service.nick_name if available_service else '暂无客服'
                }
                
                # ========== 更新客服接待计数（管理员不计入）==========
                if service_id and service_id > 0:
                    try:
                        service = Service.query.get(service_id)
                        if service:
                            # 只有普通客服才计入接待数，管理员不限制
                            if service.level not in ['super_manager', 'manager']:
                                service.current_chat_count = (service.current_chat_count or 0) + 1
                                logger.info(f"✅ 客服{service_id}接待数更新: {service.current_chat_count}/{service.max_concurrent_chats}")
                                
                                # 🔥 实时推送负载变化到客服端
                                for user_key, user_info in list(online_users.items()):
                                    # ✅ 同时检查service和admin
                                    if user_info['type'] in ['service', 'admin'] and user_info.get('service_id') == service_id:
                                        sids = user_info.get('sids', [])
                                        for sid in sids:
                                            socketio.emit('workload_update', {
                                                'current': service.current_chat_count,
                                                'max': service.max_concurrent_chats,
                                                'utilization': round(service.current_chat_count / service.max_concurrent_chats * 100, 0) if service.max_concurrent_chats > 0 else 0
                                            }, room=sid)
                            else:
                                logger.info(f"✅ 管理员{service_id}接待访客（不计入负载）")
                            service.last_assign_time = datetime.now()
                            db.session.commit()
                    except Exception as e:
                        logger.error(f"更新接待计数失败: {e}")
                
                # 如果没有在线客服，发送排队提示
                if not available_service:
                    if is_exclusive:
                        # 专属客服离线，发送专属提示
                        emit('queue_notification', {
                            'message': f'您的专属客服暂时离线，请稍候或留言，客服上线后会第一时间回复您',
                            'is_exclusive': True,
                            'exclusive_service_id': exclusive_service_id
                        }, room=f'visitor_{visitor_id}')
                        logger.info(f"📢 发送专属客服离线提示: visitor={visitor_id}, service={exclusive_service_id}")
                    else:
                        # 普通排队
                        # 获取系统设置中的排队提示
                        settings = SystemSetting.query.filter_by(business_id=business_id).first()
                        queue_text = settings.chat_queue_text if settings else '当前排队人数较多，请稍候'
                        
                        # 计算排队位置（未分配客服的队列数量）
                        queue_position = Queue.query.filter(
                            Queue.business_id == business_id,
                            (Queue.service_id == None) | (Queue.service_id == 0),  # ✅ 兼容旧数据
                            Queue.state == 'normal'
                        ).count()
                        
                        # 发送排队通知到访客
                        emit('queue_notification', {
                            'message': queue_text,
                            'queue_position': queue_position
                        }, room=f'visitor_{visitor_id}')
                        
                        logger.info(f"📢 发送排队提示: visitor={visitor_id}, 位置={queue_position}")
                
                logger.info(f"✅ 创建队列记录: visitor={visitor_id}, queue_id={new_queue.qid}, service={service_id}")
            else:
                # ========== 检查现有队列的客服是否在线，如果离线则重新分配 ==========
                old_service_id = existing_queue.service_id
                need_reassign = False
                
                if old_service_id and old_service_id > 0:
                    # 检查原客服是否在线
                    old_service_online = False
                    for user_key, user_info in online_users.items():
                        # ✅ 同时检查service和admin
                        if (user_info['type'] in ['service', 'admin'] and 
                            user_info.get('service_id') == old_service_id):
                            # 检查是否有有效连接
                            if ('sids' in user_info and len(user_info['sids']) > 0) or \
                               ('sid' in user_info and user_info['sid']):
                                old_service_online = True
                                break
                    
                    if not old_service_online:
                        logger.info(f"⚠️ 原客服{old_service_id}已离线，重新分配访客{visitor_id}")
                        need_reassign = True
                else:
                    # 原来没有分配客服（service_id为NULL或0），尝试分配
                    need_reassign = True
                
                if need_reassign:
                    # 使用智能分配重新分配（优先普通客服）
                    from mod.mysql.ModuleClass.AssignmentServiceClass import assignment_service
                    available_service = assignment_service._find_available_service(business_id)
                    
                    if available_service:
                        # 更新队列的客服分配
                        existing_queue.service_id = available_service.service_id
                        existing_queue.updated_at = datetime.now()
                        existing_queue.last_message_time = datetime.now()
                        db.session.commit()
                        
                        # 更新接待计数（管理员不计入）
                        if available_service.level not in ['super_manager', 'manager']:
                            available_service.current_chat_count = (available_service.current_chat_count or 0) + 1
                        available_service.last_assign_time = datetime.now()
                        db.session.commit()
                        
                        logger.info(f"✅ 访客{visitor_id}重新分配给客服{available_service.service_id}")
                        
                        queue_info = {
                            'queue_id': existing_queue.qid,
                            'service_id': available_service.service_id,
                            'service_name': available_service.nick_name
                        }
                    else:
                        # 没有在线客服
                        existing_queue.service_id = None  # ✅ 使用 NULL 表示未分配，避免外键约束冲突
                        db.session.commit()
                        logger.info(f"⚠️ 没有在线客服，访客{visitor_id}进入等待")
                        
                        queue_info = {
                            'queue_id': existing_queue.qid,
                            'service_id': None,  # ✅ 返回 None 表示未分配
                            'service_name': None  # ✅ 无客服时为None
                        }
                else:
                    # 原客服仍在线，继续使用
                    # 获取分配的客服名称
                    assigned_service_name = None
                    if existing_queue.service_id and existing_queue.service_id > 0:
                        assigned_service = Service.query.get(existing_queue.service_id)
                        if assigned_service:
                            assigned_service_name = assigned_service.nick_name
                    
                    queue_info = {
                        'queue_id': existing_queue.qid,
                        'service_id': existing_queue.service_id,
                        'service_name': assigned_service_name  # ✅ 添加客服名称
                    }
                    logger.info(f"♻️ 使用现有队列: visitor={visitor_id}, queue_id={existing_queue.qid}, service={existing_queue.service_id}, service_name={assigned_service_name}")
                
        except Exception as e:
            logger.error(f"❌ 创建/查询队列失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        # ⚡ 最后一条消息也异步查询（避免阻塞）
        last_msg_content = ''
        last_msg_time = ''
        # 暂不查询，后续如果需要可以异步更新
        
        # 构建完整的访客信息
        visitor_full_info = {
            'visitor_id': visitor_id,
            'visitor_name': visitor_name,
            'avatar': avatar,
            'ip': real_ip,
            'location': location_info.get('formatted', '未知'),
            'country': location_info.get('country', ''),
            'province': location_info.get('province', ''),
            'city': location_info.get('city', ''),
            'browser': device_info.get('browser', 'Unknown'),
            'os': device_info.get('os', 'Unknown'),
            'device': device_info.get('device', 'Desktop'),
            'screen_resolution': device_info.get('screen_resolution', ''),
            'visit_count': visit_info.get('visit_count', 1),
            'first_visit': visit_info.get('first_visit', ''),
            'last_message': last_msg_content,  # 最后一条消息
            'last_message_time': last_msg_time,  # 最后一条消息时间
            'timestamp': datetime.now().isoformat()
        }
        
        # 查询在线客服（优化：直接在join_success中返回，减少一次请求）
        # ✅ 修复多worker同步问题：从数据库查询而不是从online_users内存字典
        # 这样确保所有worker看到的在线状态是一致的（数据库是唯一真相来源）
        online_services = []
        try:
            # 从数据库查询state='online'的客服
            online_service_records = Service.query.filter_by(
                business_id=business_id,
                state='online'
            ).all()
            
            for service in online_service_records:
                online_services.append({
                    'service_id': service.service_id,
                    'name': service.nick_name
                })
            
            logger.info(f"📊 visitor_join返回在线客服数：{len(online_services)}个 (从数据库查询)")
        except Exception as e:
            logger.error(f"查询在线客服失败: {e}")
            # 如果数据库查询失败，降级使用online_users（保持兼容性）
            seen_service_ids = set()
            for user_id, info in online_users.items():
                has_connection = False
                if 'sids' in info and len(info['sids']) > 0:
                    has_connection = True
                elif 'sid' in info and info['sid']:
                    has_connection = True
                
                if info['type'] in ['service', 'admin'] and has_connection and info.get('service_id'):
                    service_id_val = info.get('service_id')
                    if service_id_val not in seen_service_ids:
                        seen_service_ids.add(service_id_val)
                        online_services.append({
                            'service_id': service_id_val,
                            'name': info.get('name')
                        })
            logger.warning(f"⚠️ 数据库查询失败，降级使用online_users，客服数：{len(online_services)}个")
        
        # 返回成功响应（包含在线客服信息 + 队列信息）
        emit('join_success', {
            'status': 'success',
            'message': f'欢迎，{visitor_name}！',
            'visitor_id': visitor_id,
            'room': room,
            'online_services': online_services,           # 直接返回在线客服
            'total_services': len(online_services),       # 在线客服总数
            'queue': queue_info                            # 队列信息
        })
        
        # ========== 智能通知：只通知分配到的客服和管理员 ==========
        assigned_service_id = queue_info.get('service_id') if queue_info else None
        
        # 获取所有在线客服的详细信息（包含level）
        # ✅ 同时检查service和admin
        for user_key, user_info in online_users.items():
            if user_info['type'] in ['service', 'admin']:
                service_id_val = user_info.get('service_id')
                if service_id_val:
                    # 查询客服详细信息
                    service = Service.query.get(service_id_val)
                    if service:
                        # 管理员或分配到的客服才收到通知
                        is_admin = service.level in ['super_manager', 'manager']
                        is_assigned = (assigned_service_id and service_id_val == assigned_service_id)
                        
                        if is_admin or is_assigned:
                            # 获取该客服的所有连接ID
                            sids = user_info.get('sids', [])
                            for sid in sids:
                                socketio.emit('new_visitor', visitor_full_info, room=sid)
                            
                            if is_admin:
                                logger.info(f"📢 通知管理员客服{service_id_val}: 新访客{visitor_id}")
                            else:
                                logger.info(f"📢 通知分配客服{service_id_val}: 新访客{visitor_id}")
        
    except Exception as e:
        logger.error(f"Error in visitor_join: {e}")
        import traceback
        logger.error(traceback.format_exc())
        emit('error', {'message': str(e)})


@socketio.on('service_join')
def handle_service_join(data):
    """
    客服加入（支持同一账号多标签页连接）
    data: {
        'service_id': 客服ID,
        'service_name': 客服名称
    }
    """
    try:
        service_id = data.get('service_id')
        service_name = data.get('service_name', '客服')
        sid = request.sid
        
        # ✅ 验证service_id
        if not service_id:
            logger.error(f"❌ service_join 缺少 service_id, data: {data}")
            emit('error', {'message': '缺少客服ID'})
            return
        
        # ✅ 检查是否已有 admin_join 连接（避免重复统计）
        admin_key = f'admin_{service_id}'
        service_key = f'service_{service_id}'
        
        existing_key = None
        if admin_key in online_users:
            existing_key = admin_key
            logger.info(f"🔗 客服{service_id}进入工作台，已有admin连接，合并到admin记录（避免重复统计）")
        elif service_key in online_users:
            existing_key = service_key
        
        # 🆕 支持多连接：如果已存在，添加新的sid；否则创建新entry
        # 查询客服信息获取权限级别（缓存到 online_users 中）
        service = Service.query.filter_by(service_id=service_id).first()
        if not service:
            logger.warning(f"⚠️ Service {service_id} 不存在于数据库中")
            emit('error', {'message': '客服不存在'})
            return
        
        is_admin = service.level in ['super_manager', 'manager']
        
        if existing_key:
            # 已存在，添加新的sid（如果还没有）
            if 'sids' not in online_users[existing_key]:
                # 兼容旧格式：从单个sid转换为sids列表
                old_sid = online_users[existing_key].get('sid')
                online_users[existing_key]['sids'] = [old_sid] if old_sid else []
                if 'sid' in online_users[existing_key]:
                    del online_users[existing_key]['sid']
            
            if sid not in online_users[existing_key]['sids']:
                online_users[existing_key]['sids'].append(sid)
                logger.info(f"✅ Service {service_id} ({service_name}) 添加新连接 (共{len(online_users[existing_key]['sids'])}个连接)")
            
            # 更新权限级别缓存
            online_users[existing_key]['is_admin'] = is_admin
        else:
            # 不存在，创建新entry（包含权限级别缓存）
            online_users[service_key] = {
                'sids': [sid],  # 🆕 使用列表存储多个sid
                'type': 'service',
                'service_id': service_id,
                'name': service_name,
                'is_admin': is_admin  # ⚡ 缓存权限级别，避免消息推送时查询
            }
            logger.info(f"✅ Service {service_id} ({service_name}) joined (新用户, is_admin={is_admin})")
        
        # 加入客服总房间
        join_room('service_room')
        
        # 更新数据库中的在线状态（添加验证）
        if service_id:
            service = Service.query.filter_by(service_id=service_id).first()
            if service:
                service.state = 'online'
                db.session.commit()
                logger.info(f"✅ Service {service_id} 状态更新为 online")
                
                # ✅ 客服上线时，自动同步接待数（确保数据准确）
                from mod.mysql.ModuleClass.ServiceWorkloadManager import workload_manager
                sync_result = workload_manager.sync_workload(service_id, "客服上线自动同步")
                if sync_result['success']:
                    logger.info(f"📊 客服{service_id}上线，接待数已同步: {sync_result['current_count']}")
            else:
                logger.warning(f"⚠️ Service {service_id} 不存在于数据库中")
        
        # 返回成功响应
        emit('join_success', {
            'status': 'success',
            'message': f'{service_name} 已上线',
            'service_id': service_id
        })
        
        # 通知其他客服（避免重复通知）
        emit('service_online', {
            'service_id': service_id,
            'service_name': service_name,
            'timestamp': datetime.now().isoformat()
        }, room='service_room', broadcast=True, include_self=False)
        
    except Exception as e:
        logger.error(f"Error in service_join: {e}")
        emit('error', {'message': str(e)})


@socketio.on('send_message')
def handle_send_message(data):
    """
    发送消息
    data: {
        'from_id': 发送者ID,
        'from_type': 'visitor' or 'service',
        'to_id': 接收者ID,
        'to_type': 'visitor' or 'service',
        'content': 消息内容,
        'type': 'text' or 'image' or 'file',
        'device_info': {...},  # 访客的设备信息（可选）
    }
    """
    try:
        from_id = data.get('from_id')
        from_type = data.get('from_type')
        from_name = data.get('from_name', '')
        to_id = data.get('to_id')
        to_type = data.get('to_type')
        content = data.get('content')
        msg_type = data.get('msg_type', 'text')
        business_id = data.get('business_id', 1)  # 默认商户ID为1
        
        # ========== 安全过滤：防止SSTI、XSS等攻击 ==========
        # 🛡️ 修复：只对访客和客服手动发送的消息进行HTML转义
        # 机器人消息（from_type='robot'）不过滤，保留HTML格式（如超链接）
        if content and msg_type == 'text' and from_type in ['visitor', 'service']:
            original_content = content
            content = sanitize_message(content, max_length=5000)
            
            # 如果内容被拦截（返回拦截消息），记录并通知用户
            if content == "[消息包含非法内容，已被系统拦截]":
                logger.warning(f"🛡️ 拦截非法消息 - from: {from_id}, type: {from_type}, content: {original_content[:200]}")
                emit('error', {
                    'msg': '您的消息包含不安全内容，已被系统拦截',
                    'timestamp': datetime.now().isoformat()
                }, room=request.sid)
                return
            
            # 如果内容被修改，记录
            if content != original_content:
                logger.info(f"🛡️ 消息已过滤 - from: {from_id}, type: {from_type}, original_length: {len(original_content)}, filtered_length: {len(content)}")
        elif from_type == 'robot':
            logger.debug(f"🤖 机器人消息不过滤，保留HTML格式: {content[:100]}")
        
        # ========== 访客发送消息时，更新设备信息和IP（性能优化：已禁用） ==========
        # ⚡ 性能优化：访客每次发消息都更新IP和地理位置会严重影响性能（每次500ms-2s）
        # IP和设备信息在 visitor_join 时已经更新过，这里不再重复更新
        # 如需重新启用，建议改为：1) 定时任务更新 2) 仅在访客信息变化时才更新
        # 原代码(150行)已禁用，如需查看请查看Git历史
        pass  # ⚡ 已禁用：每次发消息都更新IP会严重阻塞(500ms-2s/消息)
        
        # 处理特殊情况：访客发送给"所有客服"
        actual_service_id = None
        if to_id == 'all' and to_type == 'service':
            # 访客发送给所有客服，尝试获取第一个在线客服
            first_service = Service.query.filter_by(
                business_id=business_id,
                state='online'
            ).first()
            if first_service:
                actual_service_id = first_service.service_id
                to_id = first_service.service_id
            else:
                # 如果没有在线客服，获取任意一个客服
                any_service = Service.query.filter_by(
                    business_id=business_id
                ).first()
                if any_service:
                    actual_service_id = any_service.service_id
                    to_id = any_service.service_id
                else:
                    # 如果没有任何客服，发送错误
                    emit('error', {'message': '当前没有客服在线'})
                    return
        else:
            # 确保ID是整数类型（对于service_id）
            if from_type == 'service':
                from_id = int(from_id) if from_id else None
            if to_type == 'service':
                to_id = int(to_id) if to_id else None
                actual_service_id = to_id
        
        # 保存消息到数据库（字段名修正）
        import time
        
        # 确定visitor_id和service_id
        visitor_id_val = from_id if from_type == 'visitor' else to_id
        
        # ⚡ 重要：提前初始化queue变量（无论from_type是什么，都需要这个变量）
        queue = None
        
        # ✅ 修复service_id获取逻辑
        # 🚫 检查访客是否在黑名单中（仅检查访客发送的消息）
        if from_type == 'visitor':
            blacklist_check = Queue.query.filter_by(
                visitor_id=visitor_id_val,
                state='blacklist'
            ).first()
            
            if blacklist_check:
                logger.info(f"🚫 访客 {visitor_id_val} 在黑名单中，消息已拦截: {content[:30]}...")
                # 直接返回，不保存消息、不转发、不提醒
                emit('message_blocked', {
                    'msg': '您已被限制发送消息',
                    'timestamp': datetime.now().isoformat()
                }, room=request.sid)
                return
        
        if from_type == 'service':
            # ========== 客服发送消息 - 权限检查 ==========
            service_id_val = int(from_id)
            
            # 检查客服是否有权限回复此访客
            try:
                from mod.mysql.ModuleClass.AssignmentServiceClass import assignment_service
                can_reply, reason, assigned_service = assignment_service.check_reply_permission(
                    service_id=service_id_val,
                    visitor_id=visitor_id_val,
                    business_id=business_id
                )
                
                if not can_reply:
                    # 无权限，拒绝发送
                    logger.warning(f"⛔ 客服{service_id_val}无权限回复访客{visitor_id_val}: {reason}")
                    emit('permission_denied', {
                        'msg': reason or '您无权回复此访客',
                        'assigned_service': assigned_service,
                        'timestamp': datetime.now().isoformat()
                    }, room=request.sid)
                    return
                
                logger.info(f"✅ 客服{service_id_val}有权限回复访客{visitor_id_val}")
            except Exception as e:
                logger.error(f"权限检查失败: {str(e)}")
                # 出错时拒绝发送，保险起见
                emit('error', {
                    'msg': '权限验证失败，请刷新页面重试',
                    'timestamp': datetime.now().isoformat()
                }, room=request.sid)
                return
        elif from_type == 'visitor':
            # ========== 访客发送消息 - 检查客服在线状态并自动重新分配 ==========
            service_id_val = 0  # 默认值，确保变量一定有值
            
            # 查询访客的队列记录（queue已在前面初始化为None）
            queue = Queue.query.filter_by(
                visitor_id=visitor_id_val,
                business_id=business_id,
                state='normal'
            ).first()
            logger.info(f"🔍 访客{visitor_id_val}发送消息，队列状态: queue={queue.qid if queue else 'None'}, service_id={queue.service_id if queue else 'N/A'}")
            
            # 输出当前online_users状态（调试用）
            # ✅ 同时统计service和admin
            online_service_ids = [user_info.get('service_id') for user_key, user_info in online_users.items() if user_info['type'] in ['service', 'admin']]
            logger.info(f"📊 当前在线客服ID列表: {online_service_ids}")
            
            if queue and queue.service_id and queue.service_id > 0:
                # 检查当前分配的客服是否在线（同时检查online_users和数据库）
                current_service_online = False
                found_in_memory = False
                has_valid_connection = False
                db_state = None
                
                logger.info(f"🔍 开始检查客服{queue.service_id}在线状态...")
                
                # 1. 先检查online_users（Socket连接状态）
                # ✅ 修复：同时检查type='service'和type='admin'（管理员也是客服）
                for user_key, user_info in online_users.items():
                    if (user_info['type'] in ['service', 'admin'] and 
                        user_info.get('service_id') == queue.service_id):
                        found_in_memory = True
                        logger.info(f"✓ 客服{queue.service_id}在online_users中找到，user_key={user_key}, type={user_info['type']}")
                        
                        # 检查是否有有效连接
                        sids_list = user_info.get('sids', [])
                        sid_single = user_info.get('sid')
                        logger.info(f"  - sids列表: {sids_list}, 单sid: {sid_single}")
                        
                        if (sids_list and len(sids_list) > 0) or sid_single:
                            has_valid_connection = True
                            current_service_online = True
                            logger.info(f"✓ 客服{queue.service_id}有有效Socket连接")
                            break
                        else:
                            logger.warning(f"✗ 客服{queue.service_id}在online_users中但无有效Socket连接")
                
                if not found_in_memory:
                    logger.warning(f"✗ 客服{queue.service_id}不在online_users中")
                
                # 2. 如果online_users中显示在线，还要检查数据库状态（双重验证）
                if current_service_online:
                    db_service = Service.query.get(queue.service_id)
                    if db_service:
                        db_state = db_service.state
                        logger.info(f"  - 数据库中客服{queue.service_id}状态: {db_state}")
                        
                        if db_service.state != 'online':
                            logger.warning(f"⚠️ 客服{queue.service_id}在online_users中但数据库显示{db_state}，判定为离线")
                            current_service_online = False
                    else:
                        logger.error(f"✗ 数据库中未找到客服{queue.service_id}记录")
                        current_service_online = False
                
                # 3. 最终判定结果
                logger.info(f"{'✅' if current_service_online else '❌'} 客服{queue.service_id}在线判定结果: {current_service_online} (内存:{found_in_memory}, 连接:{has_valid_connection}, 数据库:{db_state})")
                
                if not current_service_online:
                    # 当前客服离线，使用智能分配重新分配
                    logger.warning(f"⚠️ 访客{visitor_id_val}发送消息时，当前客服{queue.service_id}已离线，开始重新分配...")
                    
                    try:
                        # 使用智能分配服务
                        from mod.mysql.ModuleClass.AssignmentServiceClass import assignment_service
                        
                        # 检查是否是专属会话
                        if queue.is_exclusive and queue.exclusive_service_id:
                            # 专属会话不重新分配，保持原客服ID
                            logger.info(f"📌 访客{visitor_id_val}是专属会话，保持客服{queue.exclusive_service_id}")
                            service_id_val = queue.service_id
                        else:
                            # 查找可用客服（优先普通客服 -> 管理员 -> 机器人）
                            new_service = assignment_service._find_available_service(business_id)
                            
                            if new_service:
                                # 有可用的人工客服，更新队列分配
                                old_service_id = queue.service_id
                                queue.service_id = new_service.service_id
                                queue.updated_at = datetime.now()
                                
                                db.session.commit()
                                
                                # ✅ 使用统一的接待数管理器进行转移
                                from mod.mysql.ModuleClass.ServiceWorkloadManager import workload_manager
                                workload_manager.transfer_workload(
                                    old_service_id,
                                    new_service.service_id,
                                    f"访客消息重新分配: {visitor_id_val}"
                                )
                                
                                service_id_val = new_service.service_id
                                logger.info(f"✅ 访客{visitor_id_val}自动重新分配: {old_service_id} -> {new_service.service_id} ({new_service.nick_name})")
                                
                                # 🔔 通知访客：客服已变更
                                # ⚡ 修复：visitor_id_val已包含'visitor_'前缀，避免重复
                                visitor_room = visitor_id_val if visitor_id_val.startswith('visitor_') else f'visitor_{visitor_id_val}'
                                emit('service_changed', {
                                    'service_id': new_service.service_id,
                                    'service_name': new_service.nick_name,
                                    'message': f'客服已切换为 {new_service.nick_name}'
                                }, room=visitor_room)
                                logger.info(f"📢 已通知访客{visitor_id_val}：客服变更为{new_service.nick_name}")
                                
                                # 🔔 广播给所有在线客服：访客分配状态更新
                                try:
                                    # 获取访客完整信息用于广播
                                    visitor_obj = Visitor.query.get(visitor_id_val)
                                    visitor_info = visitor_obj.to_dict() if visitor_obj else {'visitor_id': visitor_id_val, 'visitor_name': from_name}
                                    
                                    # ✅ 同时通知service和admin
                                    for user_key, user_info in online_users.items():
                                        if user_info['type'] in ['service', 'admin']:
                                            current_service_id = user_info.get('service_id')
                                            sids = user_info.get('sids', [])
                                            
                                            for sid in sids:
                                                if current_service_id == new_service.service_id:
                                                    # 新客服：可以回复，解锁输入框
                                                    emit('visitor_assignment_updated', {
                                                        'visitor_id': visitor_id_val,
                                                        'visitor_name': from_name,
                                                        'visitor': visitor_info,
                                                        'assigned_to_me': True,
                                                        'can_reply': True,
                                                        'service_id': new_service.service_id,
                                                        'service_name': new_service.nick_name,
                                                        'old_service_id': old_service_id,
                                                        'reason': 'reassigned',
                                                        'message': f'访客 {from_name} 已自动分配给您',
                                                        'timestamp': datetime.now().isoformat()
                                                    }, room=sid)
                                                elif current_service_id == old_service_id:
                                                    # 原客服：不能回复，锁定输入框
                                                    emit('visitor_assignment_updated', {
                                                        'visitor_id': visitor_id_val,
                                                        'visitor_name': from_name,
                                                        'assigned_to_me': False,
                                                        'can_reply': False,
                                                        'service_id': new_service.service_id,
                                                        'service_name': new_service.nick_name,
                                                        'reason': 'reassigned_away',
                                                        'message': f'访客 {from_name} 已被重新分配给 {new_service.nick_name}',
                                                        'timestamp': datetime.now().isoformat()
                                                    }, room=sid)
                                                else:
                                                    # 其他客服/管理员：清除状态，确保不能回复
                                                    # 管理员可以查看但不能主动回复（除非访客主动发消息给他）
                                                    service_obj = Service.query.get(current_service_id)
                                                    is_admin = service_obj and service_obj.level in ['super_manager', 'manager']
                                                    
                                                    emit('visitor_assignment_updated', {
                                                        'visitor_id': visitor_id_val,
                                                        'visitor_name': from_name,
                                                        'assigned_to_me': False,
                                                        'can_reply': False,  # 其他客服不能回复
                                                        'can_view': is_admin,  # 管理员可以查看
                                                        'service_id': new_service.service_id,
                                                        'service_name': new_service.nick_name,
                                                        'reason': 'reassigned_to_other',
                                                        'timestamp': datetime.now().isoformat()
                                                    }, room=sid)
                                    
                                    logger.info(f"📢 已向所有客服广播访客{visitor_id_val}的分配状态更新")
                                except Exception as emit_err:
                                    logger.error(f"广播访客分配状态失败: {emit_err}")
                                    import traceback
                                    logger.error(traceback.format_exc())
                                
                                # ✅ 已在第1132行发送过service_changed，此处删除重复发送
                            else:
                                # 没有在线的人工客服，标记为未分配（机器人模式）
                                old_service_id = queue.service_id
                                queue.service_id = None  # ✅ NULL 表示未分配/机器人
                                queue.updated_at = datetime.now()
                                db.session.commit()
                                service_id_val = 0  # ✅ Chat表仍使用0表示机器人
                                logger.info(f"🤖 访客{visitor_id_val}分配给机器人: {old_service_id} -> NULL (所有人工客服都不可用)")
                                
                                # 通知访客已切换到机器人
                                try:
                                    emit('service_changed', {
                                        'message': '当前客服繁忙，已为您接入智能助手',
                                        'new_service': {
                                            'service_id': 0,
                                            'nick_name': '智能助手',
                                            'avatar': ''
                                        },
                                        'is_robot': True,
                                        'timestamp': datetime.now().isoformat()
                                    }, room=f'visitor_{visitor_id_val}')
                                except Exception as emit_err:
                                    logger.error(f"通知访客机器人接入失败: {emit_err}")
                    except Exception as reassign_err:
                        logger.error(f"❌ 重新分配客服失败: {reassign_err}")
                        import traceback
                        logger.error(traceback.format_exc())
                        # 分配失败，使用原客服ID
                        service_id_val = queue.service_id
                else:
                    # 当前客服在线，使用队列中的客服ID
                    service_id_val = queue.service_id
            else:
                # 队列不存在或没有分配客服，尝试分配
                if actual_service_id and actual_service_id != 'all':
                    # 访客发给指定客服
                    service_id_val = int(actual_service_id)
                elif to_id and to_id != 'all':
                    # 访客发给指定客服（备用）
                    service_id_val = int(to_id)
                else:
                    # 尝试自动分配（优先普通客服 -> 管理员 -> 机器人）
                    from mod.mysql.ModuleClass.AssignmentServiceClass import assignment_service
                    available_service = assignment_service._find_available_service(business_id)
                    if available_service:
                        # 有可用的人工客服
                        service_id_val = available_service.service_id
                        logger.info(f"🔄 访客{visitor_id_val}发送消息时自动分配给客服{service_id_val} ({available_service.nick_name})")
                        
                        # 如果有队列记录，更新它
                        if queue:
                            queue.service_id = service_id_val
                            queue.updated_at = datetime.now()
                            
                            # 更新客服接待计数（管理员不计入）
                            if available_service.level not in ['super_manager', 'manager']:
                                available_service.current_chat_count = (available_service.current_chat_count or 0) + 1
                            available_service.last_assign_time = datetime.now()
                            
                            db.session.commit()
                    else:
                        # 没有人工客服，标记为未分配（机器人模式）
                        service_id_val = None  # ✅ Chat表使用None表示机器人
                        logger.info(f"🤖 访客{visitor_id_val}发送消息时分配给机器人（所有人工客服都不可用）")
                        
                        # 如果有队列记录，更新它
                        if queue:
                            queue.service_id = None  # ✅ Queue表使用NULL表示未分配
                            queue.updated_at = datetime.now()
                            db.session.commit()
        elif actual_service_id and actual_service_id != 'all':
            # 访客发给指定客服
            service_id_val = int(actual_service_id)
        elif to_id and to_id != 'all':
            # 访客发给指定客服（备用）
            service_id_val = int(to_id)
        else:
            # 访客发给所有客服，使用第一个客服ID或None
            first_service = Service.query.filter_by(business_id=business_id).first()
            service_id_val = first_service.service_id if first_service else None
        
        chat = Chat(
            visitor_id=visitor_id_val,
            service_id=service_id_val,
            business_id=business_id,
            content=content,
            msg_type=1 if msg_type == 'text' else 2,
            timestamp=int(time.time()),
            direction='to_service' if from_type == 'visitor' else 'to_visitor',
            state='unread'
        )
        db.session.add(chat)
        
        # ⚡ 优化：复用之前查询的queue对象，避免重复数据库查询
        # 如果queue还未查询（非visitor发送），才进行查询
        if queue is None:
            queue = Queue.query.filter_by(
                visitor_id=visitor_id_val,
                business_id=business_id,
                state='normal'
            ).first()
        
        # ⚡ 如果Queue不存在，尝试查找已关闭的Queue并重新激活
        if not queue and from_type == 'visitor':
            # 查找最近的已关闭队列
            closed_queue = Queue.query.filter_by(
                visitor_id=visitor_id_val,
                business_id=business_id
            ).filter(
                Queue.state.in_(['complete', 'timeout', 'closed'])
            ).order_by(Queue.updated_at.desc()).first()
            
            if closed_queue:
                # 重新激活队列
                closed_queue.state = 'normal'
                closed_queue.last_message_time = datetime.now()
                closed_queue.updated_at = datetime.now()
                queue = closed_queue
                logger.info(f"✅ 重新激活队列 {closed_queue.qid}，访客: {visitor_id_val}")
        
        if queue:
            queue.last_message_time = datetime.now()
            queue.updated_at = datetime.now()  # 更新时间戳，用于列表排序
        else:
            logger.warning(f"⚠️ 找不到Queue记录，访客: {visitor_id_val}, 无法更新last_message_time")
        
        db.session.commit()
        
        # ✅ 客服回复后，立即将该访客的所有未读消息标记为已读
        if from_type == 'service':
            try:
                # 标记该访客发给客服的所有未读消息为已读
                unread_messages = Chat.query.filter_by(
                    visitor_id=visitor_id_val,
                    direction='to_service',
                    state='unread'
                ).update({'state': 'read'})
                
                if unread_messages > 0:
                    db.session.commit()
                    logger.info(f"✅ 客服{service_id_val}回复访客{visitor_id_val}，已将{unread_messages}条未读消息标记为已读")
                    
                    # 🔔 广播给所有在线客服：该访客的未读数量已清零
                    for user_key, user_info in list(online_users.items()):
                        if user_info['type'] in ['service', 'admin']:
                            sids = user_info.get('sids', [])
                            if not sids and 'sid' in user_info:
                                sids = [user_info['sid']]
                            
                            for sid in sids:
                                socketio.emit('unread_count_updated', {
                                    'visitor_id': visitor_id_val,
                                    'unread_count': 0,
                                    'reason': 'service_replied',
                                    'timestamp': datetime.now().isoformat()
                                }, room=sid)
                    
                    logger.info(f"📢 已广播访客{visitor_id_val}的未读数量清零事件")
            except Exception as e:
                logger.error(f"标记已读消息失败: {e}")
                db.session.rollback()
        
        # ⚡ 消息发送时广播统计更新（确保实时性）
        # 访客或客服发送消息都触发统计更新（表示会话活跃）
        # 但排除机器人自动回复（from_type == 'robot'）
        if from_type != 'robot':
            broadcast_statistics_update(business_id)
            logger.debug(f"📊 触发统计广播: from_type={from_type}, visitor={visitor_id_val}, service={service_id_val}")
        else:
            logger.debug(f"⏸️ 机器人消息，跳过统计广播")
        
        logger.info(f"💾 消息已保存 - visitor_id: {visitor_id_val}, service_id: {service_id_val}, 内容: {content[:30]}...")
        
        # 构建消息对象
        # ⚡ 为客服工作台过滤HTML标签（用于列表预览）
        content_preview = strip_html_tags_for_preview(content) if msg_type == 'text' else content
        
        message = {
            'id': chat.cid,
            'from_id': str(from_id),
            'from_type': from_type,
            'from_name': from_name,
            'to_id': str(to_id),
            'to_type': to_type,
            'content': content,  # 原始内容（包含HTML）
            'content_preview': content_preview,  # ⚡ 过滤后的预览内容
            'type': msg_type,
            'timestamp': datetime.now().isoformat(),
            'is_read': False,
            'visitor_id': visitor_id_val,  # ✅ 添加访客ID
            'service_id': service_id_val   # ✅ 添加客服ID（用于前端判断）
        }
        
        # 发送给目标用户
        if to_type == 'service':
            # ========== 智能发送：只发给分配的客服和管理员 ==========
            if from_type == 'visitor':
                # ⚡ 优化：复用之前查询的queue对象（第三次重复查询已移除）
                # queue对象在前面已经查询并可能被重新激活，直接使用
                assigned_service_id = queue.service_id if queue else None
                
                # ⚡ 优化：遍历在线客服，定向发送（使用缓存的权限级别，避免数据库查询）
                sent_count = 0
                for user_key, user_info in list(online_users.items()):
                    # ✅ 同时支持 service 和 admin 类型
                    if user_info['type'] in ['service', 'admin']:
                        service_id_check = user_info.get('service_id')
                        if service_id_check:
                            # ⚡ 使用缓存的权限级别，避免数据库查询
                            is_admin = user_info.get('is_admin', False)
                            is_assigned = (assigned_service_id and service_id_check == assigned_service_id)
                            # ✅ 未分配的访客（assigned_service_id=None）也发给管理员
                            is_unassigned_to_admin = (not assigned_service_id and is_admin)
                            
                            if is_admin or is_assigned or is_unassigned_to_admin:
                                # 获取该客服的所有连接ID
                                sids = user_info.get('sids', [])
                                # 兼容旧格式：如果没有 sids，尝试获取单个 sid
                                if not sids and 'sid' in user_info:
                                    sids = [user_info['sid']]
                                
                                for sid in sids:
                                    socketio.emit('receive_message', message, room=sid)
                                    sent_count += 1
                
                logger.info(f"📨 访客消息定向发送：visitor={visitor_id_val}, assigned_service={assigned_service_id}, 发送给{sent_count}个客服连接")
                
                # ⚡ 性能优化：禁用实时未读消息推送（严重影响性能）
                # 每次访客发消息都推送未读数会导致 5-10次数据库查询（每条消息延迟1-2秒）
                # 改为：客服打开聊天界面时主动查询，或定时轮询更新
                # 原代码(100行)已禁用，如需查看请查看Git历史
                pass  # ⚡ 已禁用：实时未读消息推送会严重阻塞(每条消息5-10次DB查询)
            else:
                # 客服发送的消息，广播给所有客服（保持原有逻辑）
                emit('receive_message', message, room='service_room')
                logger.info(f"Message broadcast to services from {from_type}_{from_id}")
        else:
            # 发送给特定访客
            # ⚡ 修复：to_id可能已包含前缀（如visitor_xxx），避免重复添加
            if to_type == 'visitor' and to_id.startswith('visitor_'):
                target_room = to_id  # 直接使用visitor_id作为room名称
            else:
                target_room = f'{to_type}_{to_id}'
            emit('receive_message', message, room=target_room)
            logger.info(f"Message sent from {from_type}_{from_id} to room={target_room}")
        
        # 发送给发送者（确认）
        emit('message_sent', {
            'status': 'success',
            'message_id': chat.cid,
            'timestamp': datetime.now().isoformat()
        })
        
        # ========== 智能机器人自动回复逻辑 ==========
        # 条件：访客发送文本消息
        if from_type == 'visitor' and msg_type == 'text':
            try:
                # 获取business_id
                business_id = data.get('business_id', 1)
                
                # ✅ 优先检查是否有FAQ答案（常见问题点击）
                faq_answer = data.get('faq_answer')
                is_faq_click = data.get('is_faq_click', False)
                auto_reply = None
                reply_source = None
                
                # 🔍 调试日志：检查FAQ相关参数
                logger.info(f"🔍 [FAQ诊断] 收到访客消息: content={content[:30]}...")
                logger.info(f"🔍 [FAQ诊断] faq_answer={faq_answer[:50] if faq_answer else 'None'}...")
                logger.info(f"🔍 [FAQ诊断] is_faq_click={is_faq_click}")
                
                if faq_answer and is_faq_click:
                    # FAQ回复（常见问题气泡点击）
                    # 🚫 不进行关键词匹配，直接使用FAQ答案
                    auto_reply = faq_answer
                    reply_source = 'faq'
                    logger.info(f"✅ [FAQ诊断] FAQ点击回复已启动: {auto_reply[:50]}...")
                elif faq_answer:
                    # 兼容旧逻辑：有FAQ答案但没有FAQ点击标记
                    auto_reply = faq_answer
                    reply_source = 'faq'
                    logger.info(f"📋 FAQ回复: {auto_reply[:50]}...")
                else:
                    # 1️⃣ 检查是否有在线客服（✅ 包括 admin 和 service）
                    online_services = [u for u in online_users.values() if u.get('type') in ['service', 'admin']]
                    is_service_online = len(online_services) > 0
                    
                    # 2️⃣ 使用新的机器人服务（会根据系统设置决定是否回复）
                    robot_service_instance = RobotService()
                    
                    # 传入客服在线状态，由机器人服务根据设置决定是否回复
                    auto_reply = robot_service_instance.get_auto_reply(
                        business_id=business_id,
                        message=content,
                        is_service_online=is_service_online
                    )
                    
                    if auto_reply:
                        reply_source = 'keyword'
                
                # 🔍 调试日志：检查auto_reply结果
                logger.info(f"🔍 [FAQ诊断] auto_reply={'有内容' if auto_reply else 'None'}, reply_source={reply_source}")
                
                if auto_reply:
                    if reply_source == 'faq':
                        logger.info(f"✅ [FAQ诊断] FAQ自动回复流程开始（常见问题点击）")
                    elif reply_source == 'keyword':
                        # ✅ 检查在线客服（包括 admin 和 service）
                        online_services = [u for u in online_users.values() if u.get('type') in ['service', 'admin']]
                        is_service_online = len(online_services) > 0
                        if is_service_online:
                            logger.info(f"✅ 客服在线，但系统设置为始终回复，触发机器人回复")
                        else:
                            logger.info(f"✅ 没有在线客服，触发机器人自动回复")
                        logger.info(f"   关键词匹配成功: {auto_reply[:50]}...")
                    
                    # 🔧 修复：移除重复的auto_reply检查（原1477行）
                    # 延迟一小段时间，模拟人工回复
                    import time
                    time.sleep(0.5)
                    
                    # 机器人回复使用 service_id=None 来标识（区别于真实客服）
                    robot_service_id = None
                    
                    logger.info(f"🔍 [FAQ诊断] 准备保存机器人消息到数据库...")
                    
                    # 保存自动回复到数据库
                    auto_chat = Chat(
                        visitor_id=from_id,
                        service_id=robot_service_id,  # ✅ None表示机器人
                        business_id=business_id,
                        content=auto_reply,
                        msg_type=1,
                        timestamp=int(time.time()),
                        direction='to_visitor',
                        state='unread'
                    )
                    logger.info(f"  visitor_id={from_id}, service_id={robot_service_id}, business_id={business_id}")
                    db.session.add(auto_chat)
                    logger.info(f"  已添加到session...")
                    db.session.commit()
                    logger.info(f"✅ [FAQ诊断] 机器人消息已保存到数据库，ID={auto_chat.cid}")
                    
                    # ⚡ 更新Queue的last_message_time（确保统计准确）
                    if queue:
                        queue.last_message_time = datetime.now()
                        db.session.commit()
                    
                    # 发送自动回复给访客
                    # ⚡ 机器人消息也需要过滤HTML标签
                    auto_content_preview = strip_html_tags_for_preview(auto_reply)
                    
                    auto_message = {
                        'id': auto_chat.cid,
                        'from_id': 'robot',  # robot表示机器人
                        'from_type': 'robot',
                        'from_name': '智能助手',
                        'to_id': str(from_id),
                        'to_type': 'visitor',
                        'content': auto_reply,  # 原始内容（包含HTML）
                        'content_preview': auto_content_preview,  # ⚡ 过滤后的预览内容
                        'type': 'text',
                        'timestamp': datetime.now().isoformat(),
                        'is_read': False
                    }
                    
                    # 发送给访客
                    # ⚡ 修复：from_id（visitor_id）已包含'visitor_'前缀，避免重复
                    visitor_room = from_id if from_id.startswith('visitor_') else f'visitor_{from_id}'
                    
                    logger.info(f"🔍 [FAQ诊断] 准备发送消息到访客 room={visitor_room}")
                    emit('receive_message', auto_message, room=visitor_room)
                    logger.info(f"🔍 [FAQ诊断] 消息已发送到访客")
                    
                    # ✅ 同时广播到客服工作台
                    emit('receive_message', auto_message, room='service_room')
                    logger.info(f"✅ [FAQ诊断] 自动回复发送完成: {auto_reply[:30]}...")
                else:
                    logger.info(f"⚠️ [FAQ诊断] 没有auto_reply，跳过机器人回复")
                    
            except Exception as robot_error:
                # 自动回复失败不影响正常消息发送
                logger.error(f"自动回复失败: {robot_error}")
        
    except Exception as e:
        logger.error(f"Error in send_message: {e}")
        emit('error', {'message': '消息发送失败'})


@socketio.on('typing')
def handle_typing(data):
    """
    正在输入状态
    data: {
        'from_id': 发送者ID,
        'from_type': 'visitor' or 'service',
        'to_id': 接收者ID,
        'to_type': 'visitor' or 'service',
        'is_typing': True/False
    }
    """
    try:
        from_id = data.get('from_id')
        from_type = data.get('from_type')
        to_id = data.get('to_id')
        to_type = data.get('to_type')
        from_name = data.get('from_name', '对方')
        is_typing = data.get('is_typing', True)
        
        # 发送输入状态给目标用户
        if to_id == 'all' and to_type == 'service':
            # 发送给所有客服
            emit('user_typing', {
                'from_id': str(from_id),
                'from_type': from_type,
                'from_name': from_name,
                'is_typing': is_typing
            }, room='service_room')
        else:
            # 发送给特定用户
            target_room = f'{to_type}_{to_id}'
            emit('user_typing', {
                'from_id': str(from_id),
                'from_type': from_type,
                'from_name': from_name,
                'is_typing': is_typing
            }, room=target_room)
        
    except Exception as e:
        logger.error(f"Error in typing: {e}")


@socketio.on('read_message')
def handle_read_message(data):
    """
    标记消息已读
    data: {
        'message_id': 消息ID
    }
    """
    try:
        message_id = data.get('message_id')
        
        # 更新数据库
        chat = Chat.query.get(message_id)
        if chat:
            chat.is_read = True
            db.session.commit()
            
            emit('message_read', {
                'message_id': message_id,
                'status': 'success'
            })
        
    except Exception as e:
        logger.error(f"Error in read_message: {e}")


@socketio.on('get_online_users')
def handle_get_online_users():
    """获取在线用户列表（已按账号去重，普通客服只看到分配给自己的访客）"""
    try:
        # 获取当前请求的客服ID
        current_sid = request.sid
        current_service_id = None
        is_admin = False
        is_visitor_request = False
        
        # 查找当前用户（可能是客服或访客）
        # ✅ 同时检查service和admin
        for user_key, user_info in online_users.items():
            if user_info['type'] in ['service', 'admin']:
                sids = user_info.get('sids', [])
                if current_sid in sids:
                    current_service_id = user_info.get('service_id')
                    break
            elif user_info['type'] == 'visitor':
                sids = user_info.get('sids', [])
                if current_sid in sids:
                    is_visitor_request = True
                    break
        
        # 如果是访客请求，只返回在线客服信息（不返回其他访客）
        if is_visitor_request:
            # ✅ 修复多worker同步问题：从数据库查询而不是从online_users内存字典
            visitor_online_services = []
            try:
                # 从数据库查询state='online'的客服（假设business_id=1，实际应从访客信息获取）
                business_id = 1  # TODO: 应从访客信息中获取business_id
                online_service_records = Service.query.filter_by(
                    business_id=business_id,
                    state='online'
                ).all()
                
                for service in online_service_records:
                    visitor_online_services.append({
                        'service_id': service.service_id,
                        'name': service.nick_name
                    })
                
                logger.info(f"📊 访客请求在线用户列表：{len(visitor_online_services)}个在线客服 (从数据库查询)")
            except Exception as e:
                logger.error(f"查询在线客服失败: {e}")
                # 如果数据库查询失败，降级使用online_users（保持兼容性）
                seen_service_ids = set()
                for user_key, user_info in list(online_users.items()):
                    if user_info['type'] in ['service', 'admin']:
                        has_connection = False
                        if 'sids' in user_info and len(user_info['sids']) > 0:
                            has_connection = True
                        elif 'sid' in user_info and user_info['sid']:
                            has_connection = True
                        
                        if has_connection and user_info.get('service_id'):
                            service_id_val = user_info['service_id']
                            if service_id_val not in seen_service_ids:
                                seen_service_ids.add(service_id_val)
                                visitor_online_services.append({
                                    'service_id': service_id_val,
                                    'name': user_info.get('name', '客服')
                                })
                logger.warning(f"⚠️ 数据库查询失败，降级使用online_users，客服数：{len(visitor_online_services)}个")
            
            emit('online_users_list', {
                'services': visitor_online_services,
                'visitors': [],  # 访客不应该看到其他访客
                'total_services': len(visitor_online_services),
                'total_visitors': 0
            })
            return
        
        # 查询当前客服是否是管理员
        if current_service_id:
            current_service = Service.query.get(current_service_id)
            if current_service:
                is_admin = current_service.level in ['super_manager', 'manager']
        
        # 区分客服和访客
        online_services = []
        online_visitors = []
        seen_service_ids = set()  # ✅ 去重：防止同一客服既有admin连接又有service连接
        
        # 创建字典副本，避免遍历时字典被修改
        for user_id, info in list(online_users.items()):
            # 检查是否有有效连接（支持新旧格式）
            has_connection = False
            if 'sids' in info and len(info['sids']) > 0:
                has_connection = True
            elif 'sid' in info and info['sid']:
                has_connection = True
            
            if not has_connection:
                continue
            
            # ✅ 合并 admin 和 service 类型
            if info['type'] in ['service', 'admin']:
                service_id_val = info.get('service_id')
                if service_id_val and service_id_val not in seen_service_ids:
                    seen_service_ids.add(service_id_val)
                    # 📊 同一个service_id只会出现一次（按账号去重）
                    service_data = {
                        'service_id': service_id_val,
                        'name': info.get('name', '客服')  # ✅ 安全访问，提供默认值
                    }
                    # 🆕 添加连接数信息（用于调试）
                    if 'sids' in info:
                        service_data['connection_count'] = len(info['sids'])
                    
                    online_services.append(service_data)
                
            elif info['type'] == 'visitor':
                # ========== 访客过滤：普通客服只看到分配给自己的访客 ==========
                visitor_id = info.get('visitor_id')
                
                # 查询访客的队列信息
                queue = Queue.query.filter_by(
                    visitor_id=visitor_id,
                    state='normal'
                ).order_by(Queue.created_at.desc()).first()
                
                # 判断是否应该显示此访客
                should_show = False
                if is_admin:
                    # 管理员看到所有访客
                    should_show = True
                elif queue and queue.service_id == current_service_id:
                    # 普通客服只看到分配给自己的访客
                    should_show = True
                
                if should_show:
                    # 查询访客的最后一条消息
                    last_chat = Chat.query.filter_by(
                        visitor_id=visitor_id
                    ).order_by(Chat.timestamp.desc()).first()
                    
                    # 返回完整的访客信息
                    visitor_data = {
                        'visitor_id': info.get('visitor_id'),
                        'visitor_name': info.get('visitor_name', info.get('name')),
                        'name': info.get('name'),
                        'avatar': info.get('avatar', '👤'),
                        'ip': info.get('ip', '-'),
                        'location': info.get('location', '未知'),
                        'country': info.get('country', ''),
                        'province': info.get('province', ''),
                        'city': info.get('city', ''),
                        'browser': info.get('browser', 'Unknown'),
                        'os': info.get('os', 'Unknown'),
                        'device': info.get('device', 'Desktop'),
                        'screen_resolution': info.get('screen_resolution', ''),
                        'visit_count': info.get('visit_count', 1),
                        'first_visit': info.get('first_visit', '')
                    }
                    
                    # 添加最后一条消息信息（用于列表显示）
                    if last_chat:
                        visitor_data['last_message'] = last_chat.content
                        visitor_data['last_message_time'] = last_chat.created_at.isoformat() if last_chat.created_at else None
                    else:
                        visitor_data['last_message'] = None
                        visitor_data['last_message_time'] = None
                    
                    # 🆕 添加连接数信息（用于调试）
                    if 'sids' in info:
                        visitor_data['connection_count'] = len(info['sids'])
                    
                    online_visitors.append(visitor_data)
        
        logger.info(f"📊 客服{current_service_id}{'[管理员]' if is_admin else '[普通]'}在线统计：{len(online_services)}个客服，{len(online_visitors)}个访客")
        
        emit('online_users_list', {
            'services': online_services,
            'visitors': online_visitors,
            'total_services': len(online_services),  # 已按账号去重
            'total_visitors': len(online_visitors)
        })
        
    except Exception as e:
        logger.error(f"Error in get_online_users: {e}")


@socketio.on('end_chat')
def handle_end_chat(data):
    """
    结束会话
    data: {
        'visitor_id': 访客ID,
        'service_id': 客服ID,
        'business_id': 商户ID
    }
    """
    try:
        visitor_id = data.get('visitor_id')
        service_id = data.get('service_id')
        business_id = data.get('business_id', 1)
        
        logger.info(f"会话结束: 访客 {visitor_id} 与客服 {service_id}")
        
        # 查找队列记录
        queue = Queue.query.filter_by(
            visitor_id=visitor_id,
            business_id=business_id,
            state='normal'
        ).order_by(Queue.created_at.desc()).first()
        
        if queue:
            # 更新队列状态为已完成
            queue.state = 'complete'
            queue.updated_at = datetime.now()
            db.session.commit()
            
            # ========== 减少客服接待计数 ==========
            if queue.service_id and queue.service_id > 0:
                try:
                    service = Service.query.get(queue.service_id)
                    if service and service.current_chat_count > 0:
                        # 减少接待数
                        service.current_chat_count = max(0, service.current_chat_count - 1)
                        db.session.commit()
                        logger.info(f"✅ 客服{queue.service_id}接待数减少: {service.current_chat_count}/{service.max_concurrent_chats}")
                except Exception as e:
                    logger.error(f"减少接待计数失败: {e}")
            
            # 通知访客会话已结束
            emit('chat_ended', {
                'queue_id': queue.qid,
                'service_id': service_id,
                'message': '会话已结束'
            }, room=f'visitor_{visitor_id}')
            
            # 延迟1秒后推送评价请求
            def push_comment_request():
                """异步推送评价请求"""
                try:
                    import time
                    time.sleep(1)
                    
                    # 获取客服信息
                    service = Service.query.get(service_id)
                    service_name = service.nick_name if service else '客服'
                    
                    # 向访客推送评价请求
                    socketio.emit('request_comment', {
                        'queue_id': queue.qid,
                        'service_id': service_id,
                        'service_name': service_name,
                        'message': f'请为 {service_name} 的服务进行评价'
                    }, room=f'visitor_{visitor_id}')
                    
                    logger.info(f"✅ 已向访客 {visitor_id} 推送评价请求")
                    
                except Exception as e:
                    logger.error(f"推送评价请求失败: {e}")
            
            # 启动后台线程推送评价
            from threading import Thread
            Thread(target=push_comment_request, daemon=True).start()
            
            # 通知客服会话已结束
            emit('chat_ended', {
                'visitor_id': visitor_id,
                'message': '会话已结束'
            }, room='service_room')
            
            # 广播统计更新（会话结束）
            broadcast_statistics_update(business_id)
            
            # 通知管理员会话结束
            socketio.emit('session_ended', {
                'visitor_id': visitor_id,
                'service_id': service_id,
                'timestamp': datetime.now().isoformat()
            }, broadcast=True)
        else:
            emit('error', {'message': '未找到会话记录'})
        
    except Exception as e:
        logger.error(f"结束会话失败: {e}")
        emit('error', {'message': '结束会话失败'})


@socketio.on('error')
def handle_error(error):
    """错误处理"""
    logger.error(f"SocketIO Error: {error}")


# 辅助函数
def get_user_sid(user_type, user_id):
    """获取用户的socket ID"""
    key = f'{user_type}_{user_id}'
    return online_users.get(key, {}).get('sid')


def is_user_online(user_type, user_id):
    """检查用户是否在线"""
    key = f'{user_type}_{user_id}'
    return key in online_users


# ========== 队列管理相关事件 ==========

@socketio.on('visitor_join_queue')
def handle_visitor_join_queue(data):
    """访客加入队列"""
    try:
        visitor_id = data.get('visitor_id')
        business_id = data.get('business_id', 1)
        priority = data.get('priority', 0)
        
        logger.info(f"访客 {visitor_id} 加入队列，优先级: {priority}")
        
        # 添加到队列
        qs = get_queue_service()
        queue = qs.add_to_queue(
            visitor_id=visitor_id,
            business_id=business_id,
            priority=priority
        )
        
        # 获取排队位置和预计等待时间
        qs = get_queue_service()
        position = qs.get_queue_position(visitor_id, business_id)
        
        # 通知访客加入成功
        emit('queue_joined', {
            'queue_id': queue.qid,
            'position': position,
            'estimated_wait_time': queue.estimated_wait_time,
            'priority': queue.priority
        })
        
        # 通知所有在线客服有新访客排队
        notify_new_visitor_queued(business_id, visitor_id, priority, position)
        
        # 广播队列更新
        broadcast_queue_update(business_id)
        
    except Exception as e:
        logger.error(f"访客加入队列失败: {e}")
        emit('error', {'msg': f'加入队列失败: {str(e)}'})


@socketio.on('service_accept_queue')
def handle_service_accept_queue(data):
    """客服接入排队访客"""
    try:
        queue_id = data.get('queue_id')
        service_id = data.get('service_id')
        
        logger.info(f"客服 {service_id} 接入队列 {queue_id}")
        
        # 查找队列记录
        queue = Queue.query.get(queue_id)
        if not queue:
            emit('error', {'msg': '队列不存在'})
            return
        
        # 更新队列记录
        queue.service_id = service_id
        queue.estimated_wait_time = 0
        db.session.commit()
        
        # 通知客服接入成功
        emit('queue_accepted', {
            'queue_id': queue_id,
            'visitor_id': queue.visitor_id
        })
        
        # 通知访客已被接入
        visitor_sid = get_user_sid('visitor', queue.visitor_id)
        if visitor_sid:
            socketio.emit('service_connected', {
                'service_id': service_id,
                'queue_id': queue_id
            }, room=visitor_sid)
        
        # 广播队列更新
        broadcast_queue_update(queue.business_id)
        
        # 广播统计更新（新会话开始）
        broadcast_statistics_update(queue.business_id)
        
        # 通知管理员新会话创建
        socketio.emit('session_created', {
            'visitor_id': queue.visitor_id,
            'service_id': service_id,
            'timestamp': datetime.now().isoformat()
        }, broadcast=True)
        
    except Exception as e:
        logger.error(f"客服接入队列失败: {e}")
        emit('error', {'msg': f'接入失败: {str(e)}'})


@socketio.on('update_visitor_priority')
def handle_update_visitor_priority(data):
    """更新访客优先级"""
    try:
        visitor_id = data.get('visitor_id')
        business_id = data.get('business_id', 1)
        priority = data.get('priority', 0)
        
        logger.info(f"更新访客 {visitor_id} 优先级为: {priority}")
        
        # 查找队列记录
        queue = Queue.query.filter_by(
            visitor_id=visitor_id,
            business_id=business_id,
            state='normal'
        ).first()
        
        if queue:
            old_priority = queue.priority
            queue.priority = priority
            db.session.commit()
            
            # 重新计算预计等待时间
            qs = get_queue_service()
            position = qs.get_queue_position(visitor_id, business_id)
            estimated_time = qs.estimate_wait_time(business_id, position, priority)
            if estimated_time >= 0:
                queue.estimated_wait_time = estimated_time
                db.session.commit()
            
            # 通知访客优先级已更新
            visitor_sid = get_user_sid('visitor', visitor_id)
            if visitor_sid:
                socketio.emit('priority_updated', {
                    'old_priority': old_priority,
                    'new_priority': priority,
                    'position': position,
                    'estimated_wait_time': estimated_time
                }, room=visitor_sid)
            
            # 广播队列更新
            broadcast_queue_update(business_id)
            
            emit('success', {'msg': '优先级更新成功'})
        else:
            emit('error', {'msg': '队列记录不存在'})
            
    except Exception as e:
        logger.error(f"更新优先级失败: {e}")
        emit('error', {'msg': f'更新失败: {str(e)}'})


@socketio.on('get_queue_status')
def handle_get_queue_status(data):
    """获取队列状态"""
    try:
        business_id = data.get('business_id', 1)
        
        # 获取队列统计
        qs = get_queue_service()
        stats = qs.get_queue_statistics(business_id)
        
        emit('queue_status', stats)
        
    except Exception as e:
        logger.error(f"获取队列状态失败: {e}")
        emit('error', {'msg': f'获取失败: {str(e)}'})


def notify_new_visitor_queued(business_id, visitor_id, priority, position):
    """通知所有在线客服有新访客排队"""
    try:
        # 获取访客信息
        visitor = Visitor.query.get(visitor_id)
        if not visitor:
            return
        
        # 优先级文本
        priority_text = '普通'
        if priority == 2:
            priority_text = '紧急'
        elif priority == 1:
            priority_text = 'VIP'
        
        # 通知所有在线客服
        # ✅ 同时通知service和admin
        for user_key, user_info in online_users.items():
            if user_info['type'] in ['service', 'admin']:
                socketio.emit('new_visitor_queued', {
                    'visitor_id': visitor_id,
                    'visitor_name': visitor.visitor_name,
                    'priority': priority,
                    'priority_text': priority_text,
                    'position': position,
                    'timestamp': datetime.utcnow().isoformat()
                }, room=user_info['sid'])
                
    except Exception as e:
        logger.error(f"通知新访客排队失败: {e}")


def broadcast_queue_update(business_id):
    """广播队列更新"""
    try:
        # 获取队列统计
        qs = get_queue_service()
        stats = qs.get_queue_statistics(business_id)
        
        # 获取等待列表
        waiting_list = qs.get_waiting_list(business_id, limit=100)
        
        # 广播给所有在线客服
        # ✅ 同时广播给service和admin
        for user_key, user_info in online_users.items():
            if user_info['type'] in ['service', 'admin']:
                socketio.emit('queue_update', {
                    'stats': stats,
                    'waiting_count': len(waiting_list),
                    'timestamp': datetime.utcnow().isoformat()
                }, room=user_info['sid'])
                
    except Exception as e:
        logger.error(f"广播队列更新失败: {e}")


# 广播防抖：缓存最后一次广播的时间和数据（避免短时间内重复广播相同数据）
_last_broadcast_time = {}
_last_broadcast_data = {}

def broadcast_statistics_update(business_id):
    """
    广播统计数据更新（给管理员）
    带防抖机制：3秒内相同数据不重复广播
    
    ⚡ 性能优化：
    1. 移除主动清除缓存逻辑，利用10秒Redis缓存机制
    2. 延长防抖时间到3秒，减少高频消息场景下的查询次数
    """
    try:
        from mod.mysql.ModuleClass import StatisticsService
        
        # ⚡ 优化：不再主动清除缓存，利用get_realtime_stats的10秒缓存机制
        # 这样可以显著减少数据库查询次数，提升消息推送性能
        
        # 获取实时统计数据（带10秒Redis缓存）
        stats_service = StatisticsService(business_id, None, 'super_manager')
        realtime = stats_service.get_realtime_stats()
        
        # 构建广播数据
        broadcast_data = {
            'total_visitors': realtime.get('total_visitors', 0),
            'chatting_count': realtime.get('chatting_count', 0),
            'online_services': realtime.get('online_services', 0),
            'waiting_count': realtime.get('waiting_count', 0),
            'timestamp': datetime.now().isoformat()
        }
        
        # ⚡ 防抖检查：如果3秒内已经广播过相同的数据，跳过（从1秒延长到3秒）
        import time
        current_time = time.time()
        last_time = _last_broadcast_time.get(business_id, 0)
        last_data = _last_broadcast_data.get(business_id, {})
        
        # 比较关键数据（排除timestamp）
        key_data = {k: v for k, v in broadcast_data.items() if k != 'timestamp'}
        last_key_data = {k: v for k, v in last_data.items() if k != 'timestamp'}
        
        if (current_time - last_time < 3.0) and (key_data == last_key_data):
            logger.debug(f"⏸️ 防抖：3秒内已广播相同数据，跳过")
            return
        
        # 更新防抖缓存
        _last_broadcast_time[business_id] = current_time
        _last_broadcast_data[business_id] = broadcast_data
        
        # ⚡ Flask-SocketIO默认广播给所有连接的客户端（无需broadcast参数）
        socketio.emit('statistics_update', broadcast_data)
                
        logger.info(f"📊 已广播统计更新: 正在咨询 {realtime.get('chatting_count', 0)} 人, 在线客服 {realtime.get('online_services', 0)} 人")
                
    except Exception as e:
        logger.error(f"广播统计更新失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


@socketio.on('admin_join')
def handle_admin_join(data):
    """
    管理员加入（用于接收统计更新）
    data: {
        'service_id': 客服ID（管理员也是客服）,
        'service_name': 客服名称
    }
    """
    try:
        service_id = data.get('service_id')
        service_name = data.get('service_name', '管理员')
        sid = request.sid
        
        if not service_id:
            logger.error(f"❌ admin_join 缺少 service_id")
            emit('error', {'message': '缺少客服ID'})
            return
        
        # 查询客服信息验证权限
        service = Service.query.get(service_id)
        if not service:
            logger.error(f"❌ admin_join 找不到客服: {service_id}")
            emit('error', {'message': '客服不存在'})
            return
        
        if service.level not in ['super_manager', 'manager']:
            logger.warning(f"⚠️ 非管理员尝试加入admin_join: {service_id}")
            emit('error', {'message': '权限不足'})
            return
        
        user_key = f'admin_{service_id}'
        
        # 支持多连接
        if user_key in online_users:
            if 'sids' not in online_users[user_key]:
                old_sid = online_users[user_key].get('sid')
                online_users[user_key]['sids'] = [old_sid] if old_sid else []
            if sid not in online_users[user_key]['sids']:
                online_users[user_key]['sids'].append(sid)
            # 更新权限缓存
            online_users[user_key]['is_admin'] = True
        else:
            online_users[user_key] = {
                'type': 'admin',
                'service_id': service_id,
                'service_name': service_name,
                'level': service.level,
                'is_admin': True,  # ⚡ 缓存权限级别，避免消息推送时查询
                'sids': [sid],
                'business_id': service.business_id,
                'connected_at': datetime.now().isoformat()
            }
        
        logger.info(f"✅ 管理员加入: {service_name} ({service_id}), SID: {sid}")
        
        # ✅ 修复：更新数据库中的在线状态（与service_join保持一致）
        try:
            service.state = 'online'
            db.session.commit()
            logger.info(f"✅ 管理员{service_id}状态更新为 online")
            
            # ✅ 管理员上线时，自动同步接待数（确保数据准确）
            from mod.mysql.ModuleClass.ServiceWorkloadManager import workload_manager
            sync_result = workload_manager.sync_workload(service_id, "管理员上线自动同步")
            if sync_result['success']:
                logger.info(f"📊 管理员{service_id}上线，接待数已同步: {sync_result['current_count']}")
        except Exception as e:
            logger.error(f"更新管理员在线状态失败: {e}")
        
        # 发送加入成功消息
        emit('admin_join_success', {
            'message': '管理员已连接',
            'service_id': service_id,
            'service_name': service_name
        })
        
        # 立即发送一次统计数据
        from mod.mysql.ModuleClass import StatisticsService
        stats_service = StatisticsService(service.business_id, service_id, service.level)
        realtime = stats_service.get_realtime_stats()
        
        emit('statistics_update', {
            'total_visitors': realtime.get('total_visitors', 0),
            'chatting_count': realtime.get('chatting_count', 0),
            'online_services': realtime.get('online_services', 0),
            'waiting_count': realtime.get('waiting_count', 0),
            'timestamp': datetime.now().isoformat()
        })
        
        # ✅ 发送未读消息数
        try:
            unread_count = db.session.query(func.count(Chat.cid)).filter(
                and_(
                    Chat.state == 'unread',  # ✅ 未读状态
                    Chat.msg_type == 0,  # 访客发送的消息
                    Chat.service_id == service_id
                )
            ).scalar() or 0
            
            emit('unread_messages_update', {
                'unread_count': unread_count,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"获取未读消息数失败: {e}")
        
    except Exception as e:
        logger.error(f"admin_join错误: {e}")
        import traceback
        logger.error(traceback.format_exc())
        emit('error', {'message': str(e)})