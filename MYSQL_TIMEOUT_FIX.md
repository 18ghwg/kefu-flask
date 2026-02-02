# MySQL连接超时问题修复指南

## 问题描述

应用出现以下错误：
```
pymysql.err.OperationalError: (2013, 'Lost connection to MySQL server during query (timed out)')
sqlalchemy.exc.OperationalError: Lost connection to MySQL server during query (timed out)
```

**主要原因：**
1. 慢查询导致连接超时（10.974秒查询 system_settings 表）
2. 数据库连接池配置不当
3. SocketIO断开连接时未正确释放数据库连接
4. 异步线程持有数据库连接过久

## 已实施的修复

### 1. 优化数据库连接池配置 (`config.py`)

```python
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_pre_ping": True,        # 连接前测试可用性
    "pool_recycle": 280,          # 4分40秒回收连接（避免MySQL wait_timeout）
    "pool_size": 25,              # 增加连接池大小
    "max_overflow": 50,           # 增加最大溢出连接数
    "pool_timeout": 60,           # 增加获取连接超时
    "pool_reset_on_return": "rollback",  # 连接归还时自动回滚
    "connect_args": {
        "connect_timeout": 15,    # MySQL连接超时
        "read_timeout": 60,       # 读取超时（支持慢查询）
        "write_timeout": 60,      # 写入超时
        "charset": "utf8mb4"      # 明确字符集
    }
}
```

**关键改进：**
- `pool_recycle: 280` - 在MySQL默认超时(300秒)前回收连接
- `read_timeout: 60` - 允许慢查询有足够时间完成
- `pool_size: 25` + `max_overflow: 50` - 支持更高并发

### 2. 修复SocketIO断开连接处理 (`socketio_events.py`)

**问题：** 断开连接时数据库会话未释放，导致连接泄漏

**修复：**
```python
@socketio.on('disconnect')
def handle_disconnect():
    try:
        # ... 业务逻辑 ...
        db.session.commit()
    except Exception as e:
        logger.error(f"错误: {e}")
        db.session.rollback()  # ✅ 回滚失败的事务
    finally:
        db.session.remove()    # ✅ 关键：释放数据库连接
```

**改进点：**
- 添加 `db.session.rollback()` 处理异常情况
- 添加 `db.session.remove()` 确保连接释放
- 使用 `with_for_update(nowait=False)` 避免死锁

### 3. 数据库优化脚本

#### 运行修复脚本
```bash
python fix_connection_timeout.py
```

**功能：**
- 添加缺失的数据库索引
- 优化 system_settings 表查询
- 清理重复数据
- 检查长时间运行的查询

#### 监控数据库健康
```bash
# 单次检查
python monitor_db_health.py

# 持续监控（每30秒）
python monitor_db_health.py --continuous
```

**监控内容：**
- 连接池使用率
- MySQL实际连接数
- 慢查询检测
- 表锁检测

## 使用步骤

### 1. 应用配置更改
```bash
# 配置文件已更新，重启应用
pkill -f gunicorn
python app.py
# 或使用你的启动脚本
```

### 2. 运行数据库优化
```bash
python fix_connection_timeout.py
```

预期输出：
```
[1/4] 检查连接池状态...
  - 池大小: 25
  - 已签出: 5
  - MySQL实际连接数: 8

[2/4] 添加缺失的索引...
✅ 创建索引: idx_business_id ON system_settings(business_id)
✅ 创建索引: idx_visitor_state ON queues(visitor_id, state)

[3/4] 优化system_settings查询...
system_settings表记录数: 3
✅ 清理重复记录完成

[4/4] 检查长时间运行的查询...
✅ 没有发现长时间运行的查询

✅ 修复完成！
```

### 3. 验证修复效果
```bash
# 监控数据库健康
python monitor_db_health.py

# 查看日志
tail -f logs/20260202.log | grep -E "(慢查询|连接|timeout)"
```

## MySQL服务器配置建议

编辑 MySQL 配置文件 (`/etc/my.cnf` 或 `/etc/mysql/my.cnf`):

