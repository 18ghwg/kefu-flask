# 定时任务说明

## 📋 任务列表

### 健康检查任务（高频）

#### 1. 数据库健康检查 (db_health_check)
- **执行频率**: 每3分钟
- **功能**: 执行简单查询保持连接池活跃
- **目的**: 防止连接超时导致的"冷启动"延迟

#### 2. 连接池监控 (monitor_connection_pool)
- **执行频率**: 每5分钟
- **功能**: 
  - 监控连接池使用率
  - 检查MySQL实际连接数
  - 检测连接泄漏
- **警告阈值**:
  - 使用率 > 80%: 严重警告
  - 使用率 > 60%: 一般警告

#### 3. 连接池清理 (cleanup_connection_pool)
- **执行频率**: 每10分钟
- **功能**:
  - 清理未正确关闭的会话
  - 触发连接池健康检查
  - 检测并记录空闲连接
  - 释放僵死连接
- **清理策略**:
  - 自动清理所有会话
  - 检测空闲超过60秒的连接

#### 4. 慢查询检查 (check_slow_queries)
- **执行频率**: 每15分钟
- **功能**:
  - 检测运行超过5秒的查询
  - 记录慢查询详情
  - 帮助识别性能问题
- **检测阈值**: 5秒

### 维护任务（定时）

#### 5. 表统计信息分析 (analyze_tables)
- **执行频率**: 每天凌晨2点
- **功能**:
  - 分析表统计信息
  - 优化查询计划
  - 提升查询性能
- **影响**: 帮助MySQL选择最优执行计划

#### 6. 数据库索引优化 (optimize_database_indexes)
- **执行频率**: 每周日凌晨3点
- **功能**:
  - 检查缺失的索引
  - 自动添加优化索引
  - 提升查询性能
- **优化范围**: chats, queues, visitors表

#### 7. 清理过期数据 (cleanup_old_data)
- **执行频率**: 每天凌晨4点
- **功能**:
  - 清理90天前的聊天记录
  - 分批删除避免锁表
  - 释放存储空间
- **清理策略**: 每批1000条，逐步清理

#### 8. 检查表碎片 (check_table_fragmentation)
- **执行频率**: 每周一凌晨5点
- **功能**:
  - 检测表碎片率
  - 识别需要优化的表
  - 提供优化建议
- **警告阈值**: 碎片率 > 20%

#### 9. 生成性能报告 (generate_performance_report)
- **执行频率**: 每天早上8点
- **功能**:
  - 汇总系统性能指标
  - 统计数据库连接数
  - 分析表大小和行数
  - 监控连接池状态
- **报告内容**: 连接数、表大小、连接池使用率

#### 10. 清理Redis缓存 (vacuum_redis_cache)
- **执行频率**: 每天凌晨1点
- **功能**:
  - 清理过期的缓存键
  - 释放Redis内存
  - 优化缓存性能
- **清理范围**: dashboard:*, stats:*, temp:*

## 🚀 使用方法

### 启动任务调度器

任务调度器通常在应用启动时自动启动。如果需要手动管理：

```python
# 在 app.py 中
from flask_apscheduler import APScheduler
from Tasks.task_list import Config

scheduler = APScheduler()
app.config.from_object(Config())
scheduler.init_app(app)
scheduler.start()
```

### 查看任务状态

```python
# 获取所有任务
jobs = scheduler.get_jobs()

# 获取特定任务
job = scheduler.get_job('db_health_check')

# 暂停任务
scheduler.pause_job('db_health_check')

# 恢复任务
scheduler.resume_job('db_health_check')

# 立即执行任务
scheduler.run_job('db_health_check')
```

## 📊 监控日志

### 正常日志示例

```
2026-02-01 10:00:00 - DEBUG - ✅ 数据库健康检查通过
2026-02-01 10:05:00 - DEBUG - 📊 连接池监控 - 使用率:35.2% (8/25)
2026-02-01 10:10:00 - DEBUG - ✅ 连接池清理完成 - 状态正常
2026-02-01 10:15:00 - DEBUG - ✅ 未发现慢查询
```

### 警告日志示例

```
2026-02-01 10:05:00 - WARNING - ⚠️ 📊 连接池监控 - 使用率:85.3% (64/75) - 使用率过高！
2026-02-01 10:10:00 - WARNING - ⚠️ 发现 12 个空闲超过60秒的连接
2026-02-01 10:15:00 - WARNING - 🐌 发现 2 个慢查询:
2026-02-01 10:15:00 - WARNING -   ID:12345 | 用户:kefu_flask | 时间:8秒 | 状态:Sending data
```

## ⚙️ 配置调整

### 修改执行频率

编辑 `Tasks/task_list.py`:

