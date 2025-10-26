# Flask客服系统

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.2.5-green.svg)](https://flask.palletsprojects.com/)
[![Socket.IO](https://img.shields.io/badge/Socket.IO-5.3.4-black.svg)](https://socket.io/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

基于Flask框架的智能客服系统，支持实时聊天、访客管理、机器人自动回复等功能。

---

## 📖 系统简介

Flask客服系统是一个现代化的在线客服平台，从PHP版AI客服系统迁移而来，采用Flask框架重构，提供了更好的性能和可扩展性。

### 核心特性

✅ **实时通信** - 基于WebSocket的实时双向通信，支持消息推送、在线状态同步
✅ **智能分配** - 基于客服工作量的智能队列分配算法
✅ **多会话管理** - 客服可同时处理多个访客会话，提升服务效率
✅ **机器人客服** - 知识库驱动的自动回复系统，减轻人工压力
✅ **服务评价** - 完整的星级评价和反馈系统
✅ **访客管理** - 访客信息采集、黑名单管理、数据统计分析
✅ **快捷回复** - 预设常用回复，一键发送
✅ **文件传输** - 支持图片、文档等多种文件格式上传
✅ **响应式设计** - 完美适配PC和移动端
✅ **安全防护** - CSRF保护、XSS过滤、操作日志审计
✅ **一键安装** - Web安装向导，5分钟快速部署

---

## 🚀 快速开始

### 环境要求

- Python 3.11+
- MySQL 5.7+
- Redis 6.0+ (**必需** - WebSocket消息队列依赖)

### 安装步骤

#### 方式一：Web安装向导（推荐）⭐

1. **克隆项目并安装依赖**

```bash
git clone https://github.com/18ghwg/kefu-flask.git
cd kefu-flask
pip install -r requirements.txt
```

2. **配置环境变量（可选）**

创建 `.env` 文件配置Redis连接：

```bash
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password
REDIS_DB=0
```

3. **启动应用**

```bash
python app.py
```

4. **访问安装向导**

```text
http://localhost:5000/install
```

5. **按向导完成安装**

- ✅ 环境检测（Python版本、依赖包）
- ✅ 数据库配置（MySQL连接信息）
- ✅ Redis配置（缓存和消息队列）
- ✅ 管理员设置（创建系统管理员）
- ✅ 初始化数据库（自动创建表结构和默认数据）
- ✅ 完成安装（生成install.lock锁定文件）

#### 方式二：手动配置

1. **克隆项目**

```bash
git clone https://github.com/18ghwg/kefu-flask.git
cd kefu-flask
pip install -r requirements.txt
```

2. **编辑配置文件**

修改 `config.py` 中的数据库配置：

```python
HOSTNAME = 'localhost'
PORT = '3306'
DATABASE = 'customer_service'
USERNAME = 'your_username'
PASSWORD = 'your_password'
```

3. **配置Redis**

修改 `config.py` 或创建 `.env` 文件：

```python
REDIS_HOST = 'localhost'
REDIS_PORT = '6379'
REDIS_PASSWORD = ''  # 如有密码请填写
```

4. **初始化数据库**

```bash
# 创建数据库
mysql -u root -p -e "CREATE DATABASE customer_service CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 初始化表结构
python app.py
# 访问 /install 完成初始化
```

5. **启动应用**

```bash
python app.py
```

### 访问系统

```text
主页:         http://localhost:5000
安装向导:     http://localhost:5000/install
登录:         http://localhost:5000/login
访客聊天:     http://localhost:5000/visitor/chat
管理后台:     http://localhost:5000/admin/
客服工作台:   http://localhost:5000/service/chat
```

### 默认账号

安装向导完成后，使用您设置的管理员账号登录。

如使用手动配置，默认账号：

- 用户名: `admin`
- 密码: 安装时设置的密码

**⚠️ 安全提示**: 首次登录后请立即修改密码并启用双因素认证！

---

## ⚙️ 配置说明

### 环境变量配置（推荐）

系统支持通过 `.env` 文件进行配置，优先级高于 `config.py` 中的硬编码配置。

创建 `.env` 文件（项目根目录）：

```bash
# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password
REDIS_DB=0

# 可选：其他环境变量
# FLASK_ENV=production
# SECRET_KEY=your-secret-key
```

### 配置文件说明

**config.py** - 主配置文件

- 数据库连接配置
- Flask应用配置
- CSRF保护配置
- 文件上传配置
- Redis配置（支持环境变量）
- SocketIO配置

**config.example.py** - 配置模板文件

- 新项目部署时参考此文件
- 复制为 `config.py` 并填写实际配置
- 包含详细的配置说明

**优势**：

- ✅ 敏感信息不写入代码
- ✅ 不同环境灵活切换
- ✅ 支持Docker部署
- ✅ 符合12-Factor应用规范

### 🔒 敏感信息保护

本项目已配置 **Git Filter自动保护机制**，确保数据库密码、密钥等敏感信息不会被提交到GitHub：

**工作原理**：

1. **Git Filter** - 提交时自动清空 `config.py` 中的敏感值
2. **.gitignore** - 过滤本地脚本和AI记忆文件
3. **config.example.py** - 提供配置模板

**被保护的字段**：

- `HOSTNAME`, `PORT`, `DATABASE`, `USERNAME`, `PASSWORD` - 数据库配置
- `SECRET_KEY`, `API_SIGNATURE_SECRET`, `PASSWORD_SALT` - 安全密钥

**注意事项**：

- ⚠️ **本地 `config.py` 保持不变**，系统正常运行
- ✅ **GitHub上 `config.py`** 自动清空敏感值
- 📝 新环境部署时参考 `config.example.py` 填写配置

**如何配置**（新环境）：

```bash
# 1. 克隆项目后，复制配置模板
cp config.example.py config.py

# 2. 编辑config.py，填写实际配置
vim config.py

# 3. Git filter已自动配置，无需额外操作
```

---

## 📁 项目结构

```text
kefu-flask/
├── app.py                    # Flask应用入口
├── config.py                 # 配置文件
├── socketio_events.py        # WebSocket事件处理
├── requirements.txt          # Python依赖
├── .env                      # 环境变量配置（需自行创建）
├── exts.py                   # Flask扩展初始化
├── log.py                    # 日志配置
│
├── mod/                      # 核心模块
│   ├── blueprint/            # Flask蓝图
│   │   ├── auth.py          # 认证API
│   │   ├── visitor.py       # 访客API
│   │   ├── service.py       # 客服API
│   │   ├── admin.py         # 管理API
│   │   ├── queue.py         # 队列管理
│   │   ├── robot.py         # 机器人API
│   │   ├── rating.py        # 评价系统
│   │   ├── upload.py        # 文件上传
│   │   └── views/           # 视图蓝图
│   │       ├── index.py     # 首页
│   │       ├── install.py   # 安装向导
│   │       ├── auth.py      # 登录页
│   │       ├── admin_panel.py    # 管理后台
│   │       ├── service_panel.py  # 客服工作台
│   │       └── visitor.py        # 访客聊天页
│   │
│   ├── mysql/               # 数据库
│   │   ├── models.py        # 数据模型
│   │   └── ModuleClass/     # 业务逻辑类
│   │       ├── QueueServiceClass.py        # 队列服务
│   │       ├── VisitorServiceClass.py      # 访客服务
│   │       ├── ServiceManagementClass.py   # 客服管理
│   │       ├── RobotServiceClass.py        # 机器人服务
│   │       ├── StatisticsServiceClass.py   # 统计服务
│   │       └── ...          # 其他业务类
│   │
│   ├── decorators/          # 装饰器
│   │   ├── permission_required.py  # 权限验证
│   │   └── log_operation.py        # 操作日志
│   │
│   └── utils/               # 工具函数
│       ├── captcha_generator.py    # 验证码生成
│       └── security_filter.py      # 安全过滤
│
├── templates/               # HTML模板
│   ├── home.html           # 首页
│   ├── login.html          # 登录页
│   ├── visitor_chat.html   # 访客聊天
│   ├── install/            # 安装向导页面
│   ├── admin/              # 管理后台
│   │   ├── dashboard.html  # 仪表盘
│   │   ├── visitors.html   # 访客管理
│   │   ├── services.html   # 客服管理
│   │   ├── robots.html     # 机器人管理
│   │   └── settings.html   # 系统设置
│   └── service/            # 客服工作台
│       └── chat.html       # 客服聊天界面
│
├── static/                  # 静态文件
│   ├── css/                # 样式文件
│   ├── js/                 # JavaScript文件
│   ├── img/                # 图片资源
│   └── uploads/            # 用户上传文件
│       ├── avatars/        # 头像
│       ├── images/         # 图片
│       └── files/          # 文档
│
├── migrations/              # 数据库迁移
│   └── versions/           # 迁移版本
│
├── install/                 # 安装相关
│   ├── install.lock        # 安装锁定文件
│   └── README.md           # 安装说明
│
└── logs/                    # 日志文件
```

---

## 📸 界面预览

### 访客聊天界面

- 简洁美观的聊天窗口
- 实时消息推送
- 输入状态显示
- 响应式设计

### 客服工作台界面

- 访客列表管理
- 多窗口聊天
- 快捷回复
- 未读消息提示

### 管理后台界面

- 数据统计
- 客服管理
- 系统设置
- 操作日志

---

## 🔧 功能列表

### ✅ 已完成功能

#### 基础架构

- [X] Flask应用架构
- [X] 用户认证与会话管理
- [X] 角色权限控制（管理员/客服/访客）
- [X] CSRF保护
- [X] 响应式前端设计
- [X] RESTful API架构
- [X] Web安装向导

#### 实时通信

- [X] WebSocket双向通信（基于Socket.IO）
- [X] Redis消息队列（多进程支持）
- [X] 实时消息推送
- [X] 在线状态管理
- [X] 输入状态同步
- [X] 心跳检测机制
- [X] 断线重连

#### 访客端功能

- [X] 访客聊天界面
- [X] 自动分配客服
- [X] 消息发送/接收
- [X] 文件上传（图片、文档）
- [X] 表情包支持
- [X] 访客信息采集

#### 客服工作台功能

- [X] 客服聊天界面
- [X] 多访客会话管理
- [X] 访客列表展示
- [X] 快捷回复管理
- [X] 消息记录查看
- [X] 会话转接
- [X] 访客信息查看
- [X] 实时统计面板
- [X] 未读消息提醒

#### 队列管理

- [X] 访客排队系统
- [X] 智能分配算法
- [X] 客服工作量均衡
- [X] 队列状态监控
- [X] 超时处理机制

#### 智能机器人

- [X] 机器人自动回复
- [X] 知识库管理（问答对）
- [X] 关键词匹配
- [X] 欢迎语设置
- [X] 机器人开关控制

#### 管理后台功能

- [X] 客服账号管理
- [X] 访客信息管理
- [X] 访客黑名单
- [X] 快捷回复库
- [X] 机器人配置
- [X] 系统设置
- [X] 操作日志审计
- [X] 数据统计报表

#### 评价系统

- [X] 服务评价（星级+评论）
- [X] 评价数据统计
- [X] 评价结果展示

#### 数据统计

- [X] 访客统计（总量、今日、在线）
- [X] 会话统计
- [X] 客服工作量统计
- [X] IP地址定位
- [X] 访问来源分析

#### 文件管理

- [X] 图片上传
- [X] 文件上传
- [X] 头像管理
- [X] 文件大小限制
- [X] 文件类型过滤

#### 安全功能

- [X] CSRF防护
- [X] XSS过滤
- [X] SQL注入防护
- [X] 密码加密存储
- [X] 操作日志记录
- [X] IP黑名单

### 📋 待优化功能

#### 性能优化

- [ ] 消息分页加载
- [ ] 数据库查询优化
- [ ] 静态资源CDN
- [ ] 缓存策略优化

#### 功能增强

- [ ] 视频通话
- [ ] 语音消息
- [ ] 屏幕共享
- [ ] 消息撤回
- [ ] 消息已读回执
- [ ] 邮件通知
- [ ] 短信通知
- [ ] 微信集成
- [ ] 多语言支持

---

## 🛠️ 技术栈

### 后端

- **框架**: Flask 2.2.5
- **ORM**: SQLAlchemy 1.3.24
- **实时通信**: Flask-SocketIO 5.3.4
- **认证**: Flask-Login 0.6.2
- **数据库迁移**: Flask-Migrate 3.1.0
- **CSRF保护**: Flask-WTF 1.2.1
- **数据库驱动**: PyMySQL 1.1.0
- **Redis客户端**: redis 4.6.0
- **WSGI服务器**: Gunicorn 21.2.0
- **异步支持**: eventlet 0.33.3

### 前端

- **基础**: HTML5 + CSS3 + JavaScript ES6+
- **实时通信**: Socket.IO Client 4.5.4
- **字体**: Inter Font
- **无框架**: 使用原生JavaScript

### 数据库

- **主数据库**: MySQL 5.7+
- **消息队列/缓存**: Redis 6.0+ (**必需** - SocketIO消息队列依赖)

---

## 📊 项目进度

**当前版本**: v2.0-beta
**总体进度**: 85% (85/100+ 功能)
**最后更新**: 2025-10-26

| 模块       | 进度                                          | 说明                |
| ---------- | --------------------------------------------- | ------------------- |
| 基础架构   | ████████████████████ 100% | ✅ 完成             |
| 用户认证   | ████████████████████ 100% | ✅ 完成             |
| 实时通信   | ████████████████████ 100% | ✅ 完成             |
| 访客端     | ███████████████████░ 95%  | ✅ 核心功能完成     |
| 客服工作台 | ███████████████████░ 95%  | ✅ 核心功能完成     |
| 队列管理   | ████████████████████ 100% | ✅ 完成             |
| 智能机器人 | ███████████████████░ 95%  | ✅ 核心功能完成     |
| 访客管理   | ███████████████████░ 95%  | ✅ 核心功能完成     |
| 评价系统   | ████████████████████ 100% | ✅ 完成             |
| 统计报表   | ██████████████████░░ 90%  | ✅ 基础统计完成     |
| 文件管理   | ████████████████████ 100% | ✅ 完成             |
| 安全功能   | ███████████████████░ 95%  | ✅ 核心安全机制完成 |
| 管理后台   | ███████████████████░ 95%  | ✅ 核心功能完成     |

### 🎯 开发重点

**已完成核心功能**:

- ✅ 完整的实时通信系统（WebSocket + Redis）
- ✅ 智能队列分配系统
- ✅ 访客管理与黑名单
- ✅ 机器人自动回复
- ✅ 服务评价系统
- ✅ 完善的后台管理
- ✅ Web安装向导

**进行中的优化**:

- ⏳ 性能优化（消息分页、查询优化）
- ⏳ 用户体验提升
- ⏳ 文档完善

**未来规划**:

- 📋 多语言支持
- 📋 移动端APP
- 📋 第三方集成（微信、邮件）
- 📋 高级统计分析

---

## 🚀 生产环境部署

### 推荐部署方案

#### 方案一：Gunicorn + Nginx（推荐⭐）

**第1步：生成配置文件（自动适配环境）**

项目提供了自动配置生成脚本，可自动检测项目路径、CPU核心数等信息：

```bash
# 生成Gunicorn配置（自动检测CPU核心数和路径）
python generate_gunicorn_config.py

# 生成Nginx配置（自动检测项目路径）
python generate_nginx_config.py

# 自定义配置示例
python generate_gunicorn_config.py --port 8000 --workers 4
python generate_nginx_config.py --server-name yourdomain.com --port 80
```

**第2步：启动Gunicorn**

```bash
gunicorn -c gunicorn_config.py app:app
```

**第3步：配置Nginx**

```bash
# 复制生成的配置到Nginx目录
sudo cp nginx_correct.conf /etc/nginx/sites-available/kefu-flask.conf

# 创建软链接启用配置
sudo ln -s /etc/nginx/sites-available/kefu-flask.conf /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重载Nginx
sudo systemctl reload nginx
```

**配置说明**：

- ✅ **自动路径检测** - 无需手动修改项目路径
- ✅ **CPU核心数优化** - 自动计算最佳Worker数量
- ✅ **日志目录自适应** - 支持宝塔、标准Nginx等多种环境
- ✅ **WebSocket完整支持** - 预配置所有必需的代理头
- ✅ **一键重新生成** - 换环境只需重新运行生成脚本

**配置文件位置**：

- 模板文件：`nginx_correct.conf.template`、`gunicorn_config.py.template`
- 生成文件：`nginx_correct.conf`、`gunicorn_config.py`（不纳入版本控制）
- 生成脚本：`generate_nginx_config.py`、`generate_gunicorn_config.py`

#### 方案二：Docker部署（未来支持）

### 生产环境注意事项

⚠️ **安全配置**

```python
# config.py
DEBUG = False
SECRET_KEY = '使用强随机密钥'
WTF_CSRF_SSL_STRICT = True
```

⚠️ **数据库优化**

- 启用连接池
- 配置主从复制
- 定期备份数据

⚠️ **Redis配置**

- 设置密码认证
- 配置持久化
- 监控内存使用

⚠️ **日志管理**

- 配置日志轮转
- 错误日志监控
- 访问日志分析

---

## 🧪 测试

### 运行测试

```bash
# 测试实时聊天功能
# 1. 打开访客聊天页面: http://localhost:5000/visitor/chat
# 2. 打开客服工作台: http://localhost:5000/service/chat
# 3. 在访客端发送消息，验证客服端实时接收

# 测试机器人自动回复
# 1. 在管理后台配置机器人问答对
# 2. 访客发送匹配的问题
# 3. 验证机器人自动回复

# 运行单元测试（待实现）
pytest tests/
```

### 测试覆盖率

- 单元测试: 待实现
- 集成测试: 待实现
- E2E测试: 手动测试通过
- WebSocket测试: ✅ 通过
- 安全测试: ✅ CSRF/XSS防护测试通过

---

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议！

### 贡献流程

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 License

本项目采用 MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 👥 团队

- **项目负责人**: AI Assistant
- **架构设计**: AI Assistant
- **后端开发**: AI Assistant
- **前端开发**: AI Assistant
- **文档编写**: AI Assistant

---

## 📞 联系我们

- **项目主页**: <https://github.com/18ghwg/kefu-flask>
- **问题反馈**: <https://github.com/18ghwg/kefu-flask/issues>

---

## 🎉 致谢

感谢以下开源项目：

- Flask
- Socket.IO
- SQLAlchemy
- Bootstrap (未使用但致敬)

---

## 📝 更新日志

### v2.0-beta (2025-10-26) 🎉

#### 重大更新 - 核心功能全面完成

- ✅ Web安装向导上线
- ✅ 队列管理系统完善
- ✅ 智能分配算法优化
- ✅ 评价系统上线
- ✅ 访客黑名单功能
- ✅ 系统设置功能
- ✅ 操作日志审计
- ✅ 统计报表完善
- ✅ CSRF全面防护
- ✅ Redis环境变量支持

### v1.5-beta (2025-10-12)

- ✅ 文件上传功能
- ✅ 机器人知识库管理
- ✅ 快捷回复优化
- ✅ 访客信息管理
- ✅ IP地址定位

### v1.0-alpha (2025-10-05)

- ✅ 完成基础架构搭建
- ✅ 实现实时聊天功能
- ✅ 完成访客聊天界面
- ✅ 完成客服聊天界面
- ✅ 实现WebSocket通信
- ✅ 响应式设计

### 未来计划

- 📋 v2.1: 性能优化（消息分页、查询优化）
- 📋 v2.2: 移动端优化
- 📋 v3.0: 多语言支持
- 📋 v3.1: 第三方集成（微信、邮件）
- 📋 v4.0: 多渠道接入

---

**项目启动**: 2025-10-05
**最后更新**: 2025-10-26
**当前版本**: v2.0-beta
**项目状态**: 🚀 测试中 (Beta阶段)
