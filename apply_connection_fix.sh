#!/bin/bash
################################################################################
# MySQL连接超时问题 - 一键修复脚本
# 使用方法：bash apply_connection_fix.sh
################################################################################

set -e  # 遇到错误立即退出

echo "================================================================================"
echo "MySQL连接超时问题 - 自动修复"
echo "================================================================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查Python环境
echo -e "${YELLOW}[1/5] 检查Python环境...${NC}"
if ! command -v python &> /dev/null; then
    echo -e "${RED}❌ Python未安装${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python环境正常${NC}"
echo ""

# 备份配置文件
echo -e "${YELLOW}[2/5] 备份配置文件...${NC}"
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp config.py "$BACKUP_DIR/config.py.bak" 2>/dev/null || true
cp socketio_events.py "$BACKUP_DIR/socketio_events.py.bak" 2>/dev/null || true
echo -e "${GREEN}✅ 备份完成: $BACKUP_DIR${NC}"
echo ""

# 运行数据库优化
echo -e "${YELLOW}[3/5] 运行数据库优化...${NC}"
if python fix_connection_timeout.py; then
    echo -e "${GREEN}✅ 数据库优化完成${NC}"
else
    echo -e "${RED}❌ 数据库优化失败，请检查日志${NC}"
    exit 1
fi
echo ""

# 检查数据库健康
echo -e "${YELLOW}[4/5] 检查数据库健康...${NC}"
if python monitor_db_health.py; then
    echo -e "${GREEN}✅ 数据库健康检查通过${NC}"
else
    echo -e "${YELLOW}⚠️ 数据库健康检查有警告，请查看详情${NC}"
fi
echo ""

# 重启应用提示
echo -e "${YELLOW}[5/5] 应用重启...${NC}"
echo -e "${YELLOW}请手动重启应用以应用新配置：${NC}"
echo ""
echo "  方法1: 使用进程管理器"
echo "    pkill -f gunicorn"
echo "    python app.py"
echo ""
echo "  方法2: 使用启动脚本"
echo "    ./start_production.sh"
echo ""
echo "  方法3: 使用systemd"
echo "    sudo systemctl restart kefu-flask"
echo ""

# 完成
echo "================================================================================"
echo -e "${GREEN}✅ 修复完成！${NC}"
echo "================================================================================"
echo ""
echo "后续步骤："
echo "1. 重启应用服务"
echo "2. 观察日志：tail -f logs/$(date +%Y%m%d).log"
echo "3. 监控健康：python monitor_db_health.py --continuous"
echo ""
echo "如有问题，请查看："
echo "- 详细文档：MYSQL_TIMEOUT_FIX.md"
echo "- 快速指南：QUICK_FIX_GUIDE.md"
echo "- 修复摘要：CONNECTION_FIX_SUMMARY.txt"
echo ""
