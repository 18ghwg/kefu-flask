# 硬编码URL检测和修复工具

## 功能说明

这个工具可以自动检测和修复Flask模板文件中的硬编码URL，将它们替换为`url_for()`函数调用。

## 使用方法

### 1. 仅扫描（不修改文件）

```bash
python fix_hardcoded_urls.py --scan
```

这个命令会扫描所有模板文件，检测硬编码URL，并生成详细报告，但不会修改任何文件。

### 2. 自动修复

```bash
python fix_hardcoded_urls.py --fix
```

这个命令会扫描并自动修复所有可以修复的硬编码URL。

**⚠️ 注意**: 在执行修复前，建议先提交Git或备份文件！

## 检测范围

工具会扫描以下目录：
- `templates/` - 所有HTML模板文件
- `static/js/` - JavaScript文件（可选）

## 检测模式

工具会检测以下模式的硬编码URL：

1. **HTML href属性**: `href="/admin"`
2. **HTML action属性**: `action="/login"`
3. **JavaScript location**: `window.location = "/admin"`
4. **JavaScript fetch/axios**: `fetch("/api/data")`

## URL映射表

工具内置了常用URL的映射关系，例如：

```python
URL_MAPPING = {
    '/admin': "{{ url_for('admin_panel.index') }}",
    '/login': "{{ url_for('auth_view.login_page') }}",
    '/chat': "{{ url_for('visitor_view.chat') }}",
    # ... 更多映射
}
```

如果工具发现无法自动修复的URL，你需要：
1. 在脚本的`URL_MAPPING`中添加对应的路由映射
2. 重新运行脚本

## 输出示例

### 扫描报告示例

```
============================================================
[*] 硬编码URL检测工具
============================================================
模式: 仅扫描
============================================================

[SCAN] 扫描目录: templates
       找到 25 个HTML文件

[1/25] 检查 templates/admin/index.html... [X] 发现 8 个问题 (8 可修复, 0 需手动)
[2/25] 检查 templates/home.html... [X] 发现 3 个问题 (3 可修复, 0 需手动)
[3/25] 检查 templates/login.html... [OK] 无问题

============================================================
[*] 扫描报告
============================================================

共发现 11 个硬编码URL问题，涉及 2 个文件

[FILE] templates/admin/index.html
------------------------------------------------------------
  行  194 | [OK] 可自动修复
           URL: /service/chat
           建议: {{ url_for('service_panel.chat') }}
           上下文: <a href="/service/chat" class="action-card">...

============================================================
[*] 统计
============================================================
[OK] 可自动修复: 11
[!] 需手动修复: 0
============================================================
```

## 自动跳过的URL

以下类型的URL会被自动跳过（不替换）：
- 静态资源路径: `/static/`, `/uploads/`
- API路径: `/api/`
- 锚点链接: `#section`
- 已使用url_for的URL

## 常见问题

### Q: 为什么有些URL无法自动修复？

A: 可能的原因：
1. URL没有在`URL_MAPPING`中定义
2. URL是动态生成的（需要参数）
3. URL是外部链接

对于这些情况，需要手动修复。

### Q: 修复后如何验证？

A: 运行Flask应用，检查：
1. 所有链接是否正常工作
2. 控制台是否有路由错误
3. 运行 `python fix_hardcoded_urls.py --scan` 确认无遗漏

### Q: 可以撤销修复吗？

A: 可以通过Git回退：
```bash
git checkout -- templates/
```

或者从备份恢复文件。

## 扩展配置

### 添加新的URL映射

编辑`fix_hardcoded_urls.py`，在`URL_MAPPING`字典中添加：

```python
URL_MAPPING = {
    # ... 现有映射 ...
    '/your/path': "{{ url_for('blueprint.function') }}",
}
```

### 添加扫描目录

编辑`SCAN_DIRS`列表：

```python
SCAN_DIRS = [
    BASE_DIR / 'templates',
    BASE_DIR / 'your_custom_dir',
]
```

### 添加跳过模式

编辑`STATIC_PATTERNS`列表：

```python
STATIC_PATTERNS = [
    r'/static/',
    r'/your_custom_pattern/',
]
```

## 技术实现

- 使用正则表达式匹配硬编码URL
- 支持精确匹配和模糊匹配
- 保留原有的引号类型和格式
- 从后往前替换，避免位置偏移

## 贡献

如果发现bug或有改进建议，请提交issue或PR。

## 许可

MIT License

