"""
客服工作台视图
"""
from flask import Blueprint, render_template, session, redirect, url_for, jsonify
from flask_login import login_required, current_user
from mod.mysql.ModuleClass.StatisticsServiceClass import StatisticsService

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
    return render_template('service/chat.html', current_user=current_user)
