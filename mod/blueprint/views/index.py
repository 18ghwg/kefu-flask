"""
访客前台视图
"""
from flask import Blueprint, render_template, request

index_bp = Blueprint('index', __name__)


@index_bp.route('/')
def home():
    """首页"""
    return render_template('index.html')


@index_bp.route('/chat')
def chat():
    """访客聊天窗口"""
    visitor_id = request.args.get('visitor_id', '')
    business_id = request.args.get('business_id', 1)
    
    return render_template('visitor_chat.html', 
                         visitor_id=visitor_id,
                         business_id=business_id)