```python
JOBS = [
    {
        'id': 'db_health_check',
        'func': 'Tasks.db_health_check:check_db_health',
        'trigger': 'interval',
        'minutes': 3,  # 修改这里
        'misfire_grace_time': 30
    },
]
```

### 修改检测阈值

编辑 `Tasks/db_health_check.py`:

```python
# 慢查询阈值（秒）
SLOW_QUERY_THRESHOLD = 5  # 修改这里

# 空闲连接阈值（秒）
IDLE_CONNECTION_THRESHOLD = 60  # 修改这里

# 连接池使用率警告阈值
HIGH_USAGE_THRESHOLD = 80  # 修改这里
MEDIUM_USAGE_THRESHOLD = 60  # 修改这里
```

### 启用自动终止空闲连接

编辑 `Tasks/db_health_check.py` 中的 `cleanup_connection_pool()` 函数，取消注释以下代码：

```python
# 可选：终止长时间空闲的连接（谨慎使用）
result = db.session.execute(text("""
    SELECT id FROM information_schema.processlist
    WHERE user = :user AND command = 'Sleep' AND time > 300
"""), {"user": app.config.get('USERNAME', 'kefu_flask')})

for row in result:
    db.session.execute(text(f"KILL {row[0]}"))
    logger.info(f"🔪 终止空闲连接: {row[0]}")
```

⚠️ **警告**: 自动终止连接可能影响正在使用的连接，请谨慎启用！

## 🔍 故障排查

### 问题1: 任务未执行

**检查**:
```python
# 查看任务是否已注册
scheduler.get_jobs()

# 查看任务状态
job = scheduler.get_job('db_health_check')
print(job.next_run_time)
```

**解决**:
- 确认 APScheduler 已启动
- 检查任务配置是否正确
- 查看应用日志是否有错误

### 问题2: 权限不足

**症状**: 日志显示 "检查MySQL连接数失败（可能权限不足）"

**解决**:
```sql
-- 授予必要的权限
GRANT PROCESS ON *.* TO 'kefu_flask'@'%';
FLUSH PRIVILEGES;
```

### 问题3: 任务执行过慢

**检查**:
- 查看 `misfire_grace_time` 配置
- 检查数据库响应时间
- 查看系统资源使用情况

**解决**:
- 增加 `misfire_grace_time`
- 优化数据库查询
- 减少任务执行频率

## 📈 性能影响

### 资源消耗

| 任务 | CPU | 内存 | 数据库查询 | 执行时间 |
|------|-----|------|-----------|---------|
| db_health_check | 极低 | 极低 | 1次 | <100ms |
| monitor_connection_pool | 低 | 低 | 2次 | <200ms |
| cleanup_connection_pool | 低 | 低 | 2-3次 | <500ms |
| check_slow_queries | 低 | 低 | 1次 | <300ms |

### 优化建议

1. **生产环境**: 保持默认配置
2. **开发环境**: 可以增加执行频率以便调试
3. **高负载环境**: 可以适当减少执行频率

## 🆘 紧急处理

### 暂停所有任务

```python
scheduler.pause()
```

### 恢复所有任务

```python
scheduler.resume()
```

### 立即执行清理

```python
scheduler.run_job('cleanup_connection_pool')
```

## 📝 添加自定义任务

### 步骤1: 创建任务函数

在 `Tasks/db_health_check.py` 或新文件中添加：

```python
def my_custom_task():
    """自定义任务"""
    try:
        with app.app_context():
            # 你的任务逻辑
            pass
    except Exception as e:
        logger.error(f"任务执行失败: {e}")
    finally:
        try:
            db.session.remove()
        except:
            pass
```

### 步骤2: 注册任务

在 `Tasks/task_list.py` 中添加：

```python
JOBS = [
    # ... 现有任务 ...
    
    {
        'id': 'my_custom_task',
        'func': 'Tasks.db_health_check:my_custom_task',
        'trigger': 'interval',
        'minutes': 30,
        'misfire_grace_time': 60
    },
]
```

### 步骤3: 重启应用

```bash
pkill -f gunicorn
python app.py
```

## 🔗 相关文档

- [APScheduler 文档](https://apscheduler.readthedocs.io/)
- [Flask-APScheduler 文档](https://github.com/viniciuschiele/flask-apscheduler)
- [MySQL连接超时修复指南](../MYSQL_TIMEOUT_FIX.md)
- [数据库健康监控工具](../monitor_db_health.py)

## ✅ 验证清单

- [ ] 任务已注册并启动
- [ ] 日志中可以看到任务执行记录
- [ ] 连接池使用率保持在合理范围（<60%）
- [ ] 无频繁的连接超时错误
- [ ] 慢查询数量在可接受范围内

---

**最后更新**: 2026-02-01  
**维护者**: 系统管理员  
**版本**: 1.0
