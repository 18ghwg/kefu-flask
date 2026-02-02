# MySQL连接超时 - 快速修复指南

## 🚨 问题症状
```
pymysql.err.OperationalError: (2013, 'Lost connection to MySQL server during query (timed out)')
```

## ⚡ 快速修复（3步）

### 步骤1: 应用代码修复
已修复的文件：
- ✅ `config.py` - 优化连接池配置
- ✅ `socketio_events.py` - 修复连接泄漏

**重启应用：**
```bash
# 停止现有进程
pkill -f gunicorn
# 或
ps aux | grep python | grep app.py | awk '{print $2}' | xargs kill

# 重新启动
python app.py
# 或使用你的启动脚本
./start_production.sh
```

### 步骤2: 运行数据库优化
```bash
python fix_connection_timeout.py
```

预期输出：
```
✅ 连接池状态正常
✅ 添加数据库索引
✅ 优化system_settings查询
✅ 没有发现长时间运行的查询
```

### 步骤3: 验证修复
```bash
# 检查数据库健康
python monitor_db_health.py

# 查看应用日志（无超时错误）
tail -f logs/20260202.log | grep -i timeout
```

## 📊 关键配置变更

### config.py
```python
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_recycle": 280,      # 4分40秒回收（避免MySQL 300秒超时）
    "pool_size": 25,          # 连接池大小
    "max_overflow": 50,       # 最大溢出连接
    "pool_timeout": 60,       # 获取连接超时
    "connect_args": {
        "read_timeout": 60,   # 读取超时（支持慢查询）
        "write_timeout": 60,  # 写入超时
    }
}
```

### socketio_events.py
```python
# 所有数据库操作添加：
try:
    # ... 数据库操作 ...
    db.session.commit()
except Exception as e:
    db.session.rollback()
finally:
    db.session.remove()  # ✅ 关键：释放连接
```

## 🔍 故障排查

### 问题1: 仍然超时
```bash
# 检查MySQL连接数
python monitor_db_health.py

# 查看慢查询
tail -f logs/20260202.log | grep "慢查询"
```

**解决：** 增加 `pool_size` 到 30-40

### 问题2: 连接池耗尽
```bash
# 症状：QueuePool limit reached
```

**解决：** 检查代码是否有连接泄漏
```python
# 搜索所有 db.session 使用
grep -r "db.session" --include="*.py" | grep -v "remove"
```

### 问题3: 慢查询
```bash
# 运行优化脚本
python fix_connection_timeout.py

# 手动添加索引
mysql -u kefu_flask -p kefu_flask
> CREATE INDEX idx_business_id ON system_settings(business_id);
```

## 📈 监控建议

### 实时监控
```bash
# 持续监控（每30秒检查）
python monitor_db_health.py --continuous
```

### 定时任务（crontab）
```bash
# 每小时检查一次
0 * * * * cd /www/wwwroot/kefu-flask && python monitor_db_health.py >> logs/db_health.log 2>&1

# 每天凌晨2点优化
0 2 * * * cd /www/wwwroot/kefu-flask && python fix_connection_timeout.py >> logs/db_fix.log 2>&1
```

## ✅ 验证清单

- [ ] 重启应用服务
- [ ] 运行 `fix_connection_timeout.py`
- [ ] 运行 `monitor_db_health.py` 确认健康
- [ ] 观察日志30分钟无超时错误
- [ ] 设置定期监控任务

## 🆘 紧急处理

如果生产环境正在出现大量超时：

```bash
# 1. 立即重启应用（释放所有连接）
pkill -f gunicorn && python app.py

# 2. 检查MySQL连接
mysql -u root -p -e "SHOW PROCESSLIST;" | grep kefu_flask

# 3. 终止长时间运行的查询（谨慎！）
mysql -u root -p -e "KILL <process_id>;"

# 4. 临时增加连接池（修改config.py）
pool_size = 50
max_overflow = 100
```

## 📞 需要帮助？

收集以下信息：
1. 日志文件：`logs/20260202.log`
2. 诊断报告：`python monitor_db_health.py > diagnosis.txt`
3. MySQL状态：`SHOW FULL PROCESSLIST;`
4. 错误截图

---

**修复完成时间：** 2026-02-01  
**预计修复时间：** 5-10分钟  
**影响范围：** 数据库连接管理  
**风险等级：** 低（仅优化配置）
