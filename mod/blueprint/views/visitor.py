"""
访客视图
提供访客聊天窗口
"""
from flask import Blueprint, render_template, request

visitor_view_bp = Blueprint('visitor_view', __name__)


@visitor_view_bp.route('/chat')
def chat():
    """访客聊天窗口"""
    return render_template('visitor_chat.html')


@visitor_view_bp.route('/chat/mobile')
def chat_mobile():
    """移动端访客聊天窗口"""
    return render_template('visitor_chat.html')