```ini
[mysqld]
# 连接超时设置
wait_timeout = 300              # 非交互连接超时（5分钟）
interactive_timeout = 300       # 交互连接超时（5分钟）
net_read_timeout = 60          # 网络读取超时
net_write_timeout = 60         # 网络写入超时

# 连接数限制
max_connections = 500          # 最大连接数
max_connect_errors = 100       # 最大连接错误数

# 查询优化
query_cache_size = 64M         # 查询缓存
query_cache_type = 1           # 启用查询缓存
tmp_table_size = 64M           # 临时表大小
max_heap_table_size = 64M      # 内存表大小

# 慢查询日志
slow_query_log = 1             # 启用慢查询日志
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 2            # 慢查询阈值（秒）
```

重启MySQL：
```bash
sudo systemctl restart mysql
# 或
sudo service mysql restart
```

## 性能监控

### 1. 实时监控慢查询
```bash
# 查看慢查询日志
tail -f /var/log/mysql/slow.log

# 或使用应用日志
tail -f logs/20260202.log | grep "慢查询"
```

### 2. 监控连接池状态
```python
# 在应用中添加监控端点
@app.route('/health/db')
def db_health():
    pool = db.engine.pool
    return {
        'pool_size': pool.size(),
        'checkedout': pool.checkedout(),
        'overflow': pool.overflow(),
        'usage_rate': pool.checkedout() / (pool.size() + pool.overflow()) * 100
    }
```

### 3. 使用监控脚本
```bash
# 每小时运行一次健康检查（添加到crontab）
0 * * * * cd /www/wwwroot/kefu-flask && python monitor_db_health.py >> logs/db_health.log 2>&1
```

## 常见问题排查

### Q1: 仍然出现连接超时
**检查：**
```bash
# 1. 查看MySQL连接数
mysql -u root -p -e "SHOW PROCESSLIST;"

# 2. 查看连接池状态
python monitor_db_health.py

# 3. 检查慢查询
mysql -u root -p -e "SHOW FULL PROCESSLIST;" | grep -v Sleep
```

**解决：**
- 增加 `pool_size` 和 `max_overflow`
- 优化慢查询（添加索引）
- 检查是否有死锁

### Q2: 连接池耗尽
**症状：** `QueuePool limit of size X overflow Y reached`

**解决：**
```python
# 增加连接池配置
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_size": 30,      # 增加基础池大小
    "max_overflow": 70,   # 增加溢出连接数
}
```

### Q3: 慢查询持续出现
**排查：**
```bash
# 运行优化脚本
python fix_connection_timeout.py

# 手动添加索引
mysql -u root -p kefu_flask
> SHOW INDEX FROM system_settings;
> CREATE INDEX idx_business_id ON system_settings(business_id);
```

## 预防措施

### 1. 代码规范
```python
# ✅ 正确：使用try-finally确保连接释放
try:
    result = db.session.query(Model).all()
    db.session.commit()
except Exception as e:
    db.session.rollback()
    logger.error(f"错误: {e}")
finally:
    db.session.remove()  # 释放连接

# ❌ 错误：不释放连接
result = db.session.query(Model).all()
db.session.commit()
```

### 2. 异步任务处理
```python
# ✅ 正确：异步任务中使用独立会话
def async_task():
    try:
        with app.app_context():
            # 执行数据库操作
            pass
    finally:
        db.session.remove()  # 确保释放

# 启动异步任务
Thread(target=async_task, daemon=True).start()
```

### 3. 定期维护
```bash
# 每天运行优化脚本
0 2 * * * cd /www/wwwroot/kefu-flask && python fix_connection_timeout.py >> logs/db_fix.log 2>&1

# 每小时监控健康状况
0 * * * * cd /www/wwwroot/kefu-flask && python monitor_db_health.py >> logs/db_health.log 2>&1
```

## 验证清单

- [ ] 配置文件已更新 (`config.py`)
- [ ] SocketIO事件处理已修复 (`socketio_events.py`)
- [ ] 运行数据库优化脚本 (`fix_connection_timeout.py`)
- [ ] 添加数据库索引
- [ ] 重启应用服务
- [ ] 验证连接池状态正常
- [ ] 监控日志无超时错误
- [ ] 设置定期健康检查

## 联系支持

如果问题持续存在：
1. 收集日志：`logs/20260202.log`
2. 运行诊断：`python monitor_db_health.py > diagnosis.txt`
3. 检查MySQL状态：`SHOW FULL PROCESSLIST;`
4. 提供以上信息寻求技术支持
