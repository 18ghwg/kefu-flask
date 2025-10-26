/**
 * 客服聊天界面 - Script
 */

// ========== 工具函数：HTML清洁和日期格式化 ==========

// HTML清洁函数（防止XSS，但允许安全的HTML标签）
function sanitizeHtml(html) {
    if (!html) return '';
    const temp = document.createElement('div');
    temp.innerHTML = html;
    
    // 移除危险标签
    temp.querySelectorAll('script, style, iframe, object, embed, form, input, button').forEach(el => el.remove());
    
    // 移除危险属性
    temp.querySelectorAll('*').forEach(el => {
        Array.from(el.attributes).forEach(attr => {
            if (attr.name.startsWith('on') || attr.name === 'formaction' || attr.name === 'form') {
                el.removeAttribute(attr.name);
            }
        });
        
        // 清理链接
        if (el.tagName === 'A' && el.hasAttribute('href')) {
            const href = el.getAttribute('href');
            if (href && !href.match(/^(https?:|mailto:)/i)) {
                el.removeAttribute('href');
            }
        }
    });
    
    return temp.innerHTML;
}

// 日期格式化函数
function formatDateSeparator(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    
    const dateStr = date.toLocaleDateString('zh-CN');
    const todayStr = today.toLocaleDateString('zh-CN');
    const yesterdayStr = yesterday.toLocaleDateString('zh-CN');
    
    if (dateStr === todayStr) {
        return '今天';
    } else if (dateStr === yesterdayStr) {
        return '昨天';
    } else {
        const weekdays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'];
        const weekday = weekdays[date.getDay()];
        const month = date.getMonth() + 1;
        const day = date.getDate();
        
        // 如果是今年，显示 "X月X日 星期Y"
        if (date.getFullYear() === today.getFullYear()) {
            return `${month}月${day}日 ${weekday}`;
        } else {
            // 如果不是今年，显示 "XXXX年X月X日 星期Y"
            return `${date.getFullYear()}年${month}月${day}日 ${weekday}`;
        }
    }
}

function formatDateOnly(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleDateString('zh-CN');
}

function createDateSeparator(timestamp) {
    const separator = document.createElement('div');
    separator.className = 'date-separator';
    separator.innerHTML = `<span class="date-separator-text">${formatDateSeparator(timestamp)}</span>`;
    return separator;
}

// 全局变量：跟踪最后一条消息的日期
let lastMessageDate = null;

