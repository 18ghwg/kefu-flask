"""
全局配置文件（示例）
复制此文件为 config.py 并填写实际配置
"""
import os
from datetime import timedelta

# 加载环境变量（从 .env 文件）
try:
    from dotenv import load_dotenv
    load_dotenv()  # 自动加载项目根目录的 .env 文件
except ImportError:
    # 如果未安装 python-dotenv，继续使用系统环境变量
    pass

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ========== 数据库配置 ==========
HOSTNAME = ''  # 数据库主机地址，如：localhost 或 185.242.235.37
PORT = ''      # 数据库端口，默认：3306
DATABASE = ''  # 数据库名称
USERNAME = ''  # 数据库用户名
PASSWORD = ''  # 数据库密码

# 数据库连接 URI
SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{USERNAME}:{PASSWORD}@{HOSTNAME}:{PORT}/{DATABASE}?charset=utf8mb4'
SQLALCHEMY_TRACK_MODIFICATIONS = False

# 数据库连接池优化（解决长时间不请求后延迟问题）
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_pre_ping": True,        # 连接前测试可用性
    "pool_recycle": 300,          # 5分钟回收连接
    "pool_size": 15,              # 连接池大小
    "max_overflow": 30,           # 最大溢出连接数
    "pool_timeout": 10,           # 获取连接超时
    "connect_args": {
        "connect_timeout": 5,     # MySQL 连接超时
        "read_timeout": 10,       # 读取超时
        "write_timeout": 10,      # 写入超时
    }
}

# ========== Flask 配置 ==========
SECRET_KEY = 'your-secret-key-here'  # 请修改为随机字符串
DEBUG = True

# Session 配置
PERMANENT_SESSION_LIFETIME = timedelta(days=7)

# ========== CSRF 保护配置 ==========
# CSRF Token 配置
WTF_CSRF_ENABLED = True  # 启用 CSRF 保护
WTF_CSRF_TIME_LIMIT = None  # Token 永不过期（使用 Session 生命周期）
WTF_CSRF_SSL_STRICT = False  # 开发环境可以设为 False，生产环境建议设为 True
WTF_CSRF_CHECK_DEFAULT = True  # 默认对所有 POST/PUT/PATCH/DELETE 请求进行 CSRF 验证

# CSRF Token 字段名称
WTF_CSRF_FIELD_NAME = 'csrf_token'
WTF_CSRF_HEADERS = ['X-CSRFToken', 'X-CSRF-Token']  # 允许从请求头获取 CSRF Token

# CSRF 豁免路径（不需要 CSRF 验证的路径）
# 注意：以 / 结尾表示匹配该路径下的所有子路径
CSRF_EXEMPT_ROUTES = [
    '/api/auth/login',  # 登录接口（还没有 session）
    '/api/visitor/register',  # 访客注册（还没有 session）
    '/api/csrf-token',  # CSRF Token获取接口
    '/health',  # 健康检查
    '/install/',  # 安装向导（包括所有子路径）
]

# ========== Redis 配置 ==========
# 支持从环境变量读取 Redis 配置
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = os.getenv('REDIS_PORT', '6379')
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')  # 从环境变量读取密码
REDIS_DB = os.getenv('REDIS_DB', '0')

# 构建 Redis URL（自动处理密码）
def build_redis_url(host, port, password, db):
    """构建 Redis 连接 URL，自动处理密码"""
    if password:
        return f'redis://:{password}@{host}:{port}/{db}'
    else:
        return f'redis://{host}:{port}/{db}'

REDIS_URL = build_redis_url(REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_DB)
CELERY_BROKER_URL = build_redis_url(REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, '1')
CELERY_RESULT_BACKEND = build_redis_url(REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, '2')

# ========== SocketIO 配置 ==========
SOCKETIO_MESSAGE_QUEUE = build_redis_url(REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, '3')
SOCKETIO_ASYNC_MODE = 'eventlet'

# ========== 文件上传配置 ==========
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'xls', 'xlsx'}

# ========== 日志配置 ==========
LOG_LEVEL = 'INFO'
LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'app.log')

# ========== 分页配置 ==========
PAGE_SIZE = 20

# ========== API 配置 ==========
# API 签名验证
API_SIGNATURE_SECRET = 'your-api-secret-here'  # 请修改为随机字符串
API_SIGNATURE_EXPIRE = 300  # 5分钟

# ========== 业务配置 ==========
# 微信机器人配置（如需要）
WECHAT_API_URL = 'http://localhost:5603/send'

# 系统名称
SYSTEM_NAME = '客服系统'
SYSTEM_DESCRIPTION = '智能客服管理平台'
SYSTEM_VERSION = '1.0.0'

# ========== 密码加密 ==========
PASSWORD_SALT = 'your-password-salt-here'  # 请修改为随机字符串

# 确保必要的目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

