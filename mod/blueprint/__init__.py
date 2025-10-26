"""
蓝图包
"""
from .auth import auth_bp
from .visitor import visitor_bp
from .service import service_bp
from .admin import admin_bp

__all__ = ['auth_bp', 'visitor_bp', 'service_bp', 'admin_bp']
