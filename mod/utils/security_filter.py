"""
安全过滤器 - 防止SSTI、XSS、SQL注入等攻击
"""
import re
import html
from flask import Markup
import logging

logger = logging.getLogger(__name__)


class SecurityFilter:
    """安全过滤器类"""
    
    # SSTI危险关键词（Jinja2模板注入）
    SSTI_PATTERNS = [
        r'\{\{.*\}\}',  # {{}}
        r'\{%.*%\}',    # {%%}
        r'\{#.*#\}',    # {##}
        r'__import__',
        r'__class__',
        r'__mro__',
        r'__subclasses__',
        r'__globals__',
        r'__builtins__',
        r'__code__',
        r'__init__',
        r'__dict__',
        r'config',
        r'self',
        r'request\.',
        r'session\.',
        r'g\.',
    ]
    
    # 危险函数调用
    DANGEROUS_FUNCTIONS = [
        'eval', 'exec', 'compile', '__import__',
        'open', 'file', 'input', 'raw_input',
        'execfile', 'reload', 'vars', 'dir',
        'getattr', 'setattr', 'delattr', 'hasattr',
        'callable', 'isinstance', 'issubclass',
    ]
    
    # XSS危险标签
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'<iframe[^>]*>.*?</iframe>',
        r'javascript:',
        r'onerror\s*=',
        r'onload\s*=',
        r'onclick\s*=',
        r'<embed[^>]*>',
        r'<object[^>]*>',
    ]
    
    @classmethod
    def sanitize_message_content(cls, content, max_length=5000):
        """
        清理消息内容
        
        Args:
            content: 原始消息内容
            max_length: 最大长度限制
        
        Returns:
            清理后的安全内容
        """
        if not content or not isinstance(content, str):
            return ''
        
        # 1. 长度限制
        if len(content) > max_length:
            logger.warning(f"消息内容超长，已截断: {len(content)} -> {max_length}")
            content = content[:max_length]
        
        # 2. 检测并阻止SSTI攻击
        if cls.detect_ssti(content):
            logger.warning(f"检测到SSTI攻击尝试: {content[:100]}")
            return "[消息包含非法内容，已被系统拦截]"
        
        # 3. 检测并清理XSS攻击
        if cls.detect_xss(content):
            logger.warning(f"检测到XSS攻击尝试: {content[:100]}")
            content = cls.remove_xss(content)
        
        # 4. HTML转义（保护特殊字符）
        content = html.escape(content)
        
        # 5. 移除危险字符
        content = cls.remove_dangerous_chars(content)
        
        return content
    
    @classmethod
    def detect_ssti(cls, content):
        """
        检测SSTI攻击模式
        
        Args:
            content: 要检测的内容
        
        Returns:
            True如果检测到威胁，否则False
        """
        content_lower = content.lower()
        
        # 检查SSTI模式
        for pattern in cls.SSTI_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                logger.warning(f"SSTI模式匹配: {pattern}")
                return True
        
        # 检查危险函数
        for func in cls.DANGEROUS_FUNCTIONS:
            if func in content_lower:
                logger.warning(f"危险函数检测: {func}")
                return True
        
        return False
    
    @classmethod
    def detect_xss(cls, content):
        """
        检测XSS攻击模式
        
        Args:
            content: 要检测的内容
        
        Returns:
            True如果检测到威胁，否则False
        """
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                logger.warning(f"XSS模式匹配: {pattern}")
                return True
        
        return False
    
    @classmethod
    def remove_xss(cls, content):
        """
        移除XSS攻击代码
        
        Args:
            content: 原始内容
        
        Returns:
            清理后的内容
        """
        for pattern in cls.XSS_PATTERNS:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        return content
    
    @classmethod
    def remove_dangerous_chars(cls, content):
        """
        移除危险字符
        
        Args:
            content: 原始内容
        
        Returns:
            清理后的内容
        """
        # 移除NULL字节
        content = content.replace('\x00', '')
        
        # 移除其他控制字符（保留换行、制表符）
        content = re.sub(r'[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]', '', content)
        
        return content
    
    @classmethod
    def validate_visitor_id(cls, visitor_id):
        """
        验证访客ID格式
        
        Args:
            visitor_id: 访客ID
        
        Returns:
            True如果有效，否则False
        """
        if not visitor_id or not isinstance(visitor_id, str):
            return False
        
        # 访客ID应该是visitor_开头的格式
        if not re.match(r'^visitor_\d+_\d+$', visitor_id):
            logger.warning(f"非法访客ID格式: {visitor_id}")
            return False
        
        return True
    
    @classmethod
    def sanitize_filename(cls, filename):
        """
        清理文件名，防止路径遍历攻击
        
        Args:
            filename: 原始文件名
        
        Returns:
            安全的文件名
        """
        if not filename:
            return 'unnamed'
        
        # 移除路径分隔符
        filename = filename.replace('/', '_').replace('\\', '_')
        
        # 移除..
        filename = filename.replace('..', '')
        
        # 只保留安全字符
        filename = re.sub(r'[^\w\s\-\.]', '_', filename)
        
        # 限制长度
        if len(filename) > 100:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            filename = name[:95] + ('.' + ext if ext else '')
        
        return filename
    
    @classmethod
    def validate_url(cls, url):
        """
        验证URL安全性
        
        Args:
            url: 要验证的URL
        
        Returns:
            True如果安全，否则False
        """
        if not url:
            return False
        
        # 阻止危险协议
        dangerous_protocols = ['javascript:', 'data:', 'vbscript:', 'file:']
        url_lower = url.lower()
        
        for protocol in dangerous_protocols:
            if url_lower.startswith(protocol):
                logger.warning(f"检测到危险URL协议: {url[:50]}")
                return False
        
        return True
    
    @classmethod
    def sanitize_sql_input(cls, value):
        """
        清理SQL输入（SQLAlchemy通常会自动处理，但额外检查）
        
        Args:
            value: 输入值
        
        Returns:
            清理后的值
        """
        if not isinstance(value, str):
            return value
        
        # 检测SQL注入关键词
        sql_keywords = ['union', 'select', 'insert', 'update', 'delete', 
                       'drop', 'create', 'alter', 'exec', 'execute']
        
        value_lower = value.lower()
        for keyword in sql_keywords:
            if re.search(r'\b' + keyword + r'\b', value_lower):
                logger.warning(f"检测到潜在SQL注入: {value[:100]}")
                # 不直接拦截，因为可能是正常内容，但记录日志
        
        return value


# 快捷函数
def sanitize_message(content, max_length=5000):
    """快捷函数：清理消息内容"""
    return SecurityFilter.sanitize_message_content(content, max_length)


def validate_visitor_id(visitor_id):
    """快捷函数：验证访客ID"""
    return SecurityFilter.validate_visitor_id(visitor_id)


def sanitize_filename(filename):
    """快捷函数：清理文件名"""
    return SecurityFilter.sanitize_filename(filename)


def validate_url(url):
    """快捷函数：验证URL"""
    return SecurityFilter.validate_url(url)

