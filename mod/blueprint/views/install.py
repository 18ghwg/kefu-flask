"""
系统安装向导
"""
from flask import Blueprint, render_template, request, jsonify, current_app
import os
import sys
import subprocess
import importlib.util
from pathlib import Path

# 创建蓝图，不指定static_folder，使用全局static
install_bp = Blueprint('install', __name__, url_prefix='/install')

# 导入 CSRF 对象用于豁免
from exts import csrf

# 定义install.lock文件路径
INSTALL_LOCK_PATH = Path(__file__).parent.parent.parent.parent / 'install' / 'install.lock'
INSTALL_DIR = Path(__file__).parent.parent.parent.parent / 'install'

# 确保install目录存在
INSTALL_DIR.mkdir(exist_ok=True)


def get_existing_db_config():
    """从config.py读取现有的数据库配置"""
    try:
        import config
        db_uri = getattr(config, 'SQLALCHEMY_DATABASE_URI', '')
        
        # 解析数据库URI
        # 格式: mysql+pymysql://user:password@host:port/dbname?charset=utf8mb4
        import re
        pattern = r'mysql\+pymysql://([^:]+):([^@]*)@([^:]+):(\d+)/([^\?]+)'
        match = re.match(pattern, db_uri)
        
        if match:
            return {
                'db_user': match.group(1),
                'db_password': match.group(2),
                'db_host': match.group(3),
                'db_port': match.group(4),
                'db_name': match.group(5)
            }
    except Exception as e:
        pass
    
    # 返回默认值
    return {
        'db_host': 'localhost',
        'db_port': '3306',
        'db_user': 'root',
        'db_password': '',
        'db_name': 'customer_service'
    }


def is_installed():
    """检查系统是否已安装"""
    return INSTALL_LOCK_PATH.exists()


@install_bp.route('/')
@csrf.exempt
def index():
    """安装向导首页"""
    if is_installed():
        return render_template('install/already_installed.html')
    
    # 尝试读取现有的数据库配置
    db_config = get_existing_db_config()
    
    return render_template('install/index.html', db_config=db_config)


@install_bp.route('/check-environment', methods=['POST'])
@csrf.exempt
def check_environment():
    """检查系统环境"""
    try:
        results = {
            'python_version': sys.version,
            'python_path': sys.executable,
            'checks': []
        }
        
        # 检查Python版本
        python_version = sys.version_info
        results['checks'].append({
            'name': 'Python版本',
            'status': 'success' if python_version >= (3, 7) else 'error',
            'message': f'{python_version.major}.{python_version.minor}.{python_version.micro}',
            'requirement': '需要Python 3.7+'
        })
        
        # 检查必需的Python包
        required_packages = [
            'flask',
            'flask_sqlalchemy',
            'flask_login',
            'flask_cors',
            'flask_socketio',
            'flask_migrate',
            'pymysql',
            'redis',
            'eventlet',
            'werkzeug'
        ]
        
        missing_packages = []
        installed_packages = []
        
        for package in required_packages:
            spec = importlib.util.find_spec(package)
            if spec is None:
                missing_packages.append(package)
                results['checks'].append({
                    'name': f'Python包: {package}',
                    'status': 'error',
                    'message': '未安装',
                    'requirement': '必需'
                })
            else:
                installed_packages.append(package)
                results['checks'].append({
                    'name': f'Python包: {package}',
                    'status': 'success',
                    'message': '已安装',
                    'requirement': '必需'
                })
        
        results['missing_packages'] = missing_packages
        results['installed_packages'] = installed_packages
        results['all_packages_installed'] = len(missing_packages) == 0
        
        # 检查写入权限
        try:
            test_file = INSTALL_DIR / 'test_write.tmp'
            test_file.write_text('test')
            test_file.unlink()
            results['checks'].append({
                'name': '文件写入权限',
                'status': 'success',
                'message': '可写',
                'requirement': '需要写入权限'
            })
        except Exception as e:
            results['checks'].append({
                'name': '文件写入权限',
                'status': 'error',
                'message': f'无法写入: {str(e)}',
                'requirement': '需要写入权限'
            })
        
        return jsonify({'code': 0, 'data': results})
        
    except Exception as e:
        return jsonify({'code': -1, 'msg': str(e)})


