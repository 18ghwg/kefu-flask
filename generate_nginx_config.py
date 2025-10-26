#!/usr/bin/env python3
"""
Nginx 配置文件生成器
自动检测项目路径并生成适配当前环境的 nginx 配置

使用方法：
    python generate_nginx_config.py [--server-name SERVER_NAME] [--port PORT] [--gunicorn-port GUNICORN_PORT]

示例：
    # 使用默认配置
    python generate_nginx_config.py
    
    # 自定义服务器名称和端口
    python generate_nginx_config.py --server-name example.com --port 80
    
    # 指定Gunicorn端口
    python generate_nginx_config.py --gunicorn-port 8000
"""
import os
import sys
import argparse
import socket


def get_project_root():
    """获取项目根目录（当前脚本所在目录）"""
    return os.path.dirname(os.path.abspath(__file__))


def get_server_ip():
    """获取服务器IP地址"""
    try:
        # 获取主机名
        hostname = socket.gethostname()
        # 获取IP地址
        ip_address = socket.gethostbyname(hostname)
        return ip_address
    except Exception:
        return "localhost"


def detect_log_directory():
    """检测日志目录（常见的Web服务器日志目录）"""
    common_log_dirs = [
        '/www/wwwlogs',           # 宝塔面板
        '/var/log/nginx',          # 标准Nginx
        '/usr/local/var/log/nginx', # macOS Homebrew
        '/opt/homebrew/var/log/nginx', # macOS Apple Silicon
    ]
    
    for log_dir in common_log_dirs:
        if os.path.exists(log_dir) and os.path.isdir(log_dir):
            return log_dir
    
    # 如果都不存在，使用项目内的logs目录
    project_root = get_project_root()
    return os.path.join(project_root, 'logs')


def generate_config(template_file, output_file, config_vars):
    """
    生成Nginx配置文件
    
    Args:
        template_file: 模板文件路径
        output_file: 输出文件路径
        config_vars: 配置变量字典
    """
    # 读取模板
    with open(template_file, 'r', encoding='utf-8') as f:
        template_content = f.read()
    
    # 替换变量
    config_content = template_content
    for key, value in config_vars.items():
        config_content = config_content.replace(f'{{{{{key}}}}}', str(value))
    
    # 写入配置文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(config_content)
    
    return output_file


def main():
    parser = argparse.ArgumentParser(
        description='生成适配当前环境的Nginx配置文件',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--server-name',
        default=None,
        help='服务器域名或IP（默认：自动检测）'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=5302,
        help='Nginx监听端口（默认：5302）'
    )
    parser.add_argument(
        '--gunicorn-port',
        type=int,
        default=8000,
        help='Gunicorn内部端口（默认：8000）'
    )
    parser.add_argument(
        '--log-dir',
        default=None,
        help='日志目录（默认：自动检测）'
    )
    parser.add_argument(
        '--output',
        default='nginx_correct.conf',
        help='输出文件名（默认：nginx_correct.conf）'
    )
    
    args = parser.parse_args()
    
    # 获取项目根目录
    project_root = get_project_root()
    
    # 自动检测或使用用户指定的配置
    server_name = args.server_name or get_server_ip()
    log_dir = args.log_dir or detect_log_directory()
    
    # 配置变量
    config_vars = {
        'PROJECT_ROOT': project_root,
        'SERVER_NAME': server_name,
        'NGINX_PORT': args.port,
        'GUNICORN_PORT': args.gunicorn_port,
        'LOG_DIR': log_dir,
    }
    
    # 模板文件路径
    template_file = os.path.join(project_root, 'nginx_correct.conf.template')
    output_file = os.path.join(project_root, args.output)
    
    # 检查模板文件是否存在
    if not os.path.exists(template_file):
        print(f"[ERROR] 模板文件不存在：{template_file}")
        print(f"   请确保 nginx_correct.conf.template 文件在项目根目录")
        sys.exit(1)
    
    # 生成配置文件
    try:
        generate_config(template_file, output_file, config_vars)
        
        print("=" * 60)
        print("[SUCCESS] Nginx配置文件生成成功！")
        print("=" * 60)
        print(f"[项目根目录]      {project_root}")
        print(f"[服务器地址]      {server_name}")
        print(f"[Nginx监听端口]   {args.port}")
        print(f"[Gunicorn端口]    {args.gunicorn_port}")
        print(f"[日志目录]        {log_dir}")
        print(f"[输出文件]        {output_file}")
        print("=" * 60)
        print()
        print("[下一步操作]")
        print(f"   1. 复制配置到Nginx目录:")
        print(f"      sudo cp {args.output} /etc/nginx/sites-available/kefu-flask.conf")
        print(f"   2. 创建软链接启用配置:")
        print(f"      sudo ln -s /etc/nginx/sites-available/kefu-flask.conf /etc/nginx/sites-enabled/")
        print(f"   3. 测试配置文件:")
        print(f"      sudo nginx -t")
        print(f"   4. 重载Nginx:")
        print(f"      sudo systemctl reload nginx")
        print()
        print("[提示]")
        print(f"   - 如需修改配置，编辑模板文件后重新运行此脚本")
        print(f"   - 宝塔用户可直接在面板中粘贴配置内容")
        print("=" * 60)
        
    except Exception as e:
        print(f"[ERROR] 生成配置文件失败")
        print(f"   {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()

