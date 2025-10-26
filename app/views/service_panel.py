"""
客服工作台视图
"""
from flask import Blueprint, render_template
from flask_login import login_required

service_panel_bp = Blueprint('service_panel', __name__)


@service_panel_bp.route('/')
@login_required
def index():
    """工作台首页"""
    return render_template('service/index.html')


@service_panel_bp.route('/chat')
@login_required
def chat():
    """客服聊天页面"""
    return render_template('service/chat.html')