// 格式化文件大小
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// 客服信息
        const serviceId = {{ current_user.service_id }};
        const serviceName = "{{ current_user.nick_name }}";
        let socket = null;
        let currentVisitorId = null;
        let visitors = {}; // 存储访客信息
        let typingTimeout = null;

        // 初始化
        document.addEventListener('DOMContentLoaded', function() {
            initSocket();
            initInput();
        });

        // 初始化Socket.IO连接
        function initSocket() {
            socket = io({
                transports: ['websocket', 'polling']
            });

            // 连接成功
            socket.on('connect', function() {
                console.log('Socket connected:', socket.id);
                
                // 客服加入
                socket.emit('service_join', {
                    service_id: serviceId,
                    service_name: serviceName
                });
            });

            // 加入成功
            socket.on('join_success', function(data) {
                console.log('Join success:', data);
            });

            // 新访客上线
            socket.on('new_visitor', function(data) {
                console.log('New visitor:', data);
                addVisitorToList(data);
                updateStats();
            });

            // 接收消息
            socket.on('receive_message', function(data) {
                console.log('Received message:', data);
                
                // 如果是当前访客的消息，添加到聊天界面
                if (data.from_id == currentVisitorId) {
                    addMessage(data.content, 'visitor', data.timestamp);
                } else {
                    // 其他访客的消息，更新未读数和最后消息
                    updateVisitorUnread(data.from_id);
                    updateVisitorLastMessage(data.from_id, data.content, data.timestamp);
                }
            });

            // 访客正在输入
            socket.on('user_typing', function(data) {
                const typingIndicator = document.getElementById('typingIndicator');
                if (data.is_typing) {
                    typingIndicator.classList.add('show');
                } else {
                    typingIndicator.classList.remove('show');
                }
            });

            // 访客离线
            socket.on('user_offline', function(data) {
                if (data.user_type === 'visitor') {
                    removeVisitorFromList(data.user_id);
                    updateStats();
                }
            });

            // 获取在线用户
            socket.emit('get_online_users');
            socket.on('online_users_list', function(data) {
                console.log('Online users:', data);
                // 显示在线访客
                data.visitors.forEach(visitor => {
                    addVisitorToList(visitor);
                });
                updateStats();
            });
        });

        // 初始化输入框
        function initInput() {
            const messageInput = document.getElementById('messageInput');
            const sendBtn = document.getElementById('sendBtn');

            // 回车发送（Ctrl+Enter换行）
            messageInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter' && !e.ctrlKey) {
                    e.preventDefault();
                    sendMessage();
                }
            });

            // 点击发送
            sendBtn.addEventListener('click', sendMessage);

            // 输入状态
            messageInput.addEventListener('input', function() {
                if (currentVisitorId) {
                    clearTimeout(typingTimeout);
                    
                    socket.emit('typing', {
                        from_id: serviceId,
                        from_type: 'service',
                        from_name: serviceName,
                        to_id: currentVisitorId,
                        to_type: 'visitor',
                        is_typing: true
                    });

                    typingTimeout = setTimeout(function() {
                        socket.emit('typing', {
                            from_id: serviceId,
                            from_type: 'service',
                            to_id: currentVisitorId,
                            to_type: 'visitor',
                            is_typing: false
                        });
                    }, 1000);
                }
            });

            // 搜索访客
            document.getElementById('searchInput').addEventListener('input', function(e) {
                const keyword = e.target.value.toLowerCase();
                const items = document.querySelectorAll('.visitor-item');
                items.forEach(item => {
                    const name = item.dataset.name.toLowerCase();
                    item.style.display = name.includes(keyword) ? 'flex' : 'none';
                });
            });
        }

        // 添加访客到列表
        function addVisitorToList(visitor) {
            const visitorId = visitor.visitor_id;
            
            // 检查是否已存在
            if (document.getElementById('visitor_' + visitorId)) {
                return;
            }

            visitors[visitorId] = visitor;

            const visitorList = document.getElementById('visitorList');
            
            // 移除空状态
            const emptyState = visitorList.querySelector('.empty-state');
            if (emptyState) {
                emptyState.remove();
            }

            // ⚡ 格式化最后一条消息（带错误保护）
            let lastMsgDisplay = '等待接入...';
            if (visitor.last_message) {
                try {
                    lastMsgDisplay = formatLastMessage(visitor.last_message);
                } catch (e) {
                    console.error('格式化消息失败:', e, visitor.last_message);
                    lastMsgDisplay = '[消息格式错误]';
                }
            }
            
            // 格式化时间
            let timeDisplay = new Date().toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit'});
            if (visitor.last_message_time) {
                timeDisplay = new Date(visitor.last_message_time).toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit'});
            }

            const visitorItem = document.createElement('div');
            visitorItem.className = 'visitor-item';
            visitorItem.id = 'visitor_' + visitorId;
            visitorItem.dataset.name = visitor.name;
            visitorItem.onclick = function() {
                selectVisitor(visitorId);
            };

            visitorItem.innerHTML = `
                <div class="visitor-avatar">👤</div>
                <div class="visitor-info">
                    <div class="visitor-name">
                        ${visitor.name}
                        <span class="visitor-badge">新</span>
                    </div>
                    <div class="visitor-last-msg">${lastMsgDisplay}</div>
                    <div class="visitor-meta">
                        <span class="visitor-time">${timeDisplay}</span>
                        <span class="unread-count" style="display: none;">0</span>
                    </div>
                </div>
            `;

            visitorList.insertBefore(visitorItem, visitorList.firstChild);
        }

        // 移除访客
        function removeVisitorFromList(visitorId) {
            const item = document.getElementById('visitor_' + visitorId);
            if (item) {
                item.remove();
            }
            delete visitors[visitorId];
        }

        // 选择访客
        function selectVisitor(visitorId) {
            currentVisitorId = visitorId;
            const visitor = visitors[visitorId];

            // 更新选中状态
            document.querySelectorAll('.visitor-item').forEach(item => {
                item.classList.remove('active');
            });
            document.getElementById('visitor_' + visitorId).classList.add('active');

            // 显示聊天界面
            document.getElementById('chatContainer').style.display = 'none';
            const chatInterface = document.getElementById('chatInterfaceTemplate');
            chatInterface.style.display = 'flex';

            // 更新访客信息
            document.getElementById('currentVisitorName').textContent = visitor.name;
            document.getElementById('currentVisitorInfo').textContent = '来源: 网站首页';

            // 清空消息
            document.getElementById('chatMessages').innerHTML = '';

            // 添加欢迎消息
            addSystemMessage('开始与 ' + visitor.name + ' 的对话');

            // ⚡ 立即清除未读消息（前端显示）
            clearVisitorUnread(visitorId);
            
            // ⚡ 立即调用后端API标记该访客的消息为已读（数据库级别）
            fetch('/api/service/mark_visitor_read', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.CSRF ? window.CSRF.getToken() : ''
                },
                body: JSON.stringify({
                    visitor_id: visitorId
                })
            }).then(response => response.json())
              .then(data => {
                  if (data.code === 0) {
                      console.log(`✅ 已标记 ${data.data.updated_count} 条消息为已读`);
                  } else {
                      console.error('标记已读失败:', data.msg);
                  }
              })
              .catch(error => {
                  console.error('标记已读请求失败:', error);
              });
        }

        // 发送消息
        function sendMessage() {
            const messageInput = document.getElementById('messageInput');
            const content = messageInput.value.trim();

            if (!content || !currentVisitorId) return;

            // 添加到界面
            addMessage(content, 'service');

            // 发送到服务器
            socket.emit('send_message', {
                from_id: serviceId,
                from_type: 'service',
                to_id: currentVisitorId,
                to_type: 'visitor',
                content: content,
                type: 'text'
            });

            // 清空输入框
            messageInput.value = '';
            messageInput.style.height = 'auto';
        }

        // 快捷回复
        function sendQuickReply(text) {
            document.getElementById('messageInput').value = text;
            sendMessage();
        }

        // 添加消息到界面
        function addMessage(content, type, timestamp) {
            const messagesDiv = document.getElementById('chatMessages');
            
            // 添加日期分隔符
            const currentDate = formatDateOnly(timestamp || new Date());
            if (currentDate && currentDate !== lastMessageDate) {
                const dateSeparator = createDateSeparator(timestamp || new Date());
                messagesDiv.appendChild(dateSeparator);
                lastMessageDate = currentDate;
            }
            
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message ' + type;

            const time = timestamp ? new Date(timestamp).toLocaleTimeString('zh-CN', {
                hour: '2-digit',
                minute: '2-digit'
            }) : new Date().toLocaleTimeString('zh-CN', {
                hour: '2-digit',
                minute: '2-digit'
            });

            const avatar = type === 'visitor' ? '👤' : '👨‍💼';
            
            // 处理消息内容：支持HTML渲染
            let messageContent = content;
            try {
                // 尝试解析JSON格式（图片、文件等）
                const parsedContent = JSON.parse(content);
                if (parsedContent.type === 'file' && parsedContent.url) {
                    if (parsedContent.mime_type && parsedContent.mime_type.startsWith('image/')) {
                        // 图片消息：点击弹出预览窗口
                        messageContent = `<img src="${parsedContent.url}" alt="图片" style="max-width: 200px; max-height: 200px; border-radius: 8px; cursor: pointer;" onclick="showImagePreview('${parsedContent.url}')">`;
                    } else {
                        const fileSize = parsedContent.size ? formatFileSize(parsedContent.size) : '';
                        messageContent = `
                            <a href="${parsedContent.url}" target="_blank" class="file-link" style="display: flex; align-items: center; gap: 8px; text-decoration: none; color: var(--primary-color);">
                                <span style="font-size: 24px;">📎</span>
                                <div>
                                    <div style="font-weight: 500;">查看文件</div>
                                    ${fileSize ? `<div style="font-size: 12px; color: #9ca3af;">${fileSize}</div>` : ''}
                                </div>
                            </a>
                        `;
                    }
                } else {
                    messageContent = escapeHtml(content);
                }
            } catch (e) {
                // 不是JSON格式，检查是否包含HTML标签
                if (/<[^>]+>/.test(content)) {
                    // 包含HTML标签，进行清洁后渲染
                    messageContent = sanitizeHtml(content);
                } else {
                    // 普通文本，转义处理
                    messageContent = escapeHtml(content);
                }
            }

            messageDiv.innerHTML = `
                <div class="message-avatar">${avatar}</div>
                <div class="message-content">
                    <div class="message-bubble">${messageContent}</div>
                    <div class="message-time">${time}</div>
                </div>
            `;

            messagesDiv.appendChild(messageDiv);
            scrollToBottom();
        }

        // 添加系统消息
        function addSystemMessage(content) {
            const messagesDiv = document.getElementById('chatMessages');
            const messageDiv = document.createElement('div');
            messageDiv.style.textAlign = 'center';
            messageDiv.style.padding = '8px';
            messageDiv.style.color = '#94a3b8';
            messageDiv.style.fontSize = '12px';
            messageDiv.textContent = content;
            messagesDiv.appendChild(messageDiv);
            scrollToBottom();
        }

        // 更新统计
        function updateStats() {
            const onlineCount = Object.keys(visitors).length;
            document.getElementById('onlineCount').textContent = onlineCount;
            document.getElementById('pendingCount').textContent = onlineCount;
        }

        // 更新未读数
        function updateVisitorUnread(visitorId) {
            const item = document.getElementById('visitor_' + visitorId);
            if (item) {
                item.classList.add('unread');
                const unreadSpan = item.querySelector('.unread-count');
                if (unreadSpan) {
                    unreadSpan.style.display = 'block';
                    const count = parseInt(unreadSpan.textContent) + 1;
                    unreadSpan.textContent = count;
                }
            }
        }

        // 清除未读
        function clearVisitorUnread(visitorId) {
            const item = document.getElementById('visitor_' + visitorId);
            if (item) {
                item.classList.remove('unread');
                const unreadSpan = item.querySelector('.unread-count');
                if (unreadSpan) {
                    unreadSpan.style.display = 'none';
                    unreadSpan.textContent = '0';
                }
            }
        }
        
        // 更新访客最后一条消息显示
        function updateVisitorLastMessage(visitorId, content, timestamp) {
            const item = document.getElementById('visitor_' + visitorId);
            if (!item) return;
            
            const lastMsgEl = item.querySelector('.visitor-last-msg');
            const timeEl = item.querySelector('.visitor-time');
            
            if (lastMsgEl) {
                // ⚡ 格式化消息内容（带错误保护）
                try {
                    let displayMsg = formatLastMessage(content);
                    lastMsgEl.textContent = displayMsg;
                } catch (e) {
                    console.error('格式化消息失败:', e, content);
                    lastMsgEl.textContent = '[消息格式错误]';
                }
            }
            
            if (timeEl && timestamp) {
                const time = new Date(timestamp).toLocaleTimeString('zh-CN', {
                    hour: '2-digit',
                    minute: '2-digit'
                });
                timeEl.textContent = time;
            }
        }
        
        // ⚡ 消息格式化缓存（性能优化2025-10-26）
        const messageFormatCache = new Map();
        const MAX_CACHE_SIZE = 100;
        
        // 格式化最后一条消息（处理文件、图片、Emoji等特殊类型）
        function formatLastMessage(content) {
            if (!content) return '';
            
            // ⚡ 检查缓存（避免重复格式化）
            if (messageFormatCache.has(content)) {
                return messageFormatCache.get(content);
            }
            
            let result = '';
            
            try {
                // 尝试解析JSON（文件、图片等）
                const parsed = JSON.parse(content);
                
                if (parsed.type === 'file' || parsed.type === 'image') {
                    // 检查MIME类型
                    if (parsed.mime_type && parsed.mime_type.startsWith('image/')) {
                        result = '[图片]';
                    } else {
                        result = '[文件]';
                    }
                } else {
                    // 其他类型的JSON
                    result = content.length > 20 ? content.substring(0, 20) + '...' : content;
                }
            } catch (e) {
                // 不是JSON格式，处理为普通文本
                const trimmedContent = content.trim();
                
                // ⚡ 性能优化：只对短文本进行Emoji检测（避免长文本正则匹配耗时）
                const maxEmojiCheckLength = 50;
                if (trimmedContent.length <= maxEmojiCheckLength) {
                    const emojiRegex = /^[\p{Emoji}\u200d]+$/u;
                    if (emojiRegex.test(trimmedContent)) {
                        // 如果是纯Emoji，显示Emoji本身（最多显示3个字符）
                        result = trimmedContent.length > 3 
                            ? trimmedContent.substring(0, 3) + '...' 
                            : trimmedContent;
                    } else {
                        // 普通短文本
                        result = trimmedContent.length > 20 
                            ? trimmedContent.substring(0, 20) + '...' 
                            : trimmedContent;
                    }
                } else {
                    // 长文本直接截取，不进行Emoji检测
                    result = trimmedContent.substring(0, 20) + '...';
                }
            }
            
            // ⚡ 缓存结果（限制缓存大小，防止内存泄漏）
            if (messageFormatCache.size >= MAX_CACHE_SIZE) {
                const firstKey = messageFormatCache.keys().next().value;
                messageFormatCache.delete(firstKey);
            }
            messageFormatCache.set(content, result);
            
            return result;
        }

        // 滚动到底部
        function scrollToBottom() {
            const messagesDiv = document.getElementById('chatMessages');
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        // HTML转义
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // ========== 图片预览功能 (Image Preview Lightbox) ==========
        
        /**
         * 显示图片预览弹窗
         * @param {string} imageUrl - 图片URL
         */
        function showImagePreview(imageUrl) {
            // 创建预览容器
            const previewContainer = document.createElement('div');
            previewContainer.id = 'imagePreviewModal';
            previewContainer.className = 'image-preview-modal';
            
            previewContainer.innerHTML = `
                <div class="image-preview-backdrop" onclick="closeImagePreview()"></div>
                <div class="image-preview-content">
                    <button class="image-preview-close" onclick="closeImagePreview()" title="关闭 (ESC)">
                        ✕
                    </button>
                    <img src="${imageUrl}" alt="图片预览" class="image-preview-img">
                </div>
            `;
            
            document.body.appendChild(previewContainer);
            
            // 添加动画效果
            setTimeout(() => {
                previewContainer.classList.add('show');
            }, 10);
            
            // 监听ESC键关闭
            document.addEventListener('keydown', handlePreviewEscape);
        }
        
        /**
         * 关闭图片预览弹窗
         */
        function closeImagePreview() {
            const modal = document.getElementById('imagePreviewModal');
            if (modal) {
                modal.classList.remove('show');
                
                // 等待动画结束后移除元素
                setTimeout(() => {
                    modal.remove();
                }, 300);
            }
            
            // 移除ESC监听
            document.removeEventListener('keydown', handlePreviewEscape);
        }
        
        /**
         * 处理ESC键按下事件
         */
        function handlePreviewEscape(e) {
            if (e.key === 'Escape') {
                closeImagePreview();
            }
        }

        // 转接会话
        function transferChat() {
            modal.info('转接功能开发中...', '功能提示');
        }

        // 结束会话
        function endChat() {
            modal.confirm('确定要结束当前会话吗？', () => {
                // TODO: 发送结束会话事件
                document.getElementById('chatInterfaceTemplate').style.display = 'none';
                document.getElementById('chatContainer').style.display = 'flex';
                currentVisitorId = null;
            });
        }