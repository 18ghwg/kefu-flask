"""
文件上传API蓝图
支持安全检查、文件类型限制、大小限制、MD5重命名
"""
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
import os
import hashlib
import mimetypes
from datetime import datetime
import log

upload_bp = Blueprint('upload', __name__, url_prefix='/api/upload')
logger = log.get_logger(__name__)

# 导入CSRF对象用于豁免
from exts import csrf

# 允许的文件扩展名（默认）
ALLOWED_EXTENSIONS = {
    'image': {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'},
    'document': {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt'},
    'archive': {'zip', 'rar', '7z', 'tar', 'gz'},
    'video': {'mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv'},
    'audio': {'mp3', 'wav', 'ogg', 'aac', 'm4a'}
}

# 默认最大文件大小（10MB）
MAX_FILE_SIZE = 10 * 1024 * 1024

# 危险文件扩展名（不允许上传）
DANGEROUS_EXTENSIONS = {
    'exe', 'bat', 'cmd', 'com', 'pif', 'scr', 'vbs', 'js', 
    'jar', 'msi', 'sh', 'py', 'rb', 'pl', 'php', 'asp', 'jsp',
    'cgi', 'dll', 'so', 'dylib', 'app', 'deb', 'rpm', 'apk',
    'htm', 'html', 'xml', 'svg'  # 可能包含XSS的文件
}


def get_file_md5(file_content):
    """计算文件MD5值"""
    md5_hash = hashlib.md5()
    md5_hash.update(file_content)
    return md5_hash.hexdigest()


def is_allowed_file(filename, allowed_types=None):
    """
    检查文件是否允许上传
    
    Args:
        filename: 文件名
        allowed_types: 允许的文件类型列表，如 ['image', 'document']
                      如果为None，则允许所有非危险文件
    
    Returns:
        (bool, str): (是否允许, 错误信息)
    """
    if '.' not in filename:
        return False, '文件名无效'
    
    ext = filename.rsplit('.', 1)[1].lower()
    
    # 检查是否是危险文件
    if ext in DANGEROUS_EXTENSIONS:
        return False, f'不允许上传 .{ext} 类型的文件（安全限制）'
    
    # 如果没有指定类型限制，允许所有非危险文件
    if allowed_types is None:
        return True, ''
    
    # 检查是否在允许的类型中
    for file_type in allowed_types:
        if file_type in ALLOWED_EXTENSIONS and ext in ALLOWED_EXTENSIONS[file_type]:
            return True, ''
    
    return False, f'不允许上传 .{ext} 类型的文件'


def sanitize_filename(filename):
    """清理文件名，防止路径遍历攻击"""
    # 移除路径分隔符
    filename = filename.replace('/', '').replace('\\', '')
    # 移除..
    filename = filename.replace('..', '')
    # 使用werkzeug的secure_filename
    filename = secure_filename(filename)
    # 限制文件名长度
    if len(filename) > 200:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:195] + ('.' + ext if ext else '')
    return filename


def validate_file_content(file_content, expected_ext):
    """
    验证文件内容与扩展名是否匹配（检查文件头）
    
    Args:
        file_content: 文件二进制内容
        expected_ext: 期望的扩展名
    
    Returns:
        (bool, str): (是否有效, 错误信息)
    """
    # 文件签名（Magic Bytes）映射
    file_signatures = {
        'jpg': [b'\xFF\xD8\xFF'],
        'jpeg': [b'\xFF\xD8\xFF'],
        'png': [b'\x89\x50\x4E\x47'],
        'gif': [b'\x47\x49\x46\x38'],
        'pdf': [b'\x25\x50\x44\x46'],
        'zip': [b'\x50\x4B\x03\x04', b'\x50\x4B\x05\x06', b'\x50\x4B\x07\x08'],
        'rar': [b'\x52\x61\x72\x21'],
        'bmp': [b'\x42\x4D'],
        'webp': [b'\x52\x49\x46\x46'],
    }
    
    if not file_content or len(file_content) < 8:
        return False, '文件内容无效'
    
    # 如果扩展名不在签名列表中，允许通过（暂不验证）
    if expected_ext not in file_signatures:
        return True, ''
    
    # 检查文件头是否匹配
    signatures = file_signatures[expected_ext]
    for sig in signatures:
        if file_content.startswith(sig):
            return True, ''
    
    return False, f'文件内容与扩展名不匹配，可能是伪造的.{expected_ext}文件'


@upload_bp.route('/file', methods=['POST'])
@csrf.exempt  # ✅ CSRF豁免：支持访客上传（访客无token）
def upload_file():
    """
    上传文件接口（访客和客服都可以使用，不需要登录）
    
    请求参数：
        file: 文件对象
        visitor_id: 访客ID（可选）
        business_id: 商户ID（可选）
    
    返回：
        {
            'code': 0,
            'msg': 'success',
            'data': {
                'url': '/static/uploads/xxx.jpg',
                'name': '原始文件名.jpg',
                'size': 12345,
                'md5': 'abc123...',
                'mime_type': 'image/jpeg'
            }
        }
    """
    try:
        # 检查文件是否存在
        if 'file' not in request.files:
            return jsonify({'code': -1, 'msg': '没有文件'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'code': -1, 'msg': '文件名为空'}), 400
        
        # 获取原始文件名
        original_filename = file.filename
        logger.info(f'接收文件上传: {original_filename}')
        
        # 清理文件名
        safe_filename = sanitize_filename(original_filename)
        
        # 检查文件类型
        # TODO: 从系统设置中读取允许的类型
        allowed, error_msg = is_allowed_file(safe_filename, ['image', 'document', 'archive'])
        if not allowed:
            return jsonify({'code': -1, 'msg': error_msg}), 400
        
        # 读取文件内容
        file_content = file.read()
        file_size = len(file_content)
        
        # 获取文件扩展名
        file_ext = safe_filename.rsplit('.', 1)[1].lower() if '.' in safe_filename else ''
        
        # 验证文件内容（检查文件头magic bytes）
        content_valid, content_error = validate_file_content(file_content, file_ext)
        if not content_valid:
            logger.warning(f'文件内容验证失败: {safe_filename} - {content_error}')
            return jsonify({'code': -1, 'msg': content_error}), 400
        
        # 检查文件大小
        # TODO: 从系统设置中读取最大大小
        max_size = MAX_FILE_SIZE
        if file_size > max_size:
            max_mb = max_size / (1024 * 1024)
            return jsonify({'code': -1, 'msg': f'文件太大，最大支持 {max_mb:.0f}MB'}), 400
        
        # 计算MD5
        file_md5 = get_file_md5(file_content)
        
        # 生成新文件名（MD5 + 扩展名）
        new_filename = f'{file_md5}.{file_ext}' if file_ext else file_md5
        
        # 按日期创建子目录
        date_dir = datetime.now().strftime('%Y%m')
        upload_dir = os.path.join(current_app.static_folder, 'uploads', date_dir)
        
        # 确保目录存在
        os.makedirs(upload_dir, exist_ok=True)
        
        # 完整文件路径
        file_path = os.path.join(upload_dir, new_filename)
        
        # 检查文件是否已存在（MD5相同则不重复保存）
        if os.path.exists(file_path):
            logger.info(f'文件已存在（MD5相同），跳过保存: {new_filename}')
        else:
            # 保存文件
            with open(file_path, 'wb') as f:
                f.write(file_content)
            logger.info(f'文件保存成功: {file_path}')
        
        # 生成访问URL
        file_url = f'/static/uploads/{date_dir}/{new_filename}'
        
        # 获取MIME类型
        mime_type, _ = mimetypes.guess_type(safe_filename)
        if mime_type is None:
            mime_type = 'application/octet-stream'
        
        # 返回文件信息
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {
                'url': file_url,
                'name': original_filename,
                'size': file_size,
                'md5': file_md5,
                'mime_type': mime_type
            }
        })
        
    except Exception as e:
        logger.error(f'文件上传失败: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'code': -1, 'msg': f'上传失败: {str(e)}'}), 500


@upload_bp.route('/image', methods=['POST'])
@csrf.exempt  # ✅ CSRF豁免：支持访客上传（访客无token）
def upload_image():
    """
    上传图片接口（限制只能上传图片，不需要登录）
    """
    try:
        if 'file' not in request.files:
            return jsonify({'code': -1, 'msg': '没有文件'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'code': -1, 'msg': '文件名为空'}), 400
        
        safe_filename = sanitize_filename(file.filename)
        
        # 只允许图片
        allowed, error_msg = is_allowed_file(safe_filename, ['image'])
        if not allowed:
            return jsonify({'code': -1, 'msg': '只允许上传图片文件'}), 400
        
        # 复用upload_file的逻辑
        return upload_file()
        
    except Exception as e:
        logger.error(f'图片上传失败: {e}')
        return jsonify({'code': -1, 'msg': f'上传失败: {str(e)}'}), 500
