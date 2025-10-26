"""
管理后台视图
"""
from flask import Blueprint, render_template, jsonify, redirect, url_for
from flask_login import login_required, current_user
from mod.mysql.ModuleClass import StatisticsService

admin_panel_bp = Blueprint('admin_panel', __name__)


@admin_panel_bp.route('/')
@login_required
def index():
    """管理后台首页"""
    if current_user.level not in ['super_manager', 'manager']:
        return redirect(url_for('service_panel.chat'))
    
    # 获取实时统计数据
    business_id = current_user.business_id
    service_id = current_user.service_id
    level = current_user.level
    
    stats = StatisticsService(business_id, service_id, level)
    
    # 实时数据
    realtime = stats.get_realtime_stats()
    
    # 今日数据
    today = stats.get_today_stats()
    
    return render_template('admin/index.html', 
                         realtime=realtime,
                         today=today)


@admin_panel_bp.route('/knowledge')
@login_required
def knowledge():
    """知识库管理"""
    if current_user.level not in ['super_manager', 'manager']:
        return redirect(url_for('service_panel.chat'))
    
    return render_template('admin/knowledge.html')


@admin_panel_bp.route('/visitors')
@login_required
def visitors():
    """访客管理"""
    if current_user.level not in ['super_manager', 'manager']:
        return redirect(url_for('service_panel.chat'))
    
    return render_template('admin/visitors.html')


@admin_panel_bp.route('/visitor/<visitor_id>')
@login_required
def visitor_detail(visitor_id):
    """访客详情"""
    if current_user.level not in ['super_manager', 'manager']:
        return redirect(url_for('service_panel.chat'))
    
    return render_template('admin/visitor_detail.html')


@admin_panel_bp.route('/comments')
@login_required
def comments():
    """评价管理"""
    if current_user.level not in ['super_manager', 'manager']:
        return redirect(url_for('service_panel.chat'))
    
    return render_template('admin/comments.html')


@admin_panel_bp.route('/comment-statistics')
@login_required
def comment_statistics():
    """评价统计"""
    if current_user.level not in ['super_manager', 'manager']:
        return redirect(url_for('service_panel.chat'))
    
    return render_template('admin/comment_statistics.html')


@admin_panel_bp.route('/comment-ranking')
@login_required
def comment_ranking():
    """客服评价排行榜"""
    if current_user.level not in ['super_manager', 'manager']:
        return redirect(url_for('service_panel.chat'))
    
    return render_template('admin/comment_ranking.html')


@admin_panel_bp.route('/dashboard')
@login_required
def dashboard():
    """数据看板"""
    if current_user.level not in ['super_manager', 'manager']:
        return redirect(url_for('service_panel.chat'))
    
    # 获取统计数据
    business_id = current_user.business_id
    service_id = current_user.service_id
    level = current_user.level
    
    stats = StatisticsService(business_id, service_id, level)
    
    # 实时数据
    realtime = stats.get_realtime_stats()
    
    # 今日数据
    today = stats.get_today_stats()
    
    # 7天趋势
    trend = stats.get_trend_stats(days=7)
    
    return render_template('admin/dashboard.html',
                         realtime=realtime,
                         today=today,
                         trend=trend)


@admin_panel_bp.route('/services')
@login_required
def services():
    """客服管理"""
    if current_user.level not in ['super_manager', 'manager']:
        return redirect(url_for('service_panel.chat'))
    
    return render_template('admin/services.html')


@admin_panel_bp.route('/service-groups')
@login_required
def service_groups():
    """客服分组"""
    if current_user.level not in ['super_manager', 'manager']:
        return redirect(url_for('service_panel.chat'))
    
    return render_template('admin/service_groups.html')


@admin_panel_bp.route('/chat-history')
@login_required
def chat_history():
    """聊天记录查询"""
    if current_user.level not in ['super_manager', 'manager']:
        return redirect(url_for('service_panel.chat'))
    
    return render_template('admin/chat_history.html')


@admin_panel_bp.route('/queue-management')
@login_required
def queue_management():
    """队列管理"""
    if current_user.level not in ['super_manager', 'manager']:
        return redirect(url_for('service_panel.chat'))
    
    return render_template('admin/queue_management.html')


@admin_panel_bp.route('/system-settings')
@login_required
def system_settings():
    """系统设置"""
    if current_user.level not in ['super_manager', 'manager']:
        return redirect(url_for('service_panel.chat'))
    
    return render_template('admin/system_settings.html')


@admin_panel_bp.route('/faq-settings')
@login_required
def faq_settings():
    """常见问题设置"""
    if current_user.level not in ['super_manager', 'manager']:
        return redirect(url_for('service_panel.chat'))
    
    return render_template('admin/faq_settings.html')


@admin_panel_bp.route('/greeting-settings')
@login_required
def greeting_settings():
    """问候语设置"""
    if current_user.level not in ['super_manager', 'manager']:
        return redirect(url_for('service_panel.chat'))
    
    return render_template('admin/greeting_settings.html')


@admin_panel_bp.route('/operation-logs')
@login_required
def operation_logs():
    """操作日志"""
    if current_user.level not in ['super_manager', 'manager']:
        return redirect(url_for('service_panel.chat'))
    
    return render_template('admin/operation_logs.html')