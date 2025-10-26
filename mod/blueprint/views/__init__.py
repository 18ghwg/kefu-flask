"""
视图蓝图包
"""
from .index import index_bp
from .service_panel import service_panel_bp
from .admin_panel import admin_panel_bp
from .install import install_bp
from .auth import auth_view_bp

__all__ = ['index_bp', 'service_panel_bp', 'admin_panel_bp', 'install_bp', 'auth_view_bp']
