#!/bin/bash
################################################################################
# 应用重启脚本 (Linux/Mac)
# 用于应用优化后的重启
################################################################################

set -e

echo "================================================================================"
echo "应用重启脚本"
echo "================================================================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 显示优化信息
echo -e "${BLUE}📊 已完成的优化:${NC}"
echo "  ✅ MySQL连接超时修复"
echo "  ✅ 慢查询优化（4个索引已添加）"
echo "  ✅ 连接池自动清理任务"
echo "  ✅ 代码优化（缓存时间增加）"
echo ""

# 停止现有应用
echo -e "${YELLOW}[1/2] 正在停止现有应用...${NC}"

# 尝试多种方式停止应用
if pgrep -f "python.*app.py" > /dev/null; then
    echo "找到运行中的应用进程，正在停止..."
    pkill -f "python.*app.py" || true
    sleep 2
    echo -e "${GREEN}✅ 应用已停止${NC}"
elif pgrep -f "gunicorn" > /dev/null; then
    echo "找到运行中的Gunicorn进程，正在停止..."
    pkill -f "gunicorn" || true
    sleep 2
    echo -e "${GREEN}✅ Gunicorn已停止${NC}"
else
    echo -e "${BLUE}ℹ️ 未找到运行中的应用进程${NC}"
fi
echo ""

# 启动应用
echo -e "${YELLOW}[2/2] 正在启动应用...${NC}"
echo ""
echo "================================================================================"
echo "应用启动中..."
echo "================================================================================"
echo ""

# 检查启动脚本
if [ -f "start_production.sh" ]; then
    echo "使用生产环境启动脚本..."
    bash start_production.sh &
elif [ -f "app.py" ]; then
    echo "使用开发环境启动..."
    python app.py &
else
    echo -e "${RED}❌ 未找到启动脚本或app.py${NC}"
    exit 1
fi

# 等待启动
sleep 3

# 检查是否启动成功
if pgrep -f "python.*app.py" > /dev/null || pgrep -f "gunicorn" > /dev/null; then
    echo ""
    echo "================================================================================"
    echo -e "${GREEN}✅ 应用已成功启动！${NC}"
    echo "================================================================================"
    echo ""
    echo "后续步骤:"
    echo "1. 等待应用完全启动（约10-30秒）"
    echo "2. 访问管理后台查看统计页面"
    echo "3. 监控日志: tail -f logs/\$(date +%Y%m%d).log"
    echo ""
    echo "验证优化效果:"
    echo "- 统计页面应该加载更快"
    echo "- 慢查询警告应该消失或大幅减少"
    echo "- 查询时间应该 <0.5秒"
    echo ""
    echo "监控命令:"
    echo "  tail -f logs/\$(date +%Y%m%d).log | grep -E '(慢查询|连接池|健康检查)'"
    echo ""
else
    echo ""
    echo -e "${RED}❌ 应用启动失败，请检查日志${NC}"
    exit 1
fi
