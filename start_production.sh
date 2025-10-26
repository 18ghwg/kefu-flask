#!/bin/bash
# ========================================
# Flask 客服系统 - 生产环境启动脚本
# 使用 Gunicorn + Eventlet 支持 WebSocket
# ========================================

# 项目路径
PROJECT_DIR="/www/wwwroot/kefu-flask"

# 切换到项目目录
cd ${PROJECT_DIR}

# 激活虚拟环境（如果使用了虚拟环境）
# source venv/bin/activate

# 确保安装了必要的依赖
echo "检查依赖..."
pip list | grep -q "gunicorn" || pip install gunicorn
pip list | grep -q "eventlet" || pip install eventlet

# 启动 Gunicorn
# -k eventlet: 使用 eventlet worker（支持 WebSocket）
# -w 4: 4个 worker 进程
# -b 127.0.0.1:8000: 绑定到本地 8000 端口（由 Nginx 代理）
# --timeout 120: 超时时间 120 秒（WebSocket 长连接需要）
# --worker-connections 1000: 每个 worker 最大连接数
# --log-level info: 日志级别
# --access-logfile: 访问日志文件
# --error-logfile: 错误日志文件
# app:app: 入口文件:应用对象

echo "正在启动 Flask 客服系统..."

gunicorn \
    -k eventlet \
    -w 4 \
    -b 127.0.0.1:8000 \
    --timeout 120 \
    --worker-connections 1000 \
    --log-level info \
    --access-logfile /www/wwwlogs/kefu-flask-access.log \
    --error-logfile /www/wwwlogs/kefu-flask-error.log \
    --pid /www/wwwroot/kefu-flask/gunicorn.pid \
    app:app

echo "启动完成！"

