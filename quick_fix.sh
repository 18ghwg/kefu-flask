#!/bin/bash
# 数据库连接池问题快速修复脚本

echo "=========================================="
echo "数据库连接池问题快速修复"
echo "=========================================="
echo ""

# 1. 检查当前连接池状态
echo "1. 检查当前连接池状态..."
python check_db_pool.py
echo ""

# 2. 清理连接
echo "2. 清理泄漏的数据库连接..."
python fix_db_connections.py
echo ""

# 3. 重启应用
echo "3. 重启应用..."
echo "请选择重启方式："
echo "  a) 使用 systemctl (推荐)"
echo "  b) 手动 kill 进程"
echo "  c) 跳过重启"
read -p "请输入选项 (a/b/c): " choice

case $choice in
    a)
        echo "使用 systemctl 重启..."
        sudo systemctl restart kefu-flask
        if [ $? -eq 0 ]; then
            echo "✅ 应用重启成功"
        else
            echo "❌ systemctl 重启失败，尝试手动重启"
            pkill -f "python.*app.py"
            pkill -f "gunicorn"
            sleep 2
            echo "✅ 进程已停止，请手动启动应用"
        fi
        ;;
    b)
        echo "手动停止进程..."
        pkill -f "python.*app.py"
        pkill -f "gunicorn"
        sleep 2
        echo "✅ 进程已停止，请手动启动应用"
        ;;
    c)
        echo "跳过重启"
        ;;
    *)
        echo "无效选项，跳过重启"
        ;;
esac

echo ""
echo "=========================================="
echo "修复完成！"
echo "=========================================="
echo ""
echo "后续建议："
echo "1. 监控日志: tail -f logs/error.log"
echo "2. 定期检查: python check_db_pool.py"
echo "3. 查看文档: cat DATABASE_CONNECTION_FIX.md"
echo ""
