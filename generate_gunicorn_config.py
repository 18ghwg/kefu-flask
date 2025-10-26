#!/usr/bin/env python3
"""
Gunicorn 配置文件生成器
自动检测项目路径和系统资源，生成适配当前环境的 Gunicorn 配置

使用方法：
    python generate_gunicorn_config.py [--port PORT] [--workers WORKERS] [--user USER]

示例：
    # 使用默认配置（自动检测CPU核心数）
    python generate_gunicorn_config.py
    
    # 指定端口和worker数量
    python generate_gunicorn_config.py --port 8000 --workers 4
    
    # 指定运行用户
    python generate_gunicorn_config.py --user www --group www
"""
import os
import sys
import argparse
import multiprocessing
import pwd
import grp


def get_project_root():
    """获取项目根目录（当前脚本所在目录）"""
    return os.path.dirname(os.path.abspath(__file__))


def detect_cpu_cores():
    """检测CPU核心数并计算推荐的worker数量"""
    try:
        cpu_count = multiprocessing.cpu_count()
        # 推荐公式：CPU核心数 * 2 + 1
        recommended_workers = cpu_count * 2 + 1
        return cpu_count, recommended_workers
    except Exception:
        return 1, 4  # 默认值


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
    log_dir = os.path.join(project_root, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def get_current_user():
    """获取当前用户名"""
    try:
        return pwd.getpwuid(os.getuid()).pw_name
    except Exception:
        return 'www'


def get_current_group():
    """获取当前用户组"""
    try:
        return grp.getgrgid(os.getgid()).gr_name
    except Exception:
        return 'www'


def generate_config(template_file, output_file, config_vars):
    """
    生成Gunicorn配置文件
    
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
        description='生成适配当前环境的Gunicorn配置文件',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='Gunicorn监听端口（默认：8000）'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=None,
        help='Worker进程数（默认：自动检测，CPU核心数 * 2 + 1）'
    )
    parser.add_argument(
        '--user',
        default=None,
        help='运行用户（默认：当前用户）'
    )
    parser.add_argument(
        '--group',
        default=None,
        help='运行用户组（默认：当前用户组）'
    )
    parser.add_argument(
        '--log-dir',
        default=None,
        help='日志目录（默认：自动检测）'
    )
    parser.add_argument(
        '--output',
        default='gunicorn_config.py',
        help='输出文件名（默认：gunicorn_config.py）'
    )
    
    args = parser.parse_args()
    
    # 获取项目根目录
    project_root = get_project_root()
    
    # 检测CPU核心数
    cpu_count, recommended_workers = detect_cpu_cores()
    workers = args.workers if args.workers else recommended_workers
    
    # 自动检测或使用用户指定的配置
    user = args.user or get_current_user()
    group = args.group or get_current_group()
    log_dir = args.log_dir or detect_log_directory()
    
    # 配置变量
    config_vars = {
        'PROJECT_ROOT': project_root,
        'GUNICORN_PORT': args.port,
        'WORKERS': workers,
        'USER': user,
        'GROUP': group,
        'LOG_DIR': log_dir,
    }
    
    # 模板文件路径
    template_file = os.path.join(project_root, 'gunicorn_config.py.template')
    output_file = os.path.join(project_root, args.output)
    
    # 检查模板文件是否存在
    if not os.path.exists(template_file):
        print(f"[ERROR] 模板文件不存在：{template_file}")
        print(f"   请确保 gunicorn_config.py.template 文件在项目根目录")
        sys.exit(1)
    
    # 生成配置文件
    try:
        generate_config(template_file, output_file, config_vars)
        
        print("=" * 60)
        print("[SUCCESS] Gunicorn配置文件生成成功！")
        print("=" * 60)
        print(f"[项目根目录]      {project_root}")
        print(f"[监听端口]        127.0.0.1:{args.port}")
        print(f"[CPU核心数]       {cpu_count}")
        print(f"[Worker进程数]    {workers}")
        print(f"[运行用户]        {user}:{group}")
        print(f"[日志目录]        {log_dir}")
        print(f"[输出文件]        {output_file}")
        print("=" * 60)
        print()
        print("[下一步操作]")
        print(f"   1. 测试配置文件:")
        print(f"      gunicorn -c {args.output} app:app --check-config")
        print(f"   2. 启动应用:")
        print(f"      gunicorn -c {args.output} app:app")
        print(f"   3. 后台运行（生产环境）:")
        print(f"      nohup gunicorn -c {args.output} app:app > /dev/null 2>&1 &")
        print()
        print("[提示]")
        print(f"   - Worker数量基于CPU核心数自动计算（{cpu_count} * 2 + 1 = {workers}）")
        print(f"   - 如需调整，使用 --workers 参数重新生成")
        print(f"   - 宝塔用户可在Python项目管理中使用此配置")
        print("=" * 60)
        
    except Exception as e:
        print(f"[ERROR] 生成配置文件失败")
        print(f"   {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()