@install_bp.route('/install-packages', methods=['POST'])
@csrf.exempt
def install_packages():
    """一键安装缺失的包"""
    try:
        data = request.get_json()
        packages = data.get('packages', [])
        
        if not packages:
            return jsonify({'code': -1, 'msg': '没有需要安装的包'})
        
        results = []
        failed = []
        
        for package in packages:
            try:
                # 使用pip安装包
                result = subprocess.run(
                    [sys.executable, '-m', 'pip', 'install', package],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5分钟超时
                )
                
                if result.returncode == 0:
                    results.append({
                        'package': package,
                        'status': 'success',
                        'message': '安装成功'
                    })
                else:
                    failed.append(package)
                    results.append({
                        'package': package,
                        'status': 'error',
                        'message': result.stderr
                    })
            except subprocess.TimeoutExpired:
                failed.append(package)
                results.append({
                    'package': package,
                    'status': 'error',
                    'message': '安装超时'
                })
            except Exception as e:
                failed.append(package)
                results.append({
                    'package': package,
                    'status': 'error',
                    'message': str(e)
                })
        
        return jsonify({
            'code': 0 if len(failed) == 0 else -1,
            'data': {
                'results': results,
                'failed': failed,
                'success_count': len(packages) - len(failed),
                'total_count': len(packages)
            }
        })
        
    except Exception as e:
        return jsonify({'code': -1, 'msg': str(e)})


@install_bp.route('/test-database', methods=['POST'])
@csrf.exempt
def test_database():
    """测试数据库连接"""
    try:
        data = request.get_json()
        db_host = data.get('db_host', 'localhost')
        db_port = data.get('db_port', 3306)
        db_user = data.get('db_user', 'root')
        db_password = data.get('db_password', '')
        db_name = data.get('db_name', 'customer_service')
        
        import pymysql
        
        # 测试连接
        connection = pymysql.connect(
            host=db_host,
            port=int(db_port),
            user=db_user,
            password=db_password,
            charset='utf8mb4',
            connect_timeout=5
        )
        
        cursor = connection.cursor()
        
        # 检查数据库是否存在
        cursor.execute(f"SHOW DATABASES LIKE '{db_name}'")
        db_exists = cursor.fetchone() is not None
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'code': 0,
            'data': {
                'connected': True,
                'db_exists': db_exists,
                'message': '数据库连接成功' if db_exists else '连接成功，但数据库不存在'
            }
        })
        
    except Exception as e:
        return jsonify({
            'code': -1,
            'data': {
                'connected': False,
                'message': str(e)
            }
        })


@install_bp.route('/create-database', methods=['POST'])
@csrf.exempt
def create_database():
    """创建数据库"""
    try:
        data = request.get_json()
        db_host = data.get('db_host', 'localhost')
        db_port = data.get('db_port', 3306)
        db_user = data.get('db_user', 'root')
        db_password = data.get('db_password', '')
        db_name = data.get('db_name', 'customer_service')
        
        import pymysql
        
        connection = pymysql.connect(
            host=db_host,
            port=int(db_port),
            user=db_user,
            password=db_password,
            charset='utf8mb4'
        )
        
        cursor = connection.cursor()
        
        # 创建数据库
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'code': 0,
            'msg': f'数据库 {db_name} 创建成功'
        })
        
    except Exception as e:
        return jsonify({
            'code': -1,
            'msg': str(e)
        })


