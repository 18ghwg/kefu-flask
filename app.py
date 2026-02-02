"""
Flask 应用入口
"""
# ========== Eventlet Monkey Patch (必须在所有导入之前) ==========
import eventlet
eventlet.monkey_patch()

import os
from flask import request, session, g, render_template, jsonify, redirect, url_for
from flask_migrate import Migrate
from flask_login import login_required
from exts import app, db, login_manager, cors, csrf, socketio, redis_client
import config
import log

# 导入WebSocket事件处理
import socketio_events

# ========== 配置加载 ==========
app.config.from_object(config)

# 日志配置（必须在Redis初始化之前）
logger = log.get_logger(__name__)

# ========== 扩展初始化 ==========
db.init_app(app)
Migrate(app, db)
login_manager.init_app(app)
cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

# CSRF 保护初始化
csrf.init_app(app)

# 静态资源版本管理初始化（性能优化）
from mod.utils.static_version import static_version_manager
static_version_manager.init_app(app)

# Redis 初始化
try:
    from redis import Redis
    import exts
    redis_url = config.REDIS_URL
    exts.redis_client = Redis.from_url(redis_url, decode_responses=True)
    # 测试连接
    exts.redis_client.ping()
    logger.info(f"✅ Redis连接成功: {redis_url}")
except Exception as e:
    logger.warning(f"⚠️ Redis连接失败: {e}，将不使用缓存功能")
    exts.redis_client = None

# SocketIO 初始化
socketio.init_app(
    app,
    message_queue=config.SOCKETIO_MESSAGE_QUEUE,
    async_mode=config.SOCKETIO_ASYNC_MODE,
    cors_allowed_origins="*"
)

# ========== 蓝图注册 ==========
from mod.blueprint.auth import auth_bp
from mod.blueprint.visitor import visitor_bp
from mod.blueprint.service import service_bp
from mod.blueprint.admin import admin_bp
from mod.blueprint.robot import robot_bp
from mod.blueprint.comment import comment_bp
from mod.blueprint.queue import queue_bp
from mod.blueprint.upload import upload_bp
from mod.blueprint.rating import rating_bp  # ✅ 客服评价
from mod.blueprint.question import question_bp
from mod.blueprint.operation_log import operation_log_bp
from mod.blueprint.assignment import assignment_bp

app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(visitor_bp, url_prefix='/api/visitor')
app.register_blueprint(service_bp, url_prefix='/api/service')
app.register_blueprint(admin_bp, url_prefix='/api/admin')
app.register_blueprint(robot_bp, url_prefix='/api/robot')
app.register_blueprint(comment_bp, url_prefix='/api/comment')
app.register_blueprint(queue_bp, url_prefix='/api/queue')
app.register_blueprint(upload_bp)  # url_prefix已在Blueprint定义时设置为 /api/upload
app.register_blueprint(question_bp)  # url_prefix已在Blueprint定义时设置为 /api/question
app.register_blueprint(operation_log_bp)  # url_prefix已在Blueprint定义时设置为 /api/operation-log
app.register_blueprint(assignment_bp, url_prefix='/api/assignment')  # 智能分配API
app.register_blueprint(rating_bp)  # ✅ 客服评价 (url_prefix已在Blueprint定义时设置为 /api/rating)

# ========== 视图蓝图注册 ==========
from mod.blueprint.views.index import index_bp
from mod.blueprint.views.service_panel import service_panel_bp
from mod.blueprint.views.admin_panel import admin_panel_bp
from mod.blueprint.views.visitor import visitor_view_bp
from mod.blueprint.views.install import install_bp
from mod.blueprint.views.auth import auth_view_bp

app.register_blueprint(index_bp, url_prefix='/')
app.register_blueprint(service_panel_bp, url_prefix='/service')
app.register_blueprint(admin_panel_bp, url_prefix='/admin')
app.register_blueprint(visitor_view_bp, url_prefix='/visitor')
app.register_blueprint(install_bp)  # install_bp已在定义时设置url_prefix
app.register_blueprint(auth_view_bp, url_prefix='/')  # 认证视图（登录、登出等）


