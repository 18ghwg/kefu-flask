"""
认证视图蓝图 - 登录、登出等页面路由
"""
from flask import Blueprint, request, render_template, redirect, url_for, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from mod.mysql.models import Service
from exts import db
import secrets
import hashlib
import time
import log

auth_view_bp = Blueprint('auth_view', __name__)
logger = log.get_logger(__name__)


# ========== 滑块验证码API ==========

@auth_view_bp.route('/api/captcha/generate', methods=['POST'])
def generate_captcha():
    """生成拼图滑块验证码"""
    from mod.utils.captcha_generator import PuzzleCaptchaGenerator
    
    try:
        # 生成拼图验证码
        generator = PuzzleCaptchaGenerator(width=300, height=150)
        captcha_data = generator.generate()
        
        # 生成唯一的验证token
        captcha_token = secrets.token_urlsafe(32)
        timestamp = int(time.time())
        
        # 保存到session（5分钟有效期）
        session['captcha'] = {
            'token': captcha_token,
            'x': captcha_data['x'],  # 拼图正确的X坐标
            'y': captcha_data['y'],  # 拼图的Y坐标
            'timestamp': timestamp,
            'ip': request.remote_addr
        }
        
        logger.debug(f"生成拼图验证码: token={captcha_token[:8]}..., x={captcha_data['x']}, y={captcha_data['y']}")
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {
                'token': captcha_token,
                'background': captcha_data['background'],  # 带缺口的背景图
                'puzzle': captcha_data['puzzle'],          # 拼图块
                'y': captcha_data['y']                     # Y坐标（固定，只需要X坐标滑动）
            }
        })
    except Exception as e:
        logger.error(f"生成验证码失败: {e}", exc_info=True)
        return jsonify({
            'code': -1,
            'msg': f'生成验证码失败: {str(e)}'
        }), 500


@auth_view_bp.route('/api/captcha/verify', methods=['POST'])
def verify_captcha():
    """验证拼图滑块位置"""
    data = request.get_json()
    
    if not data or not data.get('token') or data.get('x') is None:
        return jsonify({'code': 1, 'msg': '参数不完整'}), 400
    
    token = data['token']
    client_x = data['x']  # 客户端提交的X坐标（像素）
    
    # 从session获取验证信息
    captcha_data = session.get('captcha')
    
    if not captcha_data:
        return jsonify({'code': 2, 'msg': '验证码已过期，请刷新页面'}), 400
    
    # 验证token
    if captcha_data['token'] != token:
        return jsonify({'code': 3, 'msg': '验证码无效'}), 400
    
    # 验证IP
    if captcha_data['ip'] != request.remote_addr:
        return jsonify({'code': 4, 'msg': '验证失败'}), 400
    
    # 验证时间（5分钟内有效）
    if time.time() - captcha_data['timestamp'] > 300:
        session.pop('captcha', None)
        return jsonify({'code': 5, 'msg': '验证码已过期'}), 400
    
    # 验证位置（容差±10像素，考虑到不同屏幕尺寸的映射误差）
    target_x = captcha_data['x']
    tolerance = 10
    diff = abs(client_x - target_x)
    
    if diff <= tolerance:
        # 验证成功，生成验证令牌
        verify_token = secrets.token_urlsafe(32)
        session['captcha_verified'] = {
            'token': verify_token,
            'timestamp': time.time(),
            'ip': request.remote_addr
        }
        session.pop('captcha', None)  # 清除验证码数据
        
        logger.info(f"拼图验证码验证成功: {request.remote_addr}, client_x={client_x}, target_x={target_x}, diff={diff}")
        
        return jsonify({
            'code': 0,
            'msg': '验证成功',
            'data': {
                'verify_token': verify_token,
                'debug': {
                    'client_x': client_x,
                    'target_x': target_x,
                    'diff': diff
                }
            }
        })
    else:
        logger.warning(f"拼图验证码验证失败: client_x={client_x}, target_x={target_x}, diff={diff}, tolerance={tolerance}")
        return jsonify({
            'code': 6,
            'msg': f'位置不正确，请重试（差距: {diff}px）',
            'data': {
                'client_x': client_x,
                'target_x': target_x,
                'diff': diff,
                'tolerance': tolerance
            }
        }), 400


def check_captcha_verification():
    """检查验证码是否已验证（内部辅助函数）"""
    captcha_verified = session.get('captcha_verified')
    
    if not captcha_verified:
        return False, '请完成滑块验证'
    
    # 验证IP
    if captcha_verified['ip'] != request.remote_addr:
        session.pop('captcha_verified', None)
        return False, '验证失败'
    
    # 验证时间（10分钟内有效）
    if time.time() - captcha_verified['timestamp'] > 600:
        session.pop('captcha_verified', None)
        return False, '验证已过期，请重新验证'
    
    return True, ''


# ========== 页面路由 ==========

@auth_view_bp.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面和处理"""
    # 已登录用户直接跳转（使用url_for避免硬编码）
    if current_user.is_authenticated:
        if current_user.level in ['super_manager', 'manager']:
            return redirect(url_for('admin_panel.index'))
        else:
            return redirect(url_for('service_panel.chat'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') == '1'
        verify_token = request.form.get('verify_token')
        
        # 验证滑块验证码
        is_verified, error_msg = check_captcha_verification()
        if not is_verified:
            logger.warning(f"登录失败 - 验证码未通过: {username} - {error_msg}")
            return render_template('login.html', error=error_msg)
        
        # 验证verify_token
        captcha_verified = session.get('captcha_verified')
        if not captcha_verified or captcha_verified.get('token') != verify_token:
            logger.warning(f"登录失败 - verify_token不匹配: {username}")
            return render_template('login.html', error='验证失败，请重新验证')
        
        if not username or not password:
            return render_template('login.html', error='请输入用户名和密码')
        
        # 查找用户
        service = Service.query.filter_by(user_name=username).first()
        
        if not service:
            logger.warning(f"登录失败 - 用户不存在: {username}")
            return render_template('login.html', error='用户名或密码错误')
        
        # 验证密码
        if not service.verify_password(password):
            logger.warning(f"登录失败 - 密码错误: {username}")
            return render_template('login.html', error='用户名或密码错误')
        
        # 登录成功
        login_user(service, remember=remember)
        
        # 更新在线状态
        service.state = 'online'
        db.session.commit()
        
        # 清除验证码session
        session.pop('captcha_verified', None)
        
        logger.info(f"用户登录成功: {username} (level: {service.level})")
        
        # 根据权限跳转（使用url_for避免硬编码）
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        
        if service.level in ['super_manager', 'manager']:
            return redirect(url_for('admin_panel.index'))
        else:
            return redirect(url_for('service_panel.chat'))
    
    # GET请求，显示登录页面
    return render_template('login.html')


@auth_view_bp.route('/logout')
@login_required
def logout():
    """登出"""
    # 更新离线状态
    if current_user.is_authenticated:
        current_user.state = 'offline'
        db.session.commit()
        logger.info(f"用户登出: {current_user.user_name}")
    
    logout_user()
    
    # 重定向到登录页（使用url_for避免硬编码）
    return redirect(url_for('auth_view.login'))


@auth_view_bp.route('/register', methods=['GET', 'POST'])
def register():
    """注册页面（预留）"""
    # TODO: 实现注册功能
    return render_template('register.html')


@auth_view_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """忘记密码（预留）"""
    # TODO: 实现密码重置功能
    return render_template('forgot_password.html')
