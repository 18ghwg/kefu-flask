"""
管理后台视图
"""
from flask import Blueprint, render_template
from flask_login import login_required, current_user

admin_panel_bp = Blueprint('admin_panel', __name__)


@admin_panel_bp.route('/')
@login_required
def index():
    """管理后台首页"""
    if current_user.level not in ['super_manager', 'manager']:
        return '权限不足', 403
    
    return render_template('admin/index.html')