# ========== 请求生命周期管理 ==========
# ========== Jinja2全局函数 ==========
@app.context_processor
def inject_globals():
    """注入全局模板变量和函数"""
    from datetime import datetime
    return {
        'now': datetime.now,  # 提供now函数
        'datetime': datetime   # 提供datetime模块
    }


@app.before_request
def before_request():
    """请求前处理"""
    # 跳过静态文件、安装路由和favicon的检查
    skip_paths = ['/static/', '/install', '/favicon.ico']
    should_skip = any(request.path.startswith(path) for path in skip_paths)
    
    # 检查安装状态（排除特殊路径）
    if not should_skip:
        from pathlib import Path
        install_lock = Path(__file__).parent / 'install' / 'install.lock'
        if not install_lock.exists():
            # 如果未安装，重定向到安装向导（使用url_for避免硬编码）
            return redirect(url_for('install.index'))
    
    # 设置 Session 永久有效（排除静态文件）
    if not request.path.startswith('/static/'):
        session.permanent = True
    
    # CSRF 豁免检查（对特定路径跳过 CSRF 验证）
    csrf_exempt_routes = app.config.get('CSRF_EXEMPT_ROUTES', [])
    # 支持精确匹配和前缀匹配（以 / 结尾表示匹配所有子路径）
    for route in csrf_exempt_routes:
        if route.endswith('/') and request.path.startswith(route):
            # Flask-WTF 识别这个标志来豁免 CSRF 检查
            setattr(g, '_csrf_exempt', True)
            logger.info(f"✅ CSRF 豁免: {request.path} 匹配规则 {route}")
            break
        elif request.path == route:
            setattr(g, '_csrf_exempt', True)
            logger.info(f"✅ CSRF 豁免: {request.path} 精确匹配 {route}")
            break
    
    # 如果没有豁免，记录日志（仅在非静态文件时）
    if not getattr(g, '_csrf_exempt', False) and not request.path.startswith('/static/'):
        logger.info(f"⚠️ CSRF 检查: {request.path} 需要验证，方法: {request.method}")
    
    # 记录请求信息（开发环境）
    if app.config['DEBUG']:
        logger.debug(f"Request: {request.method} {request.path}")


