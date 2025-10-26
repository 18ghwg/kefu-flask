"""
访客前台视图
"""
from flask import Blueprint, render_template, request

index_bp = Blueprint('index', __name__)


@index_bp.route('/')
def home():
    """首页"""
    return render_template('index/index.html')


@index_bp.route('/chat')
def chat():
    """聊天窗口"""
    visitor_id = request.args.get('visitor_id', '')
    business_id = request.args.get('business_id', 1)
    special = request.args.get('special', '')  # 指定客服ID（专属链接）
    
    return render_template('index/chat.html', 
                         visitor_id=visitor_id,
                         business_id=business_id,
                         special=special)
