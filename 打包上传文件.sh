#!/bin/bash
################################################################################
# 打包需要上传的文件 (Linux/Mac)
################################################################################

set -e

echo "================================================================================"
echo "打包上传文件"
echo "================================================================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# 创建打包目录
PACKAGE_DIR="upload_package_$(date +%Y%m%d_%H%M%S)"

echo "创建打包目录: $PACKAGE_DIR"
mkdir -p "$PACKAGE_DIR/mod/mysql/ModuleClass"
mkdir -p "$PACKAGE_DIR/Tasks"

echo ""
echo -e "${BLUE}[1/4] 复制核心文件...${NC}"

# 核心文件
[ -f config.py ] && cp config.py "$PACKAGE_DIR/" && echo "  ✓ config.py"
[ -f socketio_events.py ] && cp socketio_events.py "$PACKAGE_DIR/" && echo "  ✓ socketio_events.py"
[ -f mod/mysql/ModuleClass/StatisticsServiceClass.py ] && cp mod/mysql/ModuleClass/StatisticsServiceClass.py "$PACKAGE_DIR/mod/mysql/ModuleClass/" && echo "  ✓ StatisticsServiceClass.py"
[ -f Tasks/db_health_check.py ] && cp Tasks/db_health_check.py "$PACKAGE_DIR/Tasks/" && echo "  ✓ Tasks/db_health_check.py"
[ -f Tasks/task_list.py ] && cp Tasks/task_list.py "$PACKAGE_DIR/Tasks/" && echo "  ✓ Tasks/task_list.py"
[ -f Tasks/__init__.py ] && cp Tasks/__init__.py "$PACKAGE_DIR/Tasks/" && echo "  ✓ Tasks/__init__.py"

echo ""
echo -e "${BLUE}[2/4] 复制工具脚本...${NC}"

[ -f fix_connection_timeout.py ] && cp fix_connection_timeout.py "$PACKAGE_DIR/" && echo "  ✓ fix_connection_timeout.py"
[ -f optimize_slow_queries.py ] && cp optimize_slow_queries.py "$PACKAGE_DIR/" && echo "  ✓ optimize_slow_queries.py"
[ -f monitor_db_health.py ] && cp monitor_db_health.py "$PACKAGE_DIR/" && echo "  ✓ monitor_db_health.py"
[ -f restart_app.sh ] && cp restart_app.sh "$PACKAGE_DIR/" && echo "  ✓ restart_app.sh"

echo ""
echo -e "${BLUE}[3/4] 复制文档文件...${NC}"

[ -f MYSQL_TIMEOUT_FIX.md ] && cp MYSQL_TIMEOUT_FIX.md "$PACKAGE_DIR/"
[ -f SLOW_QUERY_FIX.md ] && cp SLOW_QUERY_FIX.md "$PACKAGE_DIR/"
[ -f QUICK_FIX_GUIDE.md ] && cp QUICK_FIX_GUIDE.md "$PACKAGE_DIR/"
[ -f Tasks/README.md ] && cp Tasks/README.md "$PACKAGE_DIR/Tasks/"
[ -f 优化完成报告.txt ] && cp 优化完成报告.txt "$PACKAGE_DIR/"
[ -f 慢查询修复说明.txt ] && cp 慢查询修复说明.txt "$PACKAGE_DIR/"
[ -f 修复完成说明.txt ] && cp 修复完成说明.txt "$PACKAGE_DIR/"
[ -f 上传文件清单.txt ] && cp 上传文件清单.txt "$PACKAGE_DIR/"
echo "  ✓ 文档文件已复制"

echo ""
echo -e "${BLUE}[4/4] 创建上传说明...${NC}"

# 创建上传说明文件
cat > "$PACKAGE_DIR/上传说明.txt" << 'EOF'
╔════════════════════════════════════════════════════════════════════════════╗
║                    上传说明                                                 ║
╚════════════════════════════════════════════════════════════════════════════╝

【上传方法】

方法1: 使用SCP（推荐）
  scp -r * root@your-server:/www/wwwroot/kefu-flask/

方法2: 使用rsync
  rsync -avz * root@your-server:/www/wwwroot/kefu-flask/

方法3: 使用FTP客户端
  1. 连接到服务器
  2. 导航到 /www/wwwroot/kefu-flask/
  3. 上传此目录中的所有文件

【上传后操作】

1. SSH登录服务器
   ssh root@your-server

2. 进入项目目录
   cd /www/wwwroot/kefu-flask

3. 设置权限
   chmod +x restart_app.sh
   chmod +x *.py

4. 运行优化脚本
   python fix_connection_timeout.py
   python optimize_slow_queries.py

5. 重启应用
   bash restart_app.sh

6. 验证效果
   tail -f logs/$(date +%Y%m%d).log | grep -E "(慢查询|连接池)"

【核心文件】
  ✓ config.py - 连接池配置优化
  ✓ socketio_events.py - 连接泄漏修复
  ✓ StatisticsServiceClass.py - 慢查询优化
  ✓ Tasks/db_health_check.py - 自动化任务
  ✓ Tasks/task_list.py - 任务配置

【工具脚本】
  ✓ fix_connection_timeout.py - 连接优化
  ✓ optimize_slow_queries.py - 慢查询优化
  ✓ monitor_db_health.py - 健康监控
  ✓ restart_app.sh - 重启脚本

【预期效果】
  - 无连接超时错误
  - 慢查询警告消失
  - 统计页面加载更快
  - 连接池使用率正常

EOF

# 创建快速上传脚本
cat > "$PACKAGE_DIR/快速上传.sh" << 'EOF'
#!/bin/bash
# 快速上传脚本 - 请先修改服务器地址

SERVER="root@your-server"
TARGET_DIR="/www/wwwroot/kefu-flask"

echo "上传文件到服务器..."
echo "服务器: $SERVER"
echo "目标目录: $TARGET_DIR"
echo ""

# 上传文件
scp -r * "$SERVER:$TARGET_DIR/"

echo ""
echo "上传完成！"
echo ""
echo "下一步: SSH登录服务器执行以下命令"
echo "  ssh $SERVER"
echo "  cd $TARGET_DIR"
echo "  chmod +x restart_app.sh *.py"
echo "  python fix_connection_timeout.py"
echo "  python optimize_slow_queries.py"
echo "  bash restart_app.sh"
EOF

chmod +x "$PACKAGE_DIR/快速上传.sh"

echo ""
echo "================================================================================"
echo -e "${GREEN}✅ 打包完成！${NC}"
echo "================================================================================"
echo ""
echo "打包目录: $PACKAGE_DIR"
echo ""
echo "文件列表:"
ls -lh "$PACKAGE_DIR"
echo ""
echo "下一步:"
echo "1. 进入打包目录: cd $PACKAGE_DIR"
echo "2. 修改快速上传.sh中的服务器地址"
echo "3. 运行上传脚本: bash 快速上传.sh"
echo "   或手动上传: scp -r * root@your-server:/www/wwwroot/kefu-flask/"
echo "4. 查看上传说明.txt了解详细步骤"
echo ""
