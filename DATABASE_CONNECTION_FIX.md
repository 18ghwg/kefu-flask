# 数据库连接池耗尽问题修复方案

## 问题描述

错误信息：
```
QueuePool limit of size 15 overflow 30 reached, connection timed out, timeout 10.00
```

这表示数据库连接池的所有连接（15个基础 + 30个溢出 = 45个）都被占用且未释放。

## 根本原因

1. **后台线程未释放连接**：`socketio_events.py` 中的异步线程（`async_save_visitor`）使用数据库后没有调用 `db.session.remove()`
2. **缺少全局会话清理**：Flask应用缺少 `@app.teardown_appcontext` 钩子来自动清理会话
3. **连接池配置偏小**：在高并发场景下，15个基础连接 + 30个溢出连接不够用

## 已实施的修复

### 1. 增加全局会话清理（app.py）

```python
@app.teardown_appcontext
def shutdown_session(exception=None):
    """
    请求结束后清理数据库会话
    ✅ 关键修复：确保每个请求后都释放数据库连接
    """
    db.session.remove()
```

### 2. 修复异步线程连接泄漏（socketio_events.py）

在 `async_save_visitor()` 函数中添加：

```python
finally:
    # ✅ 关键修复：清理数据库会话，释放连接
    db.session.remove()
```

### 3. 优化连接池配置（config.py）

```python
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
    "pool_size": 20,              # 从15增加到20
    "max_overflow": 40,           # 从30增加到40
    "pool_timeout": 30,           # 从10增加到30秒
    "pool_reset_on_return": "rollback",  # 自动回滚未提交事务
    "connect_args": {
        "connect_timeout": 10,    # 从5增加到10秒
        "read_timeout": 30,       # 从10增加到30秒
        "write_timeout": 30,      # 从10增加到30秒
    }
}
```

## 立即修复步骤

### 1. 重启应用

```bash
# 停止当前运行的应用
pkill -f "python.*app.py"
pkill -f "gunicorn"

# 或使用systemctl（如果配置了服务）
systemctl restart kefu-flask

# 或手动重启
python app.py
```

### 2. 检查连接池状态

```bash
python check_db_pool.py
```

### 3. 如果仍有问题，手动清理连接

```bash
python fix_db_connections.py
```

## 监控和预防

### 1. 定期检查连接池状态

```bash
# 添加到crontab，每5分钟检查一次
*/5 * * * * cd /www/wwwroot/kefu-flask && python check_db_pool.py >> logs/pool_check.log 2>&1
```

### 2. 监控日志

关注以下错误：
- `QueuePool limit`
- `connection timed out`
- `TimeoutError`

### 3. 数据库连接数监控

在MySQL中检查当前连接数：

```sql
-- 查看当前连接数
SHOW STATUS LIKE 'Threads_connected';

-- 查看最大连接数
SHOW VARIABLES LIKE 'max_connections';

-- 查看当前所有连接
SHOW PROCESSLIST;
```

## 长期优化建议

### 1. 使用连接池监控

在 `app.py` 中添加定期监控：

```python
from apscheduler.schedulers.background import BackgroundScheduler

def monitor_pool():
    with app.app_context():
        pool = db.engine.pool
        utilization = (pool.checkedout() / (pool.size() + pool._max_overflow)) * 100
        if utilization > 80:
            logger.warning(f"⚠️ 连接池利用率过高: {utilization:.1f}%")

scheduler = BackgroundScheduler()
scheduler.add_job(monitor_pool, 'interval', minutes=5)
scheduler.start()
```

### 2. 优化数据库查询

- 避免在循环中执行查询
- 使用批量操作代替单条插入
- 及时关闭不需要的查询结果

### 3. 使用数据库连接池中间件

考虑使用 PgBouncer（PostgreSQL）或 ProxySQL（MySQL）等连接池中间件。

### 4. 增加MySQL最大连接数

编辑 MySQL 配置文件 `/etc/my.cnf`：

```ini
[mysqld]
max_connections = 500
```

然后重启MySQL：

```bash
systemctl restart mysql
```

## 故障排查

### 如果问题仍然存在

1. **检查是否有长时间运行的查询**：
   ```sql
   SELECT * FROM information_schema.processlist 
   WHERE command != 'Sleep' 
   ORDER BY time DESC;
   ```

2. **检查是否有锁等待**：
   ```sql
   SHOW ENGINE INNODB STATUS;
   ```

3. **检查应用日志**：
   ```bash
   tail -f logs/error.log | grep -i "pool\|timeout\|connection"
   ```

4. **检查系统资源**：
   ```bash
   # CPU和内存
   top
   
   # 网络连接
   netstat -an | grep 3306 | wc -l
   ```

## 紧急恢复

如果应用完全无法响应：

```bash
# 1. 强制停止应用
pkill -9 -f "python.*app.py"
pkill -9 -f "gunicorn"

# 2. 重启MySQL（会断开所有连接）
systemctl restart mysql

# 3. 清理Python进程
ps aux | grep python | grep -v grep | awk '{print $2}' | xargs kill -9

# 4. 重新启动应用
cd /www/wwwroot/kefu-flask
python app.py
```

## 联系支持

如果问题持续存在，请提供：
1. `check_db_pool.py` 的输出
2. 最近的错误日志（`logs/error.log`）
3. MySQL processlist 输出
4. 系统资源使用情况（CPU、内存、网络）
