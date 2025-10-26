/**
 * 访客聊天界面 - Script
 */

// 访客信息
        const visitorId = 'visitor_' + Date.now();
        const visitorName = '访客' + Math.floor(Math.random() * 1000);
        let socket = null;
        let currentServiceId = null;
        let typingTimeout = null;

        // 初始化
        document.addEventListener('DOMContentLoaded', function() {
            initSocket();
            initInput();
        });

        // 初始化Socket.IO连接
        function initSocket() {
            const connectionStatus = document.getElementById('connectionStatus');
            connectionStatus.classList.add('show');
            connectionStatus.textContent = '正在连接客服...';

            socket = io({
                transports: ['websocket', 'polling']
            });

            // 连接成功
            socket.on('connect', function() {
                console.log('Socket connected:', socket.id);
                
                // 访客加入
                socket.emit('visitor_join', {
                    visitor_id: visitorId,
                    visitor_name: visitorName,
                    avatar: '👤'
                });
            });

            // 加入成功
            socket.on('join_success', function(data) {
                console.log('Join success:', data);
                connectionStatus.classList.remove('show');
                addSystemMessage('已连接到客服系统');
            });

            // 接收消息
            socket.on('receive_message', function(data) {
                console.log('Received message:', data);
                addMessage(data.content, 'service', data.timestamp);
            });

            // 消息发送成功
            socket.on('message_sent', function(data) {
                console.log('Message sent:', data);
            });

            // 用户正在输入
            socket.on('user_typing', function(data) {
                const typingIndicator = document.getElementById('typingIndicator');
                if (data.is_typing) {
                    typingIndicator.classList.add('show');
                } else {
                    typingIndicator.classList.remove('show');
                }
            });

            // 新客服上线
            socket.on('service_online', function(data) {
                document.getElementById('serviceName').textContent = data.service_name;
                currentServiceId = data.service_id;
                addSystemMessage(data.service_name + ' 已上线');
            });

            // 连接错误
            socket.on('connect_error', function(error) {
                console.error('Connection error:', error);
                connectionStatus.classList.add('show');
                connectionStatus.textContent = '连接失败，正在重试...';
            });

            // 断开连接
            socket.on('disconnect', function() {
                console.log('Socket disconnected');
                connectionStatus.classList.add('show');
                connectionStatus.textContent = '连接已断开';
            });

            // 错误处理
            socket.on('error', function(data) {
                console.error('Socket error:', data);
                addSystemMessage('发生错误: ' + data.message);
            });
        }

        // 初始化输入框
        function initInput() {
            const messageInput = document.getElementById('messageInput');
            const sendBtn = document.getElementById('sendBtn');

            // 回车发送
            messageInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    sendMessage();
                }
            });

            // 点击发送
            sendBtn.addEventListener('click', sendMessage);

            // 输入状态
            messageInput.addEventListener('input', function() {
                if (currentServiceId) {
                    clearTimeout(typingTimeout);
                    
                    socket.emit('typing', {
                        from_id: visitorId,
                        from_type: 'visitor',
                        from_name: visitorName,
                        to_id: currentServiceId,
                        to_type: 'service',
                        is_typing: true
                    });

                    typingTimeout = setTimeout(function() {
                        socket.emit('typing', {
                            from_id: visitorId,
                            from_type: 'visitor',
                            to_id: currentServiceId,
                            to_type: 'service',
                            is_typing: false
                        });
                    }, 1000);
                }
            });
        }

        // 发送消息
        function sendMessage() {
            const messageInput = document.getElementById('messageInput');
            const content = messageInput.value.trim();

            if (!content) return;

            if (!socket || !socket.connected) {
                modal.warning('未连接到服务器');
                return;
            }

            // 添加到界面
            addMessage(content, 'visitor');

            // 发送到服务器
            socket.emit('send_message', {
                from_id: visitorId,
                from_type: 'visitor',
                to_id: currentServiceId || 1,
                to_type: 'service',
                content: content,
                type: 'text'
            });

            // 清空输入框
            messageInput.value = '';
        }

        // 添加消息到界面
        function addMessage(content, type, timestamp) {
            const messagesDiv = document.getElementById('chatMessages');
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

            messageDiv.innerHTML = `
                <div class="message-avatar">${avatar}</div>
                <div class="message-content">
                    <div class="message-bubble">${escapeHtml(content)}</div>
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

        // 结束会话
        function endChat() {
            if (confirm('确定要结束会话吗？')) {
                if (socket) {
                    socket.disconnect();
                }
                window.close();
            }
        }