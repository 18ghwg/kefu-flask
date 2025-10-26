"""
Flask 扩展初始化
"""
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_wtf.csrf import CSRFProtect
from redis import Redis

# Flask 应用实例
app = Flask(__name__, static_url_path='/static', static_folder='static')

# 数据库 ORM
db = SQLAlchemy()

# 数据库迁移
migrate = Migrate()

# 登录管理
login_manager = LoginManager()

# 跨域支持
cors = CORS()

# CSRF 保护
csrf = CSRFProtect()

# SocketIO
socketio = SocketIO()

# Redis 客户端
redis_client = None

# 静态资源版本管理（性能优化：缓存控制）
from mod.utils.static_version import static_version_manager

# 项目根目录
root_dir = os.path.dirname(os.path.abspath(__file__))
