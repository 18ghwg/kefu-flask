# MySQL连接超时问题修复包

## 📋 问题描述

应用出现MySQL连接超时错误：
```
pymysql.err.OperationalError: (2013, 'Lost connection to MySQL server during query (timed out)')
```

## 🎯 修复内容

### 已修复的问题
1. ✅ 数据库连接池配置不足
2. ✅ SocketIO断开连接时连接泄漏
3. ✅ 慢查询导致超时（10.974秒）
4. ✅ 异步线程未释放连接

### 修改的文件
- `config.py` - 优化连接池配置
- `socketio_events.py` - 修复连接泄漏

### 新增的工具
- `fix_connection_timeout.py` - 数据库优化脚本
- `monitor_db_health.py` - 健康监控工具
- `apply_connection_fix.sh` - 一键修复脚本（Linux/Mac）
- `apply_connection_fix.bat` - 一键修复脚本（Windows）

## 🚀 快速开始

### 方法1: 一键修复（推荐）

**Linux/Mac:**
```bash
bash apply_connection_fix.sh
```

**Windows:**
```cmd
apply_connection_fix.bat
```

### 方法2: 手动修复

#### 步骤1: 运行数据库优化
```bash
python fix_connection_timeout.py
```

#### 步骤2: 检查健康状况
```bash
python monitor_db_health.py
```

#### 步骤3: 重启应用
```bash
# Linux/Mac
pkill -f gunicorn
python app.py

# Windows
# 关闭现有Python进程，然后运行
python app.py
```

## 📊 关键配置变更

### 连接池优化
```python
# config.py
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_size": 25,          # 增加连接池大小
    "max_overflow": 50,       # 增加溢出连接
    "pool_timeout": 60,       # 增加获取连接超时
    "pool_recycle": 280,      # 优化回收时间
    "connect_args": {
        "read_timeout": 60,   # 支持慢查询
        "write_timeout": 60,
    }
}
```

### 连接泄漏修复
```python
# socketio_events.py
try:
    # 数据库操作
    db.session.commit()
except Exception as e:
    db.session.rollback()
finally:
    db.session.remove()  # ✅ 关键修复
```

## 🔧 工具使用

### 1. 数据库优化脚本
```bash
python fix_connection_timeout.py
```

功能：
- 添加数据库索引
- 清理重复数据
- 检查长时间运行的查询
- 检查连接池状态

### 2. 健康监控工具
```bash
# 单次检查
python monitor_db_health.py

# 持续监控（每30秒）
python monitor_db_health.py --continuous
```

功能：
- 监控连接池使用率
- 检测慢查询（>1秒）
- 检测表锁
- 监控MySQL连接数

## 📈 监控建议

### 实时监控
```bash
# 开发/测试环境
python monitor_db_health.py --continuous
```

### 定时任务
```bash
# 添加到crontab（Linux）
# 每小时检查一次
0 * * * * cd /path/to/app && python monitor_db_health.py >> logs/db_health.log 2>&1

# 每天凌晨2点优化
0 2 * * * cd /path/to/app && python fix_connection_timeout.py >> logs/db_fix.log 2>&1
```

### 日志监控
```bash
# 监控超时错误
tail -f logs/$(date +%Y%m%d).log | grep -i timeout

# 监控慢查询
tail -f logs/$(date +%Y%m%d).log | grep "慢查询"
```

## ✅ 验证清单

修复后请确认：
- [ ] 应用已重启
- [ ] 运行 `fix_connection_timeout.py` 成功
- [ ] 运行 `monitor_db_health.py` 显示健康
- [ ] 观察日志30分钟无超时错误
- [ ] 连接池使用率 < 60%
- [ ] 无慢查询警告

## 🆘 故障排查

### 问题1: 仍然出现超时
```bash
# 检查连接池状态
python monitor_db_health.py

# 查看MySQL连接
mysql -u root -p -e "SHOW PROCESSLIST;"

# 临时增加连接池（config.py）
pool_size = 50
max_overflow = 100
```

### 问题2: 连接池耗尽
```bash
# 检查是否有连接泄漏
grep -r "db.session" --include="*.py" | grep -v "remove"

# 确保所有数据库操作都有 finally: db.session.remove()
```

### 问题3: 慢查询
```bash
# 运行优化脚本
python fix_connection_timeout.py

# 手动添加索引
mysql -u kefu_flask -p kefu_flask
> CREATE INDEX idx_business_id ON system_settings(business_id);
```

## 📚 文档

- **MYSQL_TIMEOUT_FIX.md** - 完整修复文档
- **QUICK_FIX_GUIDE.md** - 快速修复指南
- **CONNECTION_FIX_SUMMARY.txt** - 修复摘要

## 🔍 预期效果

### 修复前
- ❌ 频繁连接超时
- ❌ 慢查询10.974秒
- ❌ 连接池经常耗尽

### 修复后
- ✅ 无连接超时错误
- ✅ 查询时间 < 1秒
- ✅ 连接池使用率 < 60%
- ✅ 系统稳定运行

## 💡 最佳实践

### 代码规范
```python
# ✅ 正确：使用try-finally
try:
    result = db.session.query(Model).all()
    db.session.commit()
except Exception as e:
    db.session.rollback()
    logger.error(f"错误: {e}")
finally:
    db.session.remove()

# ❌ 错误：不释放连接
result = db.session.query(Model).all()
db.session.commit()
```

### 异步任务
```python
# ✅ 正确：异步任务中使用独立会话
def async_task():
    try:
        with app.app_context():
            # 数据库操作
            pass
    finally:
        db.session.remove()

Thread(target=async_task, daemon=True).start()
```

## 📞 技术支持

如需帮助，请提供：
1. 日志文件：`logs/YYYYMMDD.log`
2. 诊断报告：`python monitor_db_health.py > diagnosis.txt`
3. MySQL状态：`SHOW FULL PROCESSLIST;`
4. 错误截图

---

**修复版本：** 1.0  
**修复日期：** 2026-02-01  
**预计修复时间：** 5-10分钟  
**风险等级：** 低  
**影响范围：** 数据库连接管理