@install_bp.route('/initialize-database', methods=['POST'])
@csrf.exempt
def initialize_database():
    """初始化数据库表和数据"""
    import traceback
    import logging
    
    logger = logging.getLogger(__name__)
    
    # 添加调试输出
    print("=== 开始处理数据库初始化请求 ===")
    
    try:
        data = request.get_json()
        print(f"接收到的数据: {data}")
        
        if not data:
            print("错误: 无效的请求数据")
            return jsonify({
                'code': -1,
                'msg': '无效的请求数据'
            }), 400
        
        db_host = data.get('db_host', 'localhost')
        db_port = data.get('db_port', 3306)
        db_user = data.get('db_user', 'root')
        db_password = data.get('db_password', '')
        db_name = data.get('db_name', 'customer_service')
        admin_username = data.get('admin_username', 'admin')
        admin_password = data.get('admin_password', 'admin123')
        admin_email = data.get('admin_email', 'admin@example.com')
        
        logger.info(f"开始初始化数据库: {db_name}")
        
        # 构建新的数据库URI（但暂不更新config.py，避免触发Flask重启）
        new_db_uri = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"
        
        # 将数据库配置保存到临时文件，稍后在complete-install时更新
        temp_config_path = Path(__file__).parent.parent.parent.parent / 'install' / 'temp_db_config.txt'
        temp_config_path.write_text(new_db_uri, encoding='utf-8')
        logger.info("数据库配置已保存到临时文件")
        
        # 重新加载配置并初始化数据库
        # 使用独立的数据库连接
        import pymysql
        
        # 测试连接
        try:
            conn = pymysql.connect(
                host=db_host,
                port=int(db_port),
                user=db_user,
                password=db_password,
                database=db_name,
                charset='utf8mb4',
                connect_timeout=10
            )
            conn.close()
            logger.info("数据库连接测试成功")
            print("✓ 数据库连接测试成功")
        except pymysql.err.OperationalError as conn_err:
            error_msg = str(conn_err)
            if "Access denied" in error_msg or "1045" in error_msg:
                raise Exception("数据库认证失败，请检查用户名和密码")
            elif "Can't connect" in error_msg or "2003" in error_msg:
                raise Exception("无法连接到数据库服务器，请检查主机和端口是否正确")
            elif "Unknown database" in error_msg or "1049" in error_msg:
                raise Exception(f"数据库 '{db_name}' 不存在，请先在MySQL中创建该数据库")
            else:
                raise Exception(f"数据库连接失败: {error_msg}")
        except Exception as e:
            raise Exception(f"数据库连接测试失败: {str(e)}")
        
        # 直接初始化数据库（使用临时应用实例）
        logger.info("开始初始化数据库")
        
        # 先测试能否导入模型
        try:
            from mod.mysql.models import Service, Business, SystemSetting, CommentSetting, ServiceGroup
            from exts import db
            logger.info("模型导入成功")
        except Exception as model_err:
            logger.error(f"模型导入失败: {model_err}")
            raise Exception(f"模型导入失败: {str(model_err)}")
        
        # 创建临时Flask应用进行初始化（使用全局db对象）
        try:
            from flask import Flask
            
            temp_app = Flask(__name__)
            temp_app.config['SQLALCHEMY_DATABASE_URI'] = new_db_uri
            temp_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
            temp_app.config['SECRET_KEY'] = 'temp-install-key'
            
            # 初始化全局db对象到临时应用
            db.init_app(temp_app)
            logger.info("临时应用创建成功")
            
            with temp_app.app_context():
                # 步骤1: 创建所有表
                print(">>> 步骤1: 创建数据库表...")
                db.create_all()
                logger.info("数据库表创建成功")
                print("✓ 数据库表创建成功")
                
                # 步骤2: 创建默认商户
                print(">>> 步骤2: 初始化商户信息...")
                business = Business.query.first()
                if not business:
                    business = Business(
                        business_name='客服系统',
                        logo='',
                        copyright='(C) 2025 Customer Service System',
                        state='open',
                        lang='cn',
                        distribution_rule='auto',
                        video_state='close',
                        audio_state='close',
                        voice_state='open',
                        template_state='close',
                        voice_address='/static/voice/default.mp3'
                    )
                    db.session.add(business)
                    db.session.flush()
                    logger.info(f"商户创建成功: {business.id}")
                    print(f"✓ 商户创建成功 (ID: {business.id})")
                else:
                    logger.info(f"商户已存在: {business.id}")
                    print(f"✓ 商户已存在 (ID: {business.id})")
                
                # 步骤3: 创建管理员账号
                print(">>> 步骤3: 初始化管理员账号...")
                admin = Service.query.filter_by(user_name=admin_username).first()
                if admin:
                    admin.nick_name = '系统管理员'
                    admin.email = admin_email
                    admin.level = 'super_manager'
                    admin.password = admin_password
                    logger.info(f"管理员已存在，更新信息: {admin_username}")
                    print(f"✓ 管理员账号已存在，信息已更新: {admin_username}")
                else:
                    admin = Service(
                        user_name=admin_username,
                        nick_name='系统管理员',
                        business_id=business.id,
                        level='super_manager',
                        phone='',
                        email=admin_email,
                        state='offline',
                        avatar='/static/images/admin-avatar.png',
                        max_concurrent_chats=10,
                        auto_accept=1
                    )
                    admin.password = admin_password
                    db.session.add(admin)
                    logger.info(f"管理员创建成功: {admin_username}")
                    print(f"✓ 管理员账号创建成功: {admin_username}")
                
                # 步骤4: 创建系统设置
                print(">>> 步骤4: 初始化系统设置...")
                system_setting = SystemSetting.query.filter_by(business_id=business.id).first()
                if not system_setting:
                    system_setting = SystemSetting(
                        business_id=business.id,
                        upload_max_size=10485760,  # 10MB
                        upload_allowed_types='image,document,archive',
                        upload_image_max_size=5242880,  # 5MB
                        visitor_upload_allowed_types='image',
                        chat_welcome_text='您好，有什么可以帮助您的？',
                        chat_offline_text='当前客服不在线，请留言',
                        chat_queue_text='当前排队人数较多，请稍候',
                        greeting_message='欢迎使用客服系统，我们随时为您服务！',
                        robot_reply_mode='offline_only',
                        default_max_concurrent_chats=5,
                        session_timeout=1800,  # 30分钟
                        auto_close_timeout=300  # 5分钟
                    )
                    db.session.add(system_setting)
                    logger.info("系统设置创建成功")
                    print("✓ 系统设置初始化完成")
                else:
                    logger.info("系统设置已存在")
                    print("✓ 系统设置已存在")
                
                # 步骤5: 创建评价设置
                print(">>> 步骤5: 初始化评价设置...")
                import json
                comment_setting = CommentSetting.query.filter_by(business_id=business.id).first()
                if not comment_setting:
                    # 默认评价项
                    default_comments = [
                        {"title": "服务态度", "required": True},
                        {"title": "响应速度", "required": True},
                        {"title": "专业程度", "required": True},
                        {"title": "问题解决", "required": True}
                    ]
                    comment_setting = CommentSetting(
                        business_id=business.id,
                        title='请对本次服务进行评价',
                        comments=json.dumps(default_comments, ensure_ascii=False),
                        word_switch='open',
                        word_title='您的宝贵意见'
                    )
                    db.session.add(comment_setting)
                    logger.info("评价设置创建成功")
                    print("✓ 评价设置初始化完成")
                else:
                    logger.info("评价设置已存在")
                    print("✓ 评价设置已存在")
                
                # 步骤6: 创建默认客服分组
                print(">>> 步骤6: 初始化客服分组...")
                service_group = ServiceGroup.query.filter_by(business_id=business.id).first()
                if not service_group:
                    service_group = ServiceGroup(
                        business_id=business.id,
                        group_name='默认分组',
                        bgcolor='#667eea',
                        description='系统默认客服分组',
                        status=1,
                        sort=0
                    )
                    db.session.add(service_group)
                    logger.info("默认客服分组创建成功")
                    print("✓ 默认客服分组创建完成")
                else:
                    logger.info("客服分组已存在")
                    print("✓ 客服分组已存在")
                
                # 提交所有更改
                db.session.commit()
                logger.info("数据库初始化完成")
                print("=== 数据库初始化完成 ===")
                
        except Exception as init_err:
            # 回滚事务
            try:
                db.session.rollback()
                logger.warning("数据库事务已回滚")
                print("⚠️ 数据库事务已回滚")
            except Exception as rollback_err:
                logger.error(f"回滚失败: {rollback_err}")
                print(f"!!! 回滚失败: {rollback_err}")
            
            logger.error(f"初始化过程出错: {init_err}")
            print(f"!!! 初始化过程出错: {init_err}")
            import traceback
            logger.error(traceback.format_exc())
            print(traceback.format_exc())
            raise
        
        print("=== 准备返回成功响应 ===")
        return jsonify({
            'code': 0,
            'msg': '数据库初始化成功'
        })
        
    except Exception as e:
        error_trace = traceback.format_exc()
        logger.error(f"初始化失败: {e}\n{error_trace}")
        print(f"!!! 最外层捕获异常: {e}")
        print(error_trace)
        
        # 提供更友好的错误信息
        error_msg = str(e)
        if "Access denied" in error_msg or "1045" in error_msg:
            error_msg = "数据库认证失败，请检查用户名和密码"
        elif "Can't connect" in error_msg or "2003" in error_msg:
            error_msg = "无法连接到数据库服务器，请检查主机和端口"
        elif "Unknown database" in error_msg or "1049" in error_msg:
            error_msg = "数据库不存在，请先创建数据库"
        elif "导入失败" in error_msg:
            error_msg = "系统模块加载失败，请检查项目文件完整性"
        else:
            error_msg = f"初始化失败: {error_msg}"
        
        return jsonify({
            'code': -1,
            'msg': error_msg,
            'detail': error_trace if current_app.config.get('DEBUG', False) else None
        }), 500