@app.after_request
def after_request(response):
    """响应后处理 - 添加安全头部"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response


@app.teardown_appcontext
def shutdown_session(exception=None):
    """
    请求结束后清理数据库会话
    ✅ 关键修复：确保每个请求后都释放数据库连接
    """
    db.session.remove()


# ========== 数据库连接池预热 ==========
def warmup_db_pool():
    """
    数据库连接池预热
    避免首次请求延迟
    """
    try:
        with app.app_context():
            logger.info("开始预热数据库连接池...")
            for i in range(10):
                result = db.session.execute(db.text("SELECT 1"))
                result.fetchone()
            db.session.commit()
            logger.info("✅ 数据库连接池预热完成")
    except Exception as e:
        logger.error(f"❌ 数据库连接池预热失败: {e}")


@app.before_first_request
def init_after_startup():
    """应用启动后初始化"""
    warmup_db_pool()
    
    # 启动会话监控定时任务
    try:
        from mod.tasks import start_session_monitor
        start_session_monitor(app, socketio)
    except Exception as e:
        logger.error(f"启动会话监控任务失败: {e}")
    
    # 初始化性能监控（性能优化）
    try:
        from mod.utils.performance_monitor import init_performance_monitoring, DatabaseQueryMonitor
        init_performance_monitoring(app)
        DatabaseQueryMonitor.init_app(app)
        logger.info("✅ 性能监控已启动")
    except Exception as e:
        logger.warning(f"⚠️ 性能监控启动失败: {e}")
    
    logger.info(f"🚀 {config.SYSTEM_NAME} v{config.SYSTEM_VERSION} 启动成功")


# ========== Flask-Login 用户加载 ==========
@login_manager.user_loader
def load_user(service_id):
    """加载用户"""
    from mod.mysql.models import Service
    try:
        return Service.query.get(int(service_id))
    except Exception as e:
        # 数据库表不存在或其他错误时返回 None（允许访问安装向导）
        logger.debug(f"加载用户失败: {e}")
        return None


login_manager.login_view = 'auth_view.login'
login_manager.login_message = '请先登录'


# ========== 错误处理 ==========
@app.errorhandler(400)
def csrf_error(error):
    """
    CSRF验证失败处理
    - API请求：返回JSON错误
    - 页面请求：跳转到CSRF验证页面
    """
    from flask_wtf.csrf import CSRFError
    
    # 检查是否是CSRF错误
    if isinstance(error, CSRFError):
        logger.warning(f"CSRF验证失败 - {request.method} {request.path} - IP: {request.remote_addr}")
        
        # API请求返回JSON
        if request.path.startswith('/api/'):
            return jsonify({
                'code': 400,
                'msg': 'CSRF验证失败，请刷新页面后重试',
                'error': 'CSRF token missing or invalid'
            }), 400
        
        # 页面请求跳转到CSRF验证页面
        return render_template('csrf_verify.html'), 400
    
    # 其他400错误
    if request.path.startswith('/api/'):
        return jsonify({'code': 400, 'msg': '请求参数错误'}), 400
    return render_template('400.html'), 400


@app.errorhandler(404)
def not_found_error(error):
    """404 错误处理"""
    if request.path.startswith('/api/'):
        return jsonify({'code': 404, 'msg': '资源不存在'}), 404
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    """500 错误处理"""
    db.session.rollback()
    logger.error(f"服务器错误: {error}", exc_info=True)
    if request.path.startswith('/api/'):
        return jsonify({'code': 500, 'msg': '服务器错误'}), 500
    return render_template('500.html'), 500


@app.errorhandler(Exception)
def handle_exception(e):
    """全局异常处理"""
    logger.error(f"未捕获的异常: {e}", exc_info=True)
    
    # 如果是数据库表不存在的错误，且访问的是安装向导，允许继续
    if "Table" in str(e) and "doesn't exist" in str(e):
        if request.path.startswith('/install'):
            # 清除 session 中的用户 ID，避免重复查询
            from flask import session
            session.pop('_user_id', None)
            # 重定向到安装页面（使用url_for避免硬编码）
            return redirect(url_for('install.index'))
    
    if request.path.startswith('/api/'):
        return jsonify({'code': 500, 'msg': '服务器错误'}), 500
    
    # 渲染500页面时也可能失败（表不存在），使用try-except
    try:
        return render_template('500.html'), 500
    except:
        return f'<h1>服务器错误</h1><p>系统遇到错误，请访问 <a href="/install/">/install/</a> 进行安装。</p>', 500


# ========== 主页路由 ==========
@app.route('/')
def home():
    """主页 - 系统介绍页"""
    return render_template('home.html')

@app.route('/favicon.ico')
def favicon():
    """返回网站图标"""
    from flask import send_from_directory
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.svg',
        mimetype='image/svg+xml'
    )



# ========== CSRF Token 获取接口 ==========
@app.route('/api/csrf-token', methods=['GET'])
def get_csrf_token():
    """
    获取CSRF Token
    前端可以通过此接口获取CSRF Token
    """
    from flask_wtf.csrf import generate_csrf
    token = generate_csrf()
    return jsonify({
        'code': 0,
        'csrf_token': token
    })


# ========== 健康检查 ==========
@app.route('/health')
def health():
    """健康检查接口"""
    try:
        # 检查数据库连接
        db.session.execute(db.text("SELECT 1"))
        db.session.commit()
        
        return jsonify({
            'status': 'healthy',
            'service': config.SYSTEM_NAME,
            'version': config.SYSTEM_VERSION
        })
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500


# ========== Shell 上下文 ==========
@app.shell_context_processor
def make_shell_context():
    """Shell 上下文"""
    from mod.mysql import models
    return {
        'db': db,
        'models': models,
        'config': config
    }


# ========== 应用启动 ==========
if __name__ == '__main__':
    # 开发环境使用 SocketIO 运行
    socketio.run(
        app,
        host='127.0.0.1',
        port=5302,
        debug=config.DEBUG
    )