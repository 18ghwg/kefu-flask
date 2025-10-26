
        // ========== 工具函数：HTML清洁和日期格式化 ==========
        
        // HTML清洁函数（防止XSS，但允许安全的HTML标签）
        // 🛡️ 增强版：支持安全的HTML标签白名单（用于机器人消息）
        function sanitizeHtml(html) {
            if (!html) return '';
            const temp = document.createElement('div');
            temp.innerHTML = html;
            
            // 移除危险标签（保留安全标签：a, p, br, strong, em, u, b, i）
            temp.querySelectorAll('script, style, iframe, object, embed, form, input, button, link, meta').forEach(el => el.remove());
            
            // 移除危险属性（保留安全属性：href, title, target, style的某些安全属性）
            temp.querySelectorAll('*').forEach(el => {
                Array.from(el.attributes).forEach(attr => {
                    // 移除所有on*事件处理器和危险属性
                    if (attr.name.startsWith('on') || attr.name === 'formaction' || attr.name === 'form') {
                        el.removeAttribute(attr.name);
                    }
                });
                
                // 清理链接：只允许http/https/mailto协议
                if (el.tagName === 'A' && el.hasAttribute('href')) {
                    const href = el.getAttribute('href');
                    if (href && !href.match(/^(https?:|mailto:)/i)) {
                        el.removeAttribute('href');
                    }
                    // 外部链接添加安全属性
                    if (href && href.match(/^https?:/i)) {
                        el.setAttribute('target', '_blank');
                        el.setAttribute('rel', 'noopener noreferrer');
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
        
        // ========== 访客身份识别和设备信息收集 ==========
        
        // 生成设备指纹（简单版）
        function generateDeviceFingerprint() {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            ctx.textBaseline = 'top';
            ctx.font = '14px Arial';
            ctx.fillText('fingerprint', 2, 2);
            const canvasData = canvas.toDataURL();
            
            const fingerprint = {
                userAgent: navigator.userAgent,
                language: navigator.language,
                platform: navigator.platform,
                screen: `${screen.width}x${screen.height}`,
                timezone: new Date().getTimezoneOffset(),
                canvas: canvasData.substring(0, 100)
            };
            
            // 生成简单hash
            const str = JSON.stringify(fingerprint);
            let hash = 0;
            for (let i = 0; i < str.length; i++) {
                const char = str.charCodeAt(i);
                hash = ((hash << 5) - hash) + char;
                hash = hash & hash;
            }
            return 'fp_' + Math.abs(hash).toString(36);
        }
        
        // 获取客户端真实IP地址（通过后端代理接口，避免CORS问题）
        async function getClientIP() {
            try {
                const response = await fetch('/api/visitor/get-client-ip', {
                    method: 'GET',
                    cache: 'no-cache'
                });
                
                if (response.ok) {
                    const result = await response.json();
                    if (result.code === 0 && result.data && result.data.ip) {
                        const ip = result.data.ip;
                        
                        // 验证IPv4格式
                        if (ip && /^(\d{1,3}\.){3}\d{1,3}$/.test(ip) && ip !== '127.0.0.1') {
                            console.log('✅ 获取客户端IPv4:', ip);
                            return ip;
                        }
                    }
                }
            } catch (error) {
                console.log('客户端IP获取失败，将使用服务端IP');
            }
            return null; // 失败时返回null，使用服务端获取的IP
        }
        
        // 获取设备信息
        function getDeviceInfo() {
            const ua = navigator.userAgent;
            let browser = 'Unknown';
            let os = 'Unknown';
            let device = 'Desktop';
            
            // 检测浏览器（注意顺序：先检测更具体的浏览器）
            if (ua.indexOf('Edg') > -1) {
                browser = 'Edge';  // 新版Edge基于Chromium
            } else if (ua.indexOf('Chrome') > -1 && ua.indexOf('Edg') === -1) {
                browser = 'Chrome';
            } else if (ua.indexOf('Firefox') > -1) {
                browser = 'Firefox';
            } else if (ua.indexOf('Safari') > -1 && ua.indexOf('Chrome') === -1) {
                browser = 'Safari';  // 只有Safari，不是Chrome
            } else if (ua.indexOf('MSIE') > -1 || ua.indexOf('Trident') > -1) {
                browser = 'IE';
            } else if (ua.indexOf('Opera') > -1 || ua.indexOf('OPR') > -1) {
                browser = 'Opera';
            }
            
            // 检测操作系统
            if (ua.indexOf('Windows NT 10') > -1) {
                os = 'Windows 10/11';
            } else if (ua.indexOf('Windows NT 6.3') > -1) {
                os = 'Windows 8.1';
            } else if (ua.indexOf('Windows NT 6.2') > -1) {
                os = 'Windows 8';
            } else if (ua.indexOf('Windows NT 6.1') > -1) {
                os = 'Windows 7';
            } else if (ua.indexOf('Windows') > -1) {
                os = 'Windows';
            } else if (ua.indexOf('Mac OS X') > -1) {
                // 提取MacOS版本
                const match = ua.match(/Mac OS X ([\d_]+)/);
                if (match) {
                    const version = match[1].replace(/_/g, '.');
                    os = 'MacOS ' + version.split('.').slice(0, 2).join('.');
                } else {
                    os = 'MacOS';
                }
            } else if (ua.indexOf('Linux') > -1) {
                os = 'Linux';
            } else if (ua.indexOf('Android') > -1) {
                // 提取Android版本
                const match = ua.match(/Android ([\d.]+)/);
                os = match ? 'Android ' + match[1] : 'Android';
            } else if (ua.indexOf('iOS') > -1 || ua.indexOf('iPhone') > -1 || ua.indexOf('iPad') > -1) {
                // 提取iOS版本
                const match = ua.match(/OS ([\d_]+)/);
                if (match) {
                    const version = match[1].replace(/_/g, '.');
                    os = 'iOS ' + version.split('.').slice(0, 2).join('.');
                } else {
                    os = 'iOS';
                }
            }
            
            // 检测设备类型
            if (ua.indexOf('Mobile') > -1 || ua.indexOf('Android') > -1 || ua.indexOf('iPhone') > -1) {
                device = 'Mobile';
            } else if (ua.indexOf('Tablet') > -1 || ua.indexOf('iPad') > -1) {
                device = 'Tablet';
            }
            
            console.log('Device Info:', {
                browser: browser,
                os: os,
                device: device,
                ua: ua
            });
            
            return {
                browser: browser,
                os: os,
                device: device,
                user_agent: ua,
                screen_resolution: `${screen.width}x${screen.height}`,
                language: navigator.language,
                referrer: document.referrer,
                from_url: window.location.href
            };
        }
        
        // 获取或生成访客ID
        function getOrCreateVisitorId() {
            // 先检查localStorage
            let savedVisitorId = localStorage.getItem('visitor_id');
            let savedVisitorName = localStorage.getItem('visitor_name');
            
            if (!savedVisitorId) {
                // 如果没有保存的ID，生成新的
                const fingerprint = generateDeviceFingerprint();
                const timestamp = Date.now();
                const random = Math.floor(Math.random() * 1000);
                
                savedVisitorId = `visitor_${timestamp}_${random}`;
                savedVisitorName = '访客' + Math.floor(Math.random() * 10000);
                
                // 保存到localStorage
                localStorage.setItem('visitor_id', savedVisitorId);
                localStorage.setItem('visitor_name', savedVisitorName);
                localStorage.setItem('device_fingerprint', fingerprint);
                localStorage.setItem('first_visit', new Date().toISOString());
                localStorage.setItem('visit_count', '1');
            } else {
                // 老访客，更新访问次数
                const visitCount = parseInt(localStorage.getItem('visit_count') || '1') + 1;
                localStorage.setItem('visit_count', visitCount.toString());
                localStorage.setItem('last_visit', new Date().toISOString());
            }
            
            return {
                visitorId: savedVisitorId,
                visitorName: savedVisitorName,
                deviceFingerprint: localStorage.getItem('device_fingerprint'),
                visitCount: parseInt(localStorage.getItem('visit_count') || '1'),
                firstVisit: localStorage.getItem('first_visit'),
                lastVisit: localStorage.getItem('last_visit')
            };
        }
        
        // 初始化访客信息
        const visitorInfo = getOrCreateVisitorId();
        const visitorId = visitorInfo.visitorId;
        const visitorName = visitorInfo.visitorName;
        const deviceInfo = getDeviceInfo();
        
        // ✅ 暴露访客ID和商户ID为全局变量（供评价功能使用）
        window.visitorId = visitorId;
        window.visitorName = visitorName;
        window.businessId = 1;  // 默认商户ID
        window.currentServiceId = null;  // 当前客服ID（分配后更新）
        
        // 异步获取客户端真实IP
        let clientRealIP = null;
        getClientIP().then(ip => {
            if (ip) {
                clientRealIP = ip;
                deviceInfo.client_ip = ip;
                console.log('✅ 客户端真实IP已获取:', ip);
            }
        });
        
        // 访客信息（自动生成）
        let socket = null;
        let currentServiceId = null;
        let typingTimeout = null;
        let hasOnlineService = false; // 是否有在线客服
        let useRobotMode = false; // 是否使用机器人模式
        let statusCheckInterval = null; // 客服状态检测定时器
        let offlineCheckCount = 0; // 离线检测计数器（连续检测不到在线客服的次数）
        const MAX_OFFLINE_CHECK = 10; // 最大离线检测次数
        let isInitialPhase = true; // 是否处于初始检测阶段（初始用1秒，稳定后用5秒）
        let initialCheckCount = 0; // 初始检测计数器

        // 更新客服在线状态
        function updateServiceOnlineStatus(services, total) {
            const statusDot = document.querySelector('.status-dot');
            const statusText = document.getElementById('statusText');
            const serviceName = document.getElementById('serviceName');
            
            const wasOffline = !hasOnlineService; // 记录之前是否离线
            hasOnlineService = total > 0;
            useRobotMode = !hasOnlineService;
            
            if (hasOnlineService) {
                // 有客服在线 - 立即更新UI
                console.log(`✅ 立即渲染：${total}位客服在线`);
                
                // 重置离线检测计数器
                offlineCheckCount = 0;
                
                // 🆕 检测到客服在线，结束初始阶段，切换到5秒轮询
                if (isInitialPhase) {
                    console.log('✅ 检测到客服在线，切换到5秒轮询模式');
                    isInitialPhase = false;
                    // 重启定时器，使用5秒间隔
                    startStatusCheck();
                }
                
                // 强制立即更新DOM
                if (statusDot) statusDot.style.background = '#10b981';
                if (statusText) statusText.textContent = `在线 (${total})`;
                
                // ✅ 优先显示当前分配的客服名称
                if (serviceName) {
                    if (window.currentServiceName) {
                        serviceName.textContent = window.currentServiceName;
                    } else if (total === 1 && services[0]) {
                        serviceName.textContent = services[0].name;
                    } else {
                        serviceName.textContent = '在线客服';
                    }
                }
                
                // 如果之前是离线状态，现在上线了，显示提示
                if (wasOffline && total > 0) {
                    addSystemMessage('客服已上线，将为您继续服务');
                }
            } else {
                // 没有检测到在线客服
                offlineCheckCount++;
                
                // 🆕 初始阶段计数
                if (isInitialPhase) {
                    initialCheckCount++;
                    console.log(`🔍 初始检测（第${initialCheckCount}次），未检测到在线客服`);
                    
                    // 初始阶段检测10次后（10秒），切换到5秒轮询
                    if (initialCheckCount >= 10) {
                        console.log('⏱️ 初始检测10秒已过，切换到5秒轮询模式');
                        isInitialPhase = false;
                        offlineCheckCount = 10; // 直接判定为离线
                        // 重启定时器，使用5秒间隔
                        startStatusCheck();
                    }
                }
                
                // ✅ 只在关键节点输出警告，避免控制台刷屏
                if (offlineCheckCount === 1 || offlineCheckCount === 5 || offlineCheckCount >= MAX_OFFLINE_CHECK) {
                    console.log(`⚠️ 未检测到在线客服（离线计数：${offlineCheckCount}/${MAX_OFFLINE_CHECK}次）`);
                }
                
                // 连续10次检测不到才判定为离线
                if (offlineCheckCount >= MAX_OFFLINE_CHECK) {
                    // 无客服在线，切换到机器人模式 - 立即更新UI
                    console.log('⚠️ 连续10次检测无在线客服，切换机器人模式');
                    
                    // 强制立即更新DOM
                    if (statusDot) statusDot.style.background = '#f59e0b';
                    if (statusText) statusText.textContent = '机器人客服';
                    if (serviceName) serviceName.textContent = '智能助手';
                    
                    // 如果之前是在线状态，现在下线了，显示提示（只提示一次）
                    if (!wasOffline) {
                        addSystemMessage('当前暂无客服在线，智能助手为您服务');
                        // 更新hasOnlineService状态，避免重复提示
                        hasOnlineService = false;
                        useRobotMode = true;
                    }
                }
            }
            
            // 🆕 无论客服在线还是离线，都要持续检测状态变化
            // 如果定时器未启动，则启动它
            if (!statusCheckInterval) {
                startStatusCheck();
            }
        }
        
        // 启动客服状态检测（初始1秒，稳定后5秒）
        function startStatusCheck() {
            // 如果已有定时器，先清除
            stopStatusCheck();
            
            // 🆕 根据阶段选择间隔：初始阶段1秒，稳定阶段5秒
            const interval = isInitialPhase ? 1000 : 5000;  // 初始1秒，稳定5秒
            
            const intervalText = isInitialPhase ? '每1秒（初始快速检测）' : '每5秒（稳定轮询）';
            console.log(`🔄 启动客服状态检测（${intervalText}）`);
            
            statusCheckInterval = setInterval(() => {
                if (socket && socket.connected) {
                    const phase = isInitialPhase ? '初始' : '稳定';
                    console.log(`🔍 [${phase}阶段] 检查客服在线状态...`);
                    socket.emit('get_online_users');
                }
            }, interval);
        }
        
        // 停止客服状态检测
        function stopStatusCheck() {
            if (statusCheckInterval) {
                console.log('⏹️ 停止客服状态检测');
                clearInterval(statusCheckInterval);
                statusCheckInterval = null;
            }
        }
        
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
                
                // 确保device_info包含最新的IP信息
                if (clientRealIP && !deviceInfo.client_ip) {
                    deviceInfo.client_ip = clientRealIP;
                }
                
                // 获取专属客服ID（如果有）
                const specialServiceId = window.CHAT_CONFIG?.special || '';
                
                // 访客加入，发送完整的设备信息
                socket.emit('visitor_join', {
                    visitor_id: visitorId,
                    visitor_name: visitorName,
                    avatar: '👤',
                    business_id: 1,
                    special: specialServiceId,  // 🆕 指定客服ID
                    device_info: deviceInfo,
                    visit_info: {
                        device_fingerprint: visitorInfo.deviceFingerprint,
                        visit_count: visitorInfo.visitCount,
                        first_visit: visitorInfo.firstVisit,
                        last_visit: visitorInfo.lastVisit
                    }
                });
            });

            // 加入成功
            socket.on('join_success', function(data) {
                console.log('Join success:', data);
                // 立即隐藏连接状态
                connectionStatus.classList.remove('show');
                connectionStatus.textContent = '';
                addSystemMessage('已连接到客服系统');
                
                // ✅ 保存当前分配的客服信息
                if (data.queue && data.queue.service_id) {
                    window.currentServiceId = data.queue.service_id;
                    window.currentServiceName = data.queue.service_name;
                    console.log('✅ 当前分配的客服:', window.currentServiceName, '(ID:', window.currentServiceId, ')');
                }
                
                // ⚡ 直接使用返回的在线状态（优化：无需额外请求）
                if (data.online_services !== undefined && data.total_services !== undefined) {
                    console.log('✅ join_success返回在线状态，立即更新UI');
                    console.log('   - 在线客服数:', data.total_services);
                    console.log('   - 客服列表:', data.online_services);
                    
                    // 立即更新界面（不等待下一轮检测）
                    updateServiceOnlineStatus(data.online_services, data.total_services);
                } else {
                    // 兼容旧逻辑：如果后端未返回在线状态，则主动请求
                    console.log('⚠️ 后端未返回在线状态，主动请求');
                    socket.emit('get_online_users');
                }
                
                // 🆕 强制启动定时器（确保一定会轮询）
                console.log('🚀 强制启动客服状态轮询定时器...');
                if (!statusCheckInterval) {
                    startStatusCheck();
                } else {
                    console.log('⚠️ 定时器已存在，跳过启动');
                }
                
                // 其他内容延迟加载（不阻塞在线状态检测）
                setTimeout(() => {
                    // 🤖 自动发送问候语
                    loadGreetingMessage();
                    
                    // 📋 加载常见问题气泡
                    loadFAQBubbles();
                }, 300);
                
                // 老访客异步加载历史消息（不阻塞UI）
                if (visitorInfo.visitCount > 1) {
                    setTimeout(() => {
                        loadChatHistory();
                    }, 100); // 延迟100ms加载，让UI先渲染
                }
            });
            
            // 监听在线用户列表更新
            socket.on('online_users_list', function(data) {
                console.log('Online users:', data);
                updateServiceOnlineStatus(data.services || [], data.total_services || 0);
            });

            // 接收消息
            socket.on('receive_message', function(data) {
                console.log('Received message:', data);
                
                // ✅ 如果消息来自客服，更新当前客服信息
                if (data.from_type === 'service' && data.from_id && data.from_name) {
                    window.currentServiceId = data.from_id;
                    window.currentServiceName = data.from_name;
                    const serviceNameEl = document.getElementById('serviceName');
                    if (serviceNameEl && window.currentServiceName) {
                        serviceNameEl.textContent = window.currentServiceName;
                    }
                }
                
                // 根据消息来源判断类型
                const messageType = (data.from_type === 'visitor') ? 'visitor' : (data.from_type === 'robot' ? 'robot' : 'service');
                const nickname = data.nickname || (messageType === 'robot' ? '智能助手' : '客服');
                const avatar = data.avatar || (messageType === 'robot' ? '🤖' : '👨‍💼');
                addMessage(messageType, nickname, data.content, avatar, data.timestamp);
                
                // 如果是客服或机器人发来的消息，触发提示
                if (data.from_type === 'service' || data.from_type === 'robot') {
                    // 播放提示音
                    playNotificationSound();
                    
                    // 标题闪烁
                    startTitleFlash(data.content);
                    
                    // 桌面通知（如果页面不可见）
                    if (!isPageVisible) {
                        const senderName = data.from_name || (data.from_type === 'robot' ? '智能助手' : '客服');
                        const messagePreview = data.content.length > 30 
                            ? data.content.substring(0, 30) + '...' 
                            : data.content;
                        showDesktopNotification(`新消息来自 ${senderName}`, messagePreview);
                    }
                }
                
                // 如果是机器人消息，显示提示
                if (data.from_type === 'robot') {
                    console.log('智能助手回复:', data.content);
                }
            });

            // 🚫 监听消息被拦截事件
            socket.on('message_blocked', function(data) {
                console.warn('🚫 消息被拦截:', data);
                // 显示被拦截的消息（带红色感叹号）
                addBlockedMessage(data.msg || '您已被限制发送消息', data.timestamp);
            });

            // 🚫 监听黑名单事件
            socket.on('blacklisted', function(data) {
                console.warn('🚫 您在黑名单中:', data);
                // 显示黑名单提示
                addSystemMessage(data.message || '您已被限制访问，如有疑问请联系管理员', 'error');
                // 禁用输入框
                const messageInput = document.getElementById('messageInput');
                const sendBtn = document.getElementById('sendBtn');
                if (messageInput) {
                    messageInput.disabled = true;
                    messageInput.placeholder = '您已被限制发送消息';
                }
                if (sendBtn) {
                    sendBtn.disabled = true;
                }
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
                window.currentServiceId = data.service_id;
                window.currentServiceName = data.service_name;
                addSystemMessage(data.service_name + ' 已上线为您服务');
            });

            // ✅ 监听客服变更事件
            socket.on('service_changed', function(data) {
                console.log('🔄 客服已变更:', data);
                // 更新当前客服信息
                window.currentServiceId = data.service_id;
                window.currentServiceName = data.service_name;
                
                // 更新界面显示
                const serviceNameEl = document.getElementById('serviceName');
                if (serviceNameEl) {
                    serviceNameEl.textContent = data.service_name;
                }
                
                // 显示系统消息
                if (data.message) {
                    addSystemMessage(data.message);
                }
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
                
                // 停止状态检测定时器
                stopStatusCheck();
                
                // 重置在线状态显示
                const statusDot = document.querySelector('.status-dot');
                const statusText = document.getElementById('statusText');
                statusDot.style.background = '#ef4444'; // 红色表示断开
                statusText.textContent = '离线';
            });

            // 重新连接
            socket.on('reconnect', function() {
                console.log('Socket reconnected');
                connectionStatus.classList.remove('show');
                addSystemMessage('重新连接成功');
                
                // 获取专属客服ID（如果有）
                const specialServiceId = window.CHAT_CONFIG?.special || '';
                
                // 重新加入房间
                socket.emit('visitor_join', {
                    visitor_id: visitorId,
                    visitor_name: visitorName,
                    avatar: '👤',
                    business_id: 1,
                    special: specialServiceId,  // 🆕 指定客服ID
                    device_info: getDeviceInfo(),
                    visit_info: {
                        from_url: document.referrer || 'direct',
                        current_url: window.location.href,
                        visit_count: visitorInfo.visitCount
                    }
                });
                
                // 重新获取在线用户列表
                socket.emit('get_online_users');
            });

            // 错误处理
            socket.on('error', function(data) {
                console.error('Socket error:', data);
                addSystemMessage('发生错误: ' + data.message);
            });
            
            // 接收评价请求
            socket.on('request_comment', function(data) {
                console.log('收到评价请求:', data);
                
                commentQueueId = data.queue_id;
                commentServiceId = data.service_id;
                
                // 显示评价弹窗
                document.getElementById('commentServiceName').textContent = data.service_name || '客服';
                document.getElementById('commentQueueId').value = commentQueueId;
                document.getElementById('commentServiceId').value = commentServiceId;
                document.getElementById('commentContent').value = '';
                
                // 重置星级
                currentRating = 0;
                document.querySelectorAll('#starRating .star').forEach(star => {
                    star.classList.remove('active');
                    star.textContent = '☆';
                });
                document.getElementById('ratingText').textContent = '点击星星进行评分';
                
                // 初始化标签
                selectedTags = [];
                loadCommentTags();
            
            // 接收排队通知
            socket.on('queue_notification', function(data) {
                console.log('收到排队通知:', data);
                
                // 显示排队提示
                addSystemMessage(data.message);
                
                // 如果有排队位置，显示位置信息
                if (data.queue_position && data.queue_position > 0) {
                    addSystemMessage(`您当前排在第 ${data.queue_position} 位`);
                }
                
                // 更新状态显示
                updateStatus('排队中', false);
            });
            
            // 接收会话超时通知
            socket.on('session_timeout', function(data) {
                console.log('会话超时:', data);
                
                // 显示超时消息
                addSystemMessage('由于长时间无操作，会话已自动结束');
                
                // 更新状态
                updateStatus('会话已结束', false);
                
                // 禁用输入
                document.getElementById('messageInput').disabled = true;
                document.getElementById('sendBtn').disabled = true;
            });
                
                // 显示弹窗
                document.getElementById('commentModal').style.display = 'flex';
            });
        }

        // 初始化输入框
        function initInput() {
            const messageInput = document.getElementById('messageInput');
            const sendBtn = document.getElementById('sendBtn');
            const emojiBtn = document.getElementById('emojiBtn');
            const imageBtn = document.getElementById('imageBtn');
            const imageInput = document.getElementById('imageInput');

            // 用户首次交互时初始化AudioContext（解决Chrome自动播放限制）
            function handleFirstInteraction() {
                initAudioContext();
            }
            
            // 在多个交互点添加监听，确保AudioContext能被初始化
            messageInput.addEventListener('focus', handleFirstInteraction, { once: true });
            messageInput.addEventListener('click', handleFirstInteraction, { once: true });
            sendBtn.addEventListener('click', handleFirstInteraction, { once: true });
            
            // ✅ 添加全局点击/触摸监听，用户点击页面任意位置都能初始化
            document.addEventListener('click', handleFirstInteraction, { once: true });
            document.addEventListener('touchstart', handleFirstInteraction, { once: true });

            // 回车发送
            messageInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    sendMessage();
                }
            });

            // 粘贴图片上传
            messageInput.addEventListener('paste', function(e) {
                const items = e.clipboardData.items;
                for (let i = 0; i < items.length; i++) {
                    if (items[i].type.indexOf('image') !== -1) {
                        e.preventDefault();
                        const blob = items[i].getAsFile();
                        uploadImage(blob);
                        break;
                    }
                }
            });

            // 点击发送
            sendBtn.addEventListener('click', sendMessage);
            
            // Emoji选择器
            emojiBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                window.emojiPicker.show(emojiBtn, messageInput);
            });
            
            // 图片选择（访客只能上传图片）
            imageBtn.addEventListener('click', function() {
                imageInput.click();
            });
            
            imageInput.addEventListener('change', function(e) {
                const file = e.target.files[0];
                if (file) {
                    uploadImage(file);
                }
                // 清空input，允许重复选择同一文件
                e.target.value = '';
            });

            // 输入状态
            messageInput.addEventListener('input', function() {
                if (socket && socket.connected) {
                    clearTimeout(typingTimeout);
                    
                    socket.emit('typing', {
                        from_id: visitorId,
                        from_type: 'visitor',
                        from_name: visitorName,
                        to_id: currentServiceId || 'all',
                        to_type: 'service',
                        is_typing: true
                    });

                    typingTimeout = setTimeout(function() {
                        socket.emit('typing', {
                            from_id: visitorId,
                            from_type: 'visitor',
                            to_id: currentServiceId || 'all',
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
                modal.error('未连接到服务器，请稍后再试');
                return;
            }

            // 添加到界面（修复参数顺序：type, nickname, content, avatar, timestamp）
            addMessage('visitor', '访客', content, '👤', new Date());

            // 更新设备信息（可能IP已更新）
            const currentDeviceInfo = getDeviceInfo();
            if (clientRealIP) {
                currentDeviceInfo.client_ip = clientRealIP;
            }

            // 发送到服务器（附带设备信息）
            socket.emit('send_message', {
                from_id: visitorId,
                from_type: 'visitor',
                from_name: visitorName,
                to_id: currentServiceId || 'all',
                to_type: 'service',
                content: content,
                msg_type: 'text',
                timestamp: new Date().toISOString(),
                device_info: currentDeviceInfo,  // 附带设备信息
                business_id: 1
            });

            // 清空输入框
            messageInput.value = '';
        }

        // 添加消息到聊天界面（支持机器人和客服）
        function addMessage(type, nickname, content, avatar, timestamp) {
            const messagesContainer = document.getElementById('chatMessages');
            
            // 添加日期分隔符
            const currentDate = formatDateOnly(timestamp || new Date());
            if (currentDate && currentDate !== lastMessageDate) {
                const dateSeparator = createDateSeparator(timestamp || new Date());
                messagesContainer.appendChild(dateSeparator);
                lastMessageDate = currentDate;
            }
            
            const messageEl = document.createElement('div');
            messageEl.className = 'message ' + type;
            
            // 如果没有传timestamp，使用当前时间
            const time = formatTime(timestamp || new Date());
            
            // 确定头像
            let avatarIcon = avatar || '👤';
            if (type === 'service' && !avatar) avatarIcon = '👨‍💼';
            if (type === 'robot' && !avatar) avatarIcon = '🤖';
            
            // 确定徽章
            let badge = '';
            if (type === 'robot') {
                badge = '<span class="message-badge robot-badge">AI助手</span>';
            } else if (type === 'service') {
                badge = '<span class="message-badge service-badge">客服</span>';
            }
            
            // 确定昵称
            const displayName = nickname || (type === 'robot' ? '智能助手' : type === 'service' ? '客服' : '访客');
            
            // 🛡️ 安全渲染：区分机器人消息和用户消息
            // 机器人消息（type='robot'）：允许渲染安全的HTML标签（如超链接）
            // 用户消息（访客/客服）：强制转义HTML，防止XSS攻击
            let messageContent = content;
            let isHtmlContent = false;
            
            try {
                // 尝试解析JSON格式的内容（图片、文件等）
                const parsedContent = JSON.parse(content);
                if (parsedContent.type === 'file' && parsedContent.url) {
                    isHtmlContent = true;
                    // 判断是图片还是文件
                    if (parsedContent.mime_type && parsedContent.mime_type.startsWith('image/')) {
                        // 渲染图片：点击弹出预览窗口
                        messageContent = `<img src="${parsedContent.url}" alt="图片" style="max-width: 200px; max-height: 200px; border-radius: 8px; cursor: pointer;" onclick="showImagePreview('${parsedContent.url}')">`;
                    } else {
                        // 渲染文件链接
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
                }
            } catch (e) {
                // 不是JSON格式，根据消息来源处理
                if (type === 'robot') {
                    // 🤖 机器人消息：检查是否包含HTML标签
                    if (/<[^>]+>/.test(content)) {
                        // 包含HTML标签，使用sanitizeHtml清洁后渲染（允许安全标签如<a>）
                        messageContent = sanitizeHtml(content);
                        isHtmlContent = true;
                        console.log('🤖 机器人消息已渲染HTML:', messageContent.substring(0, 100));
                    } else {
                        // 普通文本内容
                        messageContent = content;
                    }
                } else {
                    // 👤 用户消息（访客/客服）：检查是否包含HTML标签
                    if (/<[^>]+>/.test(content)) {
                        // 包含HTML标签，转义处理（不渲染）
                        messageContent = escapeHtml(content);
                        console.log('👤 用户消息已转义HTML');
                    } else {
                        // 普通文本内容，保持原样
                        messageContent = content;
                    }
                }
            }
            
            // ✅ 访客消息昵称右对齐
            if (type === 'visitor') {
                messageEl.innerHTML = `
                    <div class="message-avatar-wrapper">
                        <div class="message-avatar">${avatarIcon}</div>
                        ${badge}
                    </div>
                    <div class="message-content">
                        <div class="message-name" style="text-align: right;">${displayName}</div>
                        <div class="message-bubble">${messageContent}</div>
                        <div class="message-time">${time}</div>
                    </div>
                `;
            } else {
                messageEl.innerHTML = `
                    <div class="message-avatar-wrapper">
                        <div class="message-avatar">${avatarIcon}</div>
                        ${badge}
                    </div>
                    <div class="message-content">
                        <div class="message-name">${displayName}</div>
                        <div class="message-bubble">${messageContent}</div>
                        <div class="message-time">${time}</div>
                    </div>
                `;
            }

            messagesContainer.appendChild(messageEl);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }

        // 添加系统消息
        function addSystemMessage(content, type = 'info') {
            const messagesContainer = document.getElementById('chatMessages');
            const messageEl = document.createElement('div');
            messageEl.className = 'system-message';
            
            // 根据类型添加不同样式
            if (type === 'error') {
                messageEl.style.background = '#fee2e2';
                messageEl.style.color = '#991b1b';
                messageEl.style.border = '1px solid #fecaca';
            }
            
            messageEl.textContent = content;
            
            // 包装在容器中以居中显示
            const wrapper = document.createElement('div');
            wrapper.style.textAlign = 'center';
            wrapper.appendChild(messageEl);
            
            messagesContainer.appendChild(wrapper);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }

        // 添加被拦截的消息（带红色感叹号）
        function addBlockedMessage(content, timestamp) {
            const messagesContainer = document.getElementById('chatMessages');
            const messageEl = document.createElement('div');
            messageEl.className = 'message visitor blocked';
            
            const time = formatTime(timestamp || new Date());
            
            messageEl.innerHTML = `
                <div class="message-avatar">❌</div>
                <div class="message-content">
                    <div class="message-header">
                        <span class="message-nickname">您</span>
                        <span class="message-badge" style="background: #fee2e2; color: #991b1b;">被拦截</span>
                        <span class="message-time">${time}</span>
                    </div>
                    <div class="message-bubble" style="background: #fee2e2; border: 1px solid #fecaca; color: #991b1b;">
                        <span style="font-size: 20px; margin-right: 8px;">⚠️</span>
                        ${content}
                    </div>
                </div>
            `;
            
            messagesContainer.appendChild(messageEl);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }

        // 结束会话
        function endChat() {
            modal.confirm('确定要结束会话吗？', () => {
                if (socket && socket.connected) {
                    socket.disconnect();
                }
                modal.success('感谢您的使用，再见！');
                // 可以跳转到满意度评价页面
                // window.location.href = '/feedback';
            });
        }

        // 加载聊天历史
        // 聊天记录分页变量
        let chatOffset = 0;
        let chatHasMore = false;
        let isLoadingHistory = false;
        
        function loadChatHistory(isLoadMore = false) {
            if (isLoadingHistory) return;
            isLoadingHistory = true;
            
            const chatMessages = document.getElementById('chatMessages');
            const oldScrollHeight = chatMessages.scrollHeight;
            
            // 添加超时控制，避免阻塞太久
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 3000); // 3秒超时
            
            fetch(`/api/visitor/history?visitor_id=${visitorId}&business_id=1&limit=50&offset=${chatOffset}`, {
                signal: controller.signal
            })
                .then(response => response.json())
                .then(result => {
                    clearTimeout(timeoutId);
                    if (result.code === 0 && result.data && result.data.messages) {
                        const messages = result.data.messages;
                        chatHasMore = result.data.has_more || false;
                        
                        if (messages.length > 0) {
                            if (isLoadMore) {
                                // 加载更多时，在顶部插入
                                const fragment = document.createDocumentFragment();
                                messages.forEach(msg => {
                                    const msgEl = createMessageElement(msg);
                                    fragment.appendChild(msgEl);
                                });
                                chatMessages.insertBefore(fragment, chatMessages.firstChild);
                                
                                // ✅ 保持滚动位置
                                const newScrollHeight = chatMessages.scrollHeight;
                                chatMessages.scrollTop = newScrollHeight - oldScrollHeight;
                            } else {
                                // 初次加载
                                if (!isLoadMore) {
                                    addSystemMessage(`找到 ${messages.length} 条历史消息`);
                                }
                                messages.forEach(msg => {
                                    renderHistoryMessage(msg);
                                });
                                // 滚动到底部
                                chatMessages.scrollTop = chatMessages.scrollHeight;
                            }
                            
                            chatOffset += messages.length;
                        }
                    }
                    isLoadingHistory = false;
                })
                .catch(error => {
                    clearTimeout(timeoutId);
                    if (error.name === 'AbortError') {
                        console.log('历史消息加载超时，已跳过');
                    } else {
                        console.error('加载历史消息失败:', error);
                    }
                    isLoadingHistory = false;
                });
        }
        
        // 创建消息元素（不直接添加到DOM）
        function createMessageElement(msg) {
            // ✅ 优先根据service_id判断：null=机器人，>0=客服，否则根据direction判断
            let msgType;
            if (msg.service_id === null || msg.service_id === 0) {
                msgType = 'robot';  // ✅ 兼容null和0（旧数据）
            } else if (msg.direction === 'to_visitor') {
                msgType = 'service';
            } else {
                msgType = 'visitor';
            }
            
            let nickname, avatar;
            if (msgType === 'robot') {
                nickname = '智能助手';
                avatar = '🤖';
            } else if (msgType === 'service') {
                nickname = '客服';
                avatar = '👨‍💼';
            } else {
                nickname = visitorInfo.visitorName;
                avatar = '👤';
            }
            
            const timestamp = msg.created_at || msg.timestamp;
            
            // 创建消息元素
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${msgType}-message`;
            
            const time = new Date(timestamp);
            const hours = String(time.getHours()).padStart(2, '0');
            const minutes = String(time.getMinutes()).padStart(2, '0');
            const timeStr = `${hours}:${minutes}`;
            
            messageDiv.innerHTML = `
                <div class="message-avatar-wrapper">
                    <div class="message-avatar">${avatar}</div>
                    ${msgType === 'robot' ? '<span class="message-badge robot-badge">🤖</span>' : ''}
                    ${msgType === 'service' ? '<span class="message-badge service-badge">客服</span>' : ''}
                </div>
                <div class="message-content">
                    <div class="message-header">
                        <span class="message-name">${nickname}</span>
                        <span class="message-time">${timeStr}</span>
                    </div>
                    <div class="message-bubble">${msg.content}</div>
                </div>
            `;
            
            return messageDiv;
        }
        
        // 渲染历史消息（helper函数）
        function renderHistoryMessage(msg) {
            // ✅ 优先根据service_id判断：null=机器人，>0=客服，否则根据direction判断
            let msgType;
            if (msg.service_id === null || msg.service_id === 0) {
                msgType = 'robot';  // ✅ 兼容null和0（旧数据）
            } else if (msg.direction === 'to_visitor') {
                msgType = 'service';
            } else {
                msgType = 'visitor';
            }
            
            let nickname, avatar;
            if (msgType === 'robot') {
                nickname = '智能助手';
                avatar = '🤖';
            } else if (msgType === 'service') {
                nickname = '客服';
                avatar = '👨‍💼';
            } else {
                nickname = visitorInfo.visitorName;
                avatar = '👤';
            }
            
            const timestamp = msg.created_at || msg.timestamp;
            
            if (msg.msg_type === 2 || msg.msg_type === 'file') {
                addFileMessage(msg.content, msgType, timestamp);
            } else {
                addMessage(msgType, nickname, msg.content, avatar, timestamp);
            }
        }
        
        // 监听聊天容器滚动，到顶部时加载更多
        document.getElementById('chatMessages').addEventListener('scroll', function() {
            if (this.scrollTop === 0 && chatHasMore && !isLoadingHistory) {
                loadChatHistory(true);
            }
        });
        
        // 文件上传
        // 图片上传函数（访客只能上传图片）
        function uploadImage(file) {
            // 验证是否为图片
            if (!file.type.startsWith('image/')) {
                showModal('错误', '只能上传图片文件！', '⚠️', 'error');
                return;
            }
            
            // 图片大小限制（5MB）
            const maxSize = 5 * 1024 * 1024;
            if (file.size > maxSize) {
                showModal('文件过大', '图片大小不能超过5MB', '⚠️', 'error');
                return;
            }
            
            // 显示上传进度
            const progressEl = document.getElementById('uploadProgress');
            const fileNameEl = document.getElementById('uploadFileName');
            const fileSizeEl = document.getElementById('uploadFileSize');
            const progressBar = document.getElementById('uploadProgressBar');
            const percentEl = document.getElementById('uploadPercent');
            
            fileNameEl.textContent = file.name;
            fileSizeEl.textContent = formatFileSize(file.size);
            progressEl.style.display = 'block';
            progressBar.style.width = '0%';
            percentEl.textContent = '0%';
            
            // 创建FormData
            const formData = new FormData();
            formData.append('file', file);
            formData.append('business_id', 1);
            
            // 使用XMLHttpRequest上传（支持进度）
            const xhr = new XMLHttpRequest();
            
            // 上传进度
            xhr.upload.addEventListener('progress', function(e) {
                if (e.lengthComputable) {
                    const percent = Math.round((e.loaded / e.total) * 100);
                    progressBar.style.width = percent + '%';
                    percentEl.textContent = percent + '%';
                }
            });
            
            // 上传完成
            xhr.addEventListener('load', function() {
                progressEl.style.display = 'none';
                
                if (xhr.status === 200) {
                    const response = JSON.parse(xhr.responseText);
                    if (response.code === 0) {
                        // 发送图片消息
                        sendImageMessage(response.data);
                    } else {
                        showModal('上传失败', response.msg || '上传失败，请重试', '❌', 'error');
                    }
                } else {
                    showModal('上传失败', '服务器响应错误，请重试', '❌', 'error');
                }
            });
            
            // 上传错误
            xhr.addEventListener('error', function() {
                progressEl.style.display = 'none';
                showModal('上传失败', '网络错误，请检查连接后重试', '❌', 'error');
            });
            
            // 发送请求（使用图片上传接口）
            xhr.open('POST', '/api/upload/image', true);
            
            // ✅ 添加 CSRF Token 到请求头
            if (window.CSRF && window.CSRF.getToken) {
                window.CSRF.getToken().then(token => {
                    if (token) {
                        xhr.setRequestHeader('X-CSRFToken', token);
                    }
                    xhr.send(formData);
                }).catch(() => {
                    // 如果获取 token 失败，仍然尝试发送（访客可能还没有token）
                    xhr.send(formData);
                });
            } else {
                xhr.send(formData);
            }
        }
        
        // 发送图片消息
        function sendImageMessage(fileData) {
            const imageMessage = {
                type: 'image',
                url: fileData.url,
                name: fileData.name,
                size: fileData.size,
                mime_type: fileData.mime_type
            };
            
            // 在界面显示
            addFileMessage(JSON.stringify(imageMessage), 'visitor', new Date());
            
            // 通过WebSocket发送
            // 更新设备信息
            const currentDeviceInfo = getDeviceInfo();
            if (clientRealIP) {
                currentDeviceInfo.client_ip = clientRealIP;
            }
            
            socket.emit('send_message', {
                from_id: visitorId,
                from_type: 'visitor',
                from_name: visitorName,
                to_id: currentServiceId || 'all',
                to_type: 'service',
                content: JSON.stringify(imageMessage),  // ✅ 修复：使用imageMessage而不是fileMessage
                msg_type: 'file',
                timestamp: new Date().toISOString(),
                device_info: currentDeviceInfo,  // 附带设备信息
                business_id: 1
            });
        }
        
        // 添加文件消息
        function addFileMessage(content, type, timestamp) {
            try {
                const fileData = JSON.parse(content);
                const messagesContainer = document.getElementById('chatMessages');
                const messageEl = document.createElement('div');
                messageEl.className = 'message ' + type;
                
                const time = formatTime(timestamp);
                const avatar = type === 'visitor' ? '👤' : '👨‍💼';
                const nickname = type === 'visitor' ? '访客' : '客服';
                
                // 确定徽章
                let badge = '';
                if (type === 'service') {
                    badge = '<span class="message-badge service-badge">客服</span>';
                }
                
                // 判断是否为图片，如果是图片直接显示图片
                const isImage = fileData.mime_type && fileData.mime_type.startsWith('image/');
                
                if (isImage) {
                    // 图片消息：点击弹出预览窗口
                    messageEl.innerHTML = `
                        <div class="message-avatar-wrapper">
                            <div class="message-avatar">${avatar}</div>
                            ${badge}
                        </div>
                        <div class="message-content">
                            <div class="message-name">${nickname}</div>
                            <div class="message-bubble image-message" onclick="showImagePreview('${fileData.url}')" style="cursor: pointer; padding: 4px; background: transparent;">
                                <img src="${fileData.url}" alt="${escapeHtml(fileData.name)}" style="max-width: 200px; max-height: 200px; border-radius: 8px; display: block;">
                            </div>
                            <div class="message-time">${time}</div>
                        </div>
                    `;
                } else {
                    // 非图片文件：显示文件图标和信息
                    let fileIcon = '📄';
                    if (fileData.mime_type) {
                        if (fileData.mime_type.includes('pdf')) fileIcon = '📕';
                        else if (fileData.mime_type.includes('word')) fileIcon = '📘';
                        else if (fileData.mime_type.includes('excel') || fileData.mime_type.includes('sheet')) fileIcon = '📗';
                        else if (fileData.mime_type.includes('zip') || fileData.mime_type.includes('rar')) fileIcon = '📦';
                    }
                    
                    messageEl.innerHTML = `
                        <div class="message-avatar-wrapper">
                            <div class="message-avatar">${avatar}</div>
                            ${badge}
                        </div>
                        <div class="message-content">
                            <div class="message-name">${nickname}</div>
                            <div class="message-bubble file-message" style="cursor: pointer;" onclick="window.open('${fileData.url}', '_blank')">
                                <div style="display: flex; align-items: center; gap: 12px;">
                                    <div style="font-size: 32px;">${fileIcon}</div>
                                    <div style="flex: 1;">
                                        <div style="font-weight: 600; margin-bottom: 4px;">${escapeHtml(fileData.name)}</div>
                                        <div style="font-size: 12px; color: #9ca3af;">${formatFileSize(fileData.size)}</div>
                                    </div>
                                    <div style="font-size: 20px;">📥</div>
                                </div>
                            </div>
                            <div class="message-time">${time}</div>
                        </div>
                    `;
                }
                
                messagesContainer.appendChild(messageEl);
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            } catch(e) {
                // 如果解析失败，按普通消息显示
                const nickname = type === 'visitor' ? '访客' : '客服';
                const avatar = type === 'visitor' ? '👤' : '👨‍💼';
                addMessage(type, nickname, content, avatar, timestamp);
            }
        }
        
        // 格式化文件大小
        function formatFileSize(bytes) {
            if (bytes < 1024) return bytes + ' B';
            if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
            return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
        }
        
        // 格式化时间
        function formatTime(date) {
            if (!date) return '';
            const d = new Date(date);
            const year = d.getFullYear();
            const month = String(d.getMonth() + 1).padStart(2, '0');
            const day = String(d.getDate()).padStart(2, '0');
            const hours = String(d.getHours()).padStart(2, '0');
            const minutes = String(d.getMinutes()).padStart(2, '0');
            return `${year}-${month}-${day} ${hours}:${minutes}`;
        }

        // HTML转义（防止XSS）
        function escapeHtml(text) {
            const map = {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#039;'
            };
            return text.replace(/[&<>"']/g, function(m) { return map[m]; });
        }
        
        // ========== 新消息提示功能 ==========
        
        let originalTitle = document.title;
        let titleFlashInterval = null;
        let isPageVisible = true;
        let unreadCount = 0;
        let audioContext = null; // 全局AudioContext，避免重复创建
        let audioContextInitialized = false;
        
        // 监听页面可见性
        document.addEventListener('visibilitychange', async () => {
            isPageVisible = !document.hidden;
            if (isPageVisible) {
                // 页面变为可见时，停止闪烁并恢复标题
                stopTitleFlash();
                unreadCount = 0;
                
                // ✅ 恢复AudioContext（确保提示音可以播放）
                if (audioContext && audioContext.state === 'suspended') {
                    try {
                        console.log('🔄 页面可见，恢复AudioContext...');
                        await audioContext.resume();
                        console.log('✅ AudioContext已恢复:', audioContext.state);
                    } catch (error) {
                        console.error('❌ AudioContext恢复失败:', error);
                    }
                }
            }
        });
        
        // 初始化AudioContext（在用户首次交互时调用）
        async function initAudioContext() {
            if (!audioContextInitialized) {
                try {
                    audioContext = new (window.AudioContext || window.webkitAudioContext)();
                    audioContextInitialized = true;
                    console.log('✅ AudioContext已初始化，状态:', audioContext.state);
                    
                    // ✅ 立即恢复AudioContext（确保状态为running）
                    if (audioContext.state === 'suspended') {
                        await audioContext.resume();
                        console.log('✅ AudioContext已恢复到running状态:', audioContext.state);
                    }
                } catch (error) {
                    console.error('❌ AudioContext初始化失败:', error);
                }
            }
        }
        
        // 开始标题闪烁
        function startTitleFlash(message) {
            unreadCount++;
            
            // 如果页面可见，不需要闪烁
            if (isPageVisible) return;
            
            // 如果已经在闪烁，只更新未读数
            if (titleFlashInterval) {
                return;
            }
            
            let showNew = true;
            titleFlashInterval = setInterval(() => {
                if (showNew) {
                    document.title = `(${unreadCount}条新消息) ${originalTitle}`;
                } else {
                    document.title = originalTitle;
                }
                showNew = !showNew;
            }, 1000);
        }
        
        // 停止标题闪烁
        function stopTitleFlash() {
            if (titleFlashInterval) {
                clearInterval(titleFlashInterval);
                titleFlashInterval = null;
            }
            document.title = originalTitle;
        }
        
        // 播放提示音（使用预创建的AudioContext）
        async function playNotificationSound() {
            // ⚠️ 不要在WebSocket回调中尝试初始化，必须在真实用户交互中初始化
            if (!audioContext || !audioContextInitialized) {
                // 只在第一次时显示提示（避免刷屏）
                if (!window.audioInitHintShown) {
                    console.log('💡 提示音需要用户交互后才能播放，请点击页面任意位置');
                    window.audioInitHintShown = true;
                }
                return;
            }
            
            try {
                // ✅ 确保AudioContext处于运行状态（异步等待恢复完成）
                if (audioContext.state === 'suspended') {
                    console.log('🔄 AudioContext已暂停，正在恢复...');
                    await audioContext.resume();
                    console.log('✅ AudioContext已恢复:', audioContext.state);
                }
                
                // 再次检查状态，确保已恢复
                if (audioContext.state !== 'running') {
                    console.warn('⚠️ AudioContext状态异常:', audioContext.state);
                    return;
                }
                
                const oscillator = audioContext.createOscillator();
                const gainNode = audioContext.createGain();
                
                oscillator.connect(gainNode);
                gainNode.connect(audioContext.destination);
                
                // 设置音调
                oscillator.frequency.value = 800; // 800Hz
                oscillator.type = 'sine';
                
                // 设置音量（淡入淡出效果）- 增强音量和时长
                gainNode.gain.setValueAtTime(0, audioContext.currentTime);
                gainNode.gain.linearRampToValueAtTime(0.6, audioContext.currentTime + 0.01);
                gainNode.gain.linearRampToValueAtTime(0, audioContext.currentTime + 0.5);
                
                // 播放
                oscillator.start(audioContext.currentTime);
                oscillator.stop(audioContext.currentTime + 0.5);
                
                console.log('🔔 提示音播放成功');
                
                // 第二个音（稍高音调）
                setTimeout(() => {
                    const oscillator2 = audioContext.createOscillator();
                    const gainNode2 = audioContext.createGain();
                    
                    oscillator2.connect(gainNode2);
                    gainNode2.connect(audioContext.destination);
                    
                    oscillator2.frequency.value = 1000; // 1000Hz
                    oscillator2.type = 'sine';
                    
                    gainNode2.gain.setValueAtTime(0, audioContext.currentTime);
                    gainNode2.gain.linearRampToValueAtTime(0.6, audioContext.currentTime + 0.01);
                    gainNode2.gain.linearRampToValueAtTime(0, audioContext.currentTime + 0.5);
                    
                    oscillator2.start(audioContext.currentTime);
                    oscillator2.stop(audioContext.currentTime + 0.5);
                }, 150);
            } catch (error) {
                console.error('❌ 播放提示音失败:', error);
            }
        }
        
        // 显示桌面通知（需要用户授权）
        function showDesktopNotification(title, body) {
            if (!("Notification" in window)) {
                console.log('浏览器不支持桌面通知');
                return;
            }
            
            if (Notification.permission === "granted") {
                new Notification(title, {
                    body: body,
                    icon: '/static/favicon.svg',
                    badge: '/static/favicon.svg',
                    tag: 'new-message',
                    requireInteraction: false
                });
            } else if (Notification.permission !== "denied") {
                Notification.requestPermission().then(permission => {
                    if (permission === "granted") {
                        new Notification(title, {
                            body: body,
                            icon: '/static/favicon.svg'
                        });
                    }
                });
            }
        }
        
        // 页面加载时请求桌面通知权限
        if ("Notification" in window && Notification.permission === "default") {
            Notification.requestPermission();
        }
        
        // ========== 模态弹窗功能 ==========
        
        let modalConfirmCallback = null;
        
        /**
         * 显示模态弹窗
         * @param {string} title - 标题
         * @param {string} message - 消息内容
         * @param {string} icon - 图标（Emoji）
         * @param {string} type - 类型：'info', 'success', 'error', 'warning', 'confirm'
         * @param {function} onConfirm - 确认回调函数（可选）
         */
        function showModal(title, message, icon = 'ℹ️', type = 'info', onConfirm = null) {
            const modal = document.getElementById('modalOverlay');
            const modalTitle = document.getElementById('modalTitle');
            const modalMessage = document.getElementById('modalMessage');
            const modalIcon = document.getElementById('modalIcon');
            const confirmBtn = document.getElementById('modalConfirmBtn');
            const cancelBtn = document.getElementById('modalCancelBtn');
            
            // 设置内容
            modalTitle.textContent = title;
            modalMessage.textContent = message;
            modalIcon.textContent = icon;
            
            // 设置回调
            modalConfirmCallback = onConfirm;
            
            // 根据类型显示不同按钮
            if (type === 'confirm') {
                confirmBtn.textContent = '确定';
                cancelBtn.style.display = 'block';
                cancelBtn.textContent = '取消';
            } else {
                confirmBtn.textContent = '好的';
                cancelBtn.style.display = 'none';
            }
            
            // 显示弹窗
            modal.style.display = 'flex';
        }
        
        /**
         * 关闭模态弹窗
         */
        function closeModal() {
            const modal = document.getElementById('modalOverlay');
            modal.style.display = 'none';
            modalConfirmCallback = null;
        }
        
        /**
         * 确认按钮点击
         */
        function modalConfirmAction() {
            if (modalConfirmCallback && typeof modalConfirmCallback === 'function') {
                modalConfirmCallback();
            }
            closeModal();
        }
        
        // 点击遮罩层关闭弹窗
        document.getElementById('modalOverlay').addEventListener('click', function(e) {
            if (e.target === this) {
                closeModal();
            }
        });
        
        // ESC键关闭弹窗
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                const modal = document.getElementById('modalOverlay');
                if (modal.style.display === 'flex') {
                    closeModal();
                }
            }
        });
        
        // ========== 问候语和常见问题功能 ==========
        
        // 加载问候语并自动发送
        async function loadGreetingMessage() {
            try {
                // 检查本次会话是否已经发送过问候语（使用sessionStorage，关闭标签页后重置）
                const greetingSent = sessionStorage.getItem(`greeting_sent_${visitorId}`);
                if (greetingSent) {
                    console.log('本次会话问候语已发送，跳过');
                    return;
                }
                
                const response = await fetch('/api/visitor/greeting?business_id=1');
                const result = await response.json();
                
                console.log('问候语API响应:', result);
                
                if (result.code === 0 && result.data.greeting) {
                    // 延迟1秒后发送问候语，让用户感觉更自然
                    setTimeout(() => {
                        addMessage('robot', '智能助手', result.data.greeting, '🤖', new Date());
                        // 标记已发送（使用sessionStorage，关闭标签页后重置）
                        sessionStorage.setItem(`greeting_sent_${visitorId}`, 'true');
                        console.log('✅ 问候语已发送');
                    }, 1000);
                } else {
                    console.error('❌ 问候语数据为空');
                }
            } catch (error) {
                console.error('❌ 加载问候语失败:', error);
            }
        }
        
        // 加载常见问题气泡
        async function loadFAQBubbles() {
            try {
                const response = await fetch('/api/visitor/faq?business_id=1&limit=6');
                const result = await response.json();
                
                if (result.code === 0 && result.data.faqs && result.data.faqs.length > 0) {
                    const faqBubbles = document.getElementById('faqBubbles');
                    
                    // 确保初始状态（移除show类）
                    faqBubbles.classList.remove('show');
                    faqBubbles.innerHTML = '';
                    
                    result.data.faqs.forEach(faq => {
                        const bubble = document.createElement('div');
                        bubble.className = 'faq-bubble';
                        // 显示问题文本（截取前15个字符，避免太长）
                        const displayText = faq.question.length > 15 
                            ? faq.question.substring(0, 15) + '...' 
                            : faq.question;
                        bubble.textContent = displayText;
                        bubble.title = faq.question;  // 鼠标悬停显示完整问题
                        bubble.onclick = () => handleFAQClick(faq);
                        faqBubbles.appendChild(bubble);
                    });
                    
                    // 强制重绘，确保CSS初始状态已应用
                    faqBubbles.offsetHeight;
                    
                    // 延迟显示气泡（给页面加载留出时间，避免卡顿）
                    setTimeout(() => {
                        faqBubbles.classList.add('show');
                    }, 800);
                }
            } catch (error) {
                console.error('加载常见问题失败:', error);
            }
        }
        
        // 处理常见问题点击
        function handleFAQClick(faq) {
            console.log('点击常见问题:', faq.question);
            
            if (!socket || !socket.connected) {
                modal.error('未连接到服务器，请稍后再试');
                return;
            }
            
            // 访客发送问题（使用问题文本）
            const questionText = faq.question;
            addMessage('visitor', visitorInfo.visitorName, questionText, visitorInfo.avatar, new Date());
            
            // 更新设备信息
            const currentDeviceInfo = getDeviceInfo();
            if (clientRealIP) {
                currentDeviceInfo.client_ip = clientRealIP;
            }
            
            // 发送到服务器（包含FAQ答案和特殊标记）
            socket.emit('send_message', {
                from_id: visitorInfo.visitorId,
                from_type: 'visitor',
                from_name: visitorInfo.visitorName,
                to_id: currentServiceId || 'all',
                to_type: 'service',
                content: questionText,
                msg_type: 'text',
                timestamp: new Date().toISOString(),
                device_info: currentDeviceInfo,
                business_id: 1,
                faq_answer: faq.answer,  // ✅ 传递FAQ答案
                is_faq_click: true  // ✅ 标记为FAQ点击（不要关键词匹配）
            });
            
            // ✅ 不在前端显示机器人回复，等待后端回复
            // 这样避免重复显示
            console.log('✅ 已发送FAQ问题，等待后端机器人回复...');
        }

        // ========== 评价功能 ==========
        let currentRating = 0;
        let commentQueueId = null;
        let commentServiceId = null;
        let selectedTags = [];

        // 预设标签
        const commentTagOptions = {
            positive: ['态度好', '响应快', '专业', '耐心', '热情', '解决问题', '服务周到'],
            negative: ['态度一般', '响应慢', '不够专业', '不耐烦', '未解决问题']
        };

        // 注意：socket.on('request_comment') 监听已移至 initSocket() 函数内部

        // 加载评价标签
        function loadCommentTags() {
            const tagsContainer = document.getElementById('commentTags');
            tagsContainer.innerHTML = '';
            
            // 根据评分显示不同的标签
            let tags = [];
            if (currentRating >= 4) {
                tags = commentTagOptions.positive;
            } else if (currentRating > 0 && currentRating < 4) {
                tags = [...commentTagOptions.positive, ...commentTagOptions.negative];
            } else {
                tags = [...commentTagOptions.positive, ...commentTagOptions.negative];
            }
            
            tags.forEach(tag => {
                const tagElement = document.createElement('span');
                tagElement.className = 'comment-tag';
                tagElement.textContent = tag;
                tagElement.onclick = function() {
                    toggleTag(tag, tagElement);
                };
                
                // 如果已选中，添加样式
                if (selectedTags.includes(tag)) {
                    tagElement.classList.add('selected');
                }
                
                tagsContainer.appendChild(tagElement);
            });
        }

        // 切换标签选中状态
        function toggleTag(tag, element) {
            if (selectedTags.includes(tag)) {
                selectedTags = selectedTags.filter(t => t !== tag);
                element.classList.remove('selected');
            } else {
                selectedTags.push(tag);
                element.classList.add('selected');
            }
        }

        // 星级评分点击事件
        document.querySelectorAll('#starRating .star').forEach(star => {
            star.addEventListener('click', function() {
                currentRating = parseInt(this.getAttribute('data-value'));
                updateStarRating(currentRating);
            });
            
            star.addEventListener('mouseenter', function() {
                const value = parseInt(this.getAttribute('data-value'));
                updateStarRatingHover(value);
            });
        });

        document.getElementById('starRating').addEventListener('mouseleave', function() {
            updateStarRating(currentRating);
        });

        function updateStarRating(rating) {
            const stars = document.querySelectorAll('#starRating .star');
            stars.forEach((star, index) => {
                if (index < rating) {
                    star.classList.add('active');
                    star.textContent = '★';
                } else {
                    star.classList.remove('active');
                    star.textContent = '☆';
                }
            });
            
            const ratingTexts = ['', '非常不满意', '不满意', '一般', '满意', '非常满意'];
            document.getElementById('ratingText').textContent = ratingTexts[rating] || '点击星星进行评分';
            
            // 重新加载标签（根据评分显示不同标签）
            loadCommentTags();
        }

        function updateStarRatingHover(rating) {
            const stars = document.querySelectorAll('#starRating .star');
            stars.forEach((star, index) => {
                if (index < rating) {
                    star.textContent = '★';
                } else {
                    star.textContent = '☆';
                }
            });
        }

        // 提交评价
        async function submitComment() {
            if (currentRating === 0) {
                alert('请选择评分');
                return;
            }
            
            const content = document.getElementById('commentContent').value;
            
            // 构建评价数据（包含标签）
            const commentData = {
                text: content,
                tags: selectedTags
            };
            
            try {
                const response = await fetch('/api/comment/submit', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        queue_id: commentQueueId,
                        visitor_id: visitorInfo.visitorId,
                        service_id: commentServiceId,
                        level: currentRating,
                        content: JSON.stringify(commentData)
                    })
                });
                
                const result = await response.json();
                
                if (result.code === 0) {
                    closeCommentModal();
                    modal.success('感谢您的评价！');
                } else {
                    alert(result.msg || '提交失败');
                }
            } catch (error) {
                console.error('提交评价失败:', error);
                alert('提交失败，请稍后重试');
            }
        }

        // 跳过评价
        function skipComment() {
            closeCommentModal();
        }

        // 关闭评价弹窗
        function closeCommentModal() {
            document.getElementById('commentModal').style.display = 'none';
            currentRating = 0;
            commentQueueId = null;
            commentServiceId = null;
            selectedTags = [];
        }

        // 暴露函数到全局作用域
        window.submitComment = submitComment;
        window.skipComment = skipComment;
        window.closeCommentModal = closeCommentModal;
        
        
        // ========== 客服评价功能 ==========
        let currentServiceRating = 0;
        let serviceRatingEligible = true;
        
        // 显示客服评价弹窗
        async function showServiceRatingModal() {
            console.log('🌟 准备打开评价弹窗');
            console.log('  - visitorId:', window.visitorId);
            console.log('  - currentServiceId:', window.currentServiceId);
            console.log('  - businessId:', window.businessId);
            
            // 检查访客ID
            if (!window.visitorId) {
                modal.error('访客信息未初始化，请刷新页面重试');
                return;
            }
            
            // 检查是否已分配客服
            if (!window.currentServiceId) {
                modal.info('暂未分配客服，无法评价<br>请先发送消息与客服对话后再评价');
                return;
            }
            
            // 检查评价资格（24小时限制）
            try {
                console.log('🔍 检查评价资格...');
                const response = await fetch('/api/rating/check-eligible', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        visitor_id: window.visitorId,
                        service_id: window.currentServiceId
                    })
                });
                
                const result = await response.json();
                console.log('📋 评价资格检查结果:', result);
                
                if (result.code === 0 && result.data.eligible === false) {
                    modal.warning(result.data.reason);
                    return;
                }
                
                // 显示评价弹窗
                console.log('✅ 符合评价条件，显示评价弹窗');
                const ratingModal = document.getElementById('serviceRatingModal');
                if (ratingModal) {
                    ratingModal.style.display = 'flex';
                    currentServiceRating = 0;
                    updateServiceStars(0);
                    const commentBox = document.getElementById('serviceRatingComment');
                    if (commentBox) {
                        commentBox.value = '';
                    }
                } else {
                    console.error('❌ 评价弹窗元素不存在');
                    modal.error('评价功能初始化失败，请刷新页面重试');
                }
                
            } catch (error) {
                console.error('❌ 检查评价资格失败:', error);
                modal.error('检查评价资格失败，请稍后重试');
            }
        }
        
        // 更新星级显示
        function updateServiceStars(rating) {
            currentServiceRating = rating;
            for (let i = 1; i <= 5; i++) {
                const star = document.getElementById(`serviceStar${i}`);
                if (star) {
                    star.textContent = i <= rating ? '★' : '☆';
                    star.style.color = i <= rating ? '#fbbf24' : '#d1d5db';
                }
            }
        }
        
        // 提交客服评价
        async function submitServiceRating() {
            console.log('📤 准备提交评价...');
            
            if (currentServiceRating === 0) {
                modal.warning('请先选择评分');
                return;
            }
            
            const comment = document.getElementById('serviceRatingComment').value.trim();
            
            const ratingData = {
                visitor_id: window.visitorId,
                service_id: window.currentServiceId,
                business_id: window.businessId || 1,
                rating: currentServiceRating,
                comment: comment,
                tags: []
            };
            
            console.log('📝 评价数据:', ratingData);
            
            try {
                const response = await fetch('/api/rating/submit', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(ratingData)
                });
                
                const result = await response.json();
                console.log('📋 提交结果:', result);
                
                if (result.code === 0) {
                    closeServiceRatingModal();
                    modal.success('评价提交成功，感谢您的反馈！');
                } else {
                    modal.error(result.msg || '提交失败');
                }
            } catch (error) {
                console.error('❌ 提交评价失败:', error);
                modal.error('提交失败，请稍后重试');
            }
        }
        
        // 关闭客服评价弹窗
        function closeServiceRatingModal() {
            const modal = document.getElementById('serviceRatingModal');
            if (modal) {
                modal.style.display = 'none';
            }
            currentServiceRating = 0;
            updateServiceStars(0);
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
            document.addEventListener('keydown', handleImagePreviewEscape);
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
            document.removeEventListener('keydown', handleImagePreviewEscape);
        }
        
        /**
         * 处理ESC键按下事件
         */
        function handleImagePreviewEscape(e) {
            if (e.key === 'Escape') {
                closeImagePreview();
            }
        }
        
        // 暴露图片预览函数到全局
        window.showImagePreview = showImagePreview;
        window.closeImagePreview = closeImagePreview;
        
        // 暴露评价函数到全局
        window.showServiceRatingModal = showServiceRatingModal;
        window.updateServiceStars = updateServiceStars;
        window.submitServiceRating = submitServiceRating;
        window.closeServiceRatingModal = closeServiceRatingModal;
    