@install_bp.route('/complete-install', methods=['POST'])
@csrf.exempt
def complete_install():
    """完成安装，创建install.lock文件"""
    try:
        from datetime import datetime
        import re
        
        print("=== 开始完成安装 ===")
        
        # 读取临时保存的数据库配置
        temp_config_path = Path(__file__).parent.parent.parent.parent / 'install' / 'temp_db_config.txt'
        if temp_config_path.exists():
            new_db_uri = temp_config_path.read_text(encoding='utf-8').strip()
            print(f"读取到数据库配置: {new_db_uri}")
            
            # 现在更新config.py（此时数据库已初始化完成）
            config_path = Path(__file__).parent.parent.parent.parent / 'config.py'
            if config_path.exists():
                config_content = config_path.read_text(encoding='utf-8')
                
                # 替换数据库配置
                config_content = re.sub(
                    r"SQLALCHEMY_DATABASE_URI\s*=\s*['\"].*?['\"]",
                    f'SQLALCHEMY_DATABASE_URI = "{new_db_uri}"',
                    config_content
                )
                
                config_path.write_text(config_content, encoding='utf-8')
                print("config.py已更新")
                
                # 删除临时配置文件
                temp_config_path.unlink()
                print("临时配置文件已删除")
        
        # 创建install.lock文件
        install_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        lock_content = f'''系统安装信息
==================
安装时间: {install_time}
状态: 已完成

警告: 删除此文件将允许重新安装系统！
重新安装将会重置管理员密码和部分配置。
'''
        
        INSTALL_LOCK_PATH.write_text(lock_content, encoding='utf-8')
        print("install.lock文件已创建")
        print("=== 安装完成 ===")
        
        return jsonify({
            'code': 0,
            'msg': '安装完成！请重启Flask应用以使配置生效。'
        })
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"!!! 完成安装失败: {e}")
        print(error_trace)
        return jsonify({
            'code': -1,
            'msg': f'创建锁定文件失败: {str(e)}',
            'detail': error_trace
        }), 500
