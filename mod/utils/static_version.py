"""
静态资源版本管理
自动为静态资源添加版本号，实现缓存控制
"""
import os
import hashlib
from flask import url_for
from functools import lru_cache


class StaticVersionManager:
    """
    静态资源版本管理器
    
    设计原则：
    - KISS: 基于文件MD5生成版本号
    - 性能: 使用LRU缓存避免重复计算
    """
    
    def __init__(self, app=None):
        """
        初始化
        
        Args:
            app: Flask应用实例
        """
        self.app = app
        self.static_folder = None
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """
        初始化Flask应用
        
        Args:
            app: Flask应用实例
        """
        self.app = app
        self.static_folder = app.static_folder
        
        # 注册Jinja2全局函数
        app.jinja_env.globals['static_v'] = self.static_v
    
    @lru_cache(maxsize=1000)
    def get_file_hash(self, filepath: str, length: int = 8) -> str:
        """
        获取文件MD5哈希值（带缓存）
        
        Args:
            filepath: 文件路径
            length: 哈希值长度（取前N位）
            
        Returns:
            文件哈希值
        """
        try:
            if not os.path.exists(filepath):
                # 文件不存在，返回时间戳作为版本号
                import time
                return str(int(time.time()))
            
            # 计算文件MD5
            md5 = hashlib.md5()
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    md5.update(chunk)
            
            return md5.hexdigest()[:length]
            
        except Exception as e:
            # 发生错误时返回固定值
            import time
            return str(int(time.time()))
    
    def static_v(self, filename: str) -> str:
        """
        生成带版本号的静态资源URL
        
        在模板中使用：
            <link rel="stylesheet" href="{{ static_v('css/style.css') }}">
            <script src="{{ static_v('js/app.js') }}"></script>
        
        生成的URL：
            /static/css/style.css?v=a1b2c3d4
        
        Args:
            filename: 静态资源路径（相对于static目录）
            
        Returns:
            带版本号的URL
        """
        # 生成基础URL
        base_url = url_for('static', filename=filename)
        
        # 获取文件完整路径
        if self.static_folder:
            filepath = os.path.join(self.static_folder, filename)
            version = self.get_file_hash(filepath)
            return f"{base_url}?v={version}"
        
        # 如果无法获取static_folder，返回基础URL
        return base_url
    
    def clear_cache(self):
        """
        清除缓存
        
        在静态文件更新后调用此方法，确保获取最新的版本号
        """
        self.get_file_hash.cache_clear()


# ========== 全局实例 ==========
static_version_manager = StaticVersionManager()


# ========== 使用示例 ==========
"""
# 在 app.py 或 exts.py 中初始化：

from mod.utils.static_version import static_version_manager

# 初始化
static_version_manager.init_app(app)


# 在模板中使用：

<!DOCTYPE html>
<html>
<head>
    <!-- 自动添加版本号 -->
    <link rel="stylesheet" href="{{ static_v('css/common/common.css') }}">
    <script src="{{ static_v('js/vendor/socket.io.min.js') }}"></script>
</head>
<body>
    <img src="{{ static_v('favicon.svg') }}" alt="Logo">
</body>
</html>


# 静态文件更新后清除缓存：

from mod.utils.static_version import static_version_manager

static_version_manager.clear_cache()
"""


