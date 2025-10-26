"""
客服API
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.queue import Queue
from app.models.visitor import Visitor
from app.services.queue_service import QueueService
from app.services.chat_service import ChatService

service_bp = Blueprint('service', __name__)


@service_bp.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    """工作台数据"""
    business_id = current_user.business_id
    
    # 统计数据
    waiting_count = Queue.query.filter_by(
        business_id=business_id,
        service_id=0,
        state='normal'
    ).count()
    
    chatting_count = Queue.query.filter_by(
        business_id=business_id,
        state='normal'
    ).filter(Queue.service_id > 0).count()
    
    return jsonify({
        'code': 0,
        'data': {
            'waiting_count': waiting_count,
            'chatting_count': chatting_count
        }
    })


@service_bp.route('/queue', methods=['GET'])
@login_required
def get_queue():
    """获取排队列表"""
    business_id = current_user.business_id
    
    # 查询排队中的访客
    queues = Queue.query.filter_by(
        business_id=business_id,
        service_id=0,
        state='normal'
    ).all()
    
    visitor_list = []
    for q in queues:
        visitor = Visitor.query.filter_by(
            visitor_id=q.visitor_id,
            business_id=business_id
        ).first()
        if visitor:
            visitor_list.append(visitor.to_dict())
    
    return jsonify({
        'code': 0,
        'data': {
            'queue': visitor_list
        }
    })


@service_bp.route('/claim', methods=['POST'])
@login_required
def claim():
    """认领访客"""
    data = request.get_json()
    
    if not data or not data.get('visitor_id'):
        return jsonify({'code': 1000, 'msg': '参数不完整'}), 400
    
    queue_service = QueueService()
    success = queue_service.claim_visitor(
        service_id=current_user.service_id,
        visitor_id=data['visitor_id']
    )
    
    if success:
        return jsonify({'code': 0, 'msg': '认领成功'})
    else:
        return jsonify({'code': 3000, 'msg': '认领失败'}), 400


@service_bp.route('/message', methods=['POST'])
@login_required
def send_message():
    """发送消息"""
    data = request.get_json()
    
    required_fields = ['visitor_id', 'content']
    if not all(field in data for field in required_fields):
        return jsonify({'code': 1000, 'msg': '参数不完整'}), 400
    
    chat_service = ChatService()
    message = chat_service.send_message(
        visitor_id=data['visitor_id'],
        service_id=current_user.service_id,
        business_id=current_user.business_id,
        content=data['content'],
        msg_type=data.get('msg_type', 'text'),
        direction='to_visitor'
    )
    
    return jsonify({
        'code': 0,
        'msg': 'success',
        'data': message.to_dict() if message else None
    })


@service_bp.route('/personal-link', methods=['GET'])
@login_required
def get_personal_link():
    """获取客服专属对话链接"""
    service_id = current_user.service_id
    business_id = current_user.business_id
    
    # 获取当前访问的域名和协议
    base_url = request.host_url.rstrip('/')
    
    # 生成专属链接
    personal_link = f"{base_url}/chat?business_id={business_id}&special={service_id}"
    
    return jsonify({
        'code': 0,
        'msg': 'success',
        'data': {
            'service_id': service_id,
            'personal_link': personal_link,
            'base_url': base_url
        }
    })