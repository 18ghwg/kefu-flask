#!/bin/bash
# 修复 SQLAlchemy 和 alembic 版本兼容性问题

echo "当前版本："
pip show sqlalchemy alembic | grep -E "Name|Version"

echo ""
echo "升级到兼容版本组合..."
echo "SQLAlchemy 1.4.53 + alembic 1.8.1（支持旧语法 case([...])）"
pip install SQLAlchemy==1.4.53 alembic==1.8.1 --force-reinstall

echo ""
echo "升级后版本："
pip show sqlalchemy alembic | grep -E "Name|Version"

echo ""
echo "✅ 完成！请重启服务..."
# 根据你的实际情况调整重启命令
# systemctl restart your-service
# 或
# supervisorctl restart your-service
