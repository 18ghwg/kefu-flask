/**
 * 全局Socket.IO连接和消息通知
 * 用于所有后台页面的实时通信
 */

(function() {
    'use strict';

    // ========== 配置和状态 ==========
    const CONFIG = {
        socketUrl: window.location.origin,
        reconnectDelay: 3000
    };

    let socket = null;
    let currentUser = null;
    let titleFlashInterval = null;
    let originalTitle = document.title;
    let unreadCount = 0;
    let isInChatPage = false;  // 是否在客服工作台页面

    // ========== 检测当前页面 ==========
    function detectCurrentPage() {
        const path = window.location.pathname;
        // 检测是否在客服工作台页面
        isInChatPage = path.includes('/service/chat');
        console.log('[全局Socket] 当前页面:', path, '是否客服工作台:', isInChatPage);
        return isInChatPage;
    }

    // ========== 获取当前用户信息 ==========
    async function getCurrentUser() {
        try {
            const response = await fetch('/api/auth/current-user');
            if (response.ok) {
                const data = await response.json();
                if (data.code === 0) {
                    currentUser = data.data;
                    console.log('[全局Socket] 当前用户:', currentUser);
                    return currentUser;
                }
            }
        } catch (error) {
            console.error('[全局Socket] 获取用户信息失败:', error);
        }
        return null;
    }

    // ========== Socket.IO连接初始化 ==========
    function initSocket() {
        if (socket && socket.connected) {
            console.log('[全局Socket] Socket已连接，无需重复初始化');
            return;
        }

        console.log('[全局Socket] 初始化Socket.IO连接...');
        
        socket = io(CONFIG.socketUrl, {
            transports: ['websocket', 'polling'],
            reconnection: true,
            reconnectionDelay: CONFIG.reconnectDelay,
            reconnectionAttempts: 5
        });

        // 连接成功
        socket.on('connect', () => {
            console.log('[全局Socket] ✅ Socket连接成功');
            if (currentUser) {
                joinAsService();
            }
        });

        // 连接失败
        socket.on('connect_error', (error) => {
            console.error('[全局Socket] ❌ Socket连接失败:', error);
        });

        // 断开连接
        socket.on('disconnect', (reason) => {
            console.log('[全局Socket] ⚠️ Socket断开连接:', reason);
        });

        // 重新连接
        socket.on('reconnect', (attemptNumber) => {
            console.log('[全局Socket] 🔄 Socket重新连接成功 (尝试次数:', attemptNumber, ')');
            if (currentUser) {
                joinAsService();
            }
        });

        // 监听新消息
        socket.on('receive_message', handleNewMessage);
        
        // 监听新访客
        socket.on('new_visitor', handleNewVisitor);
    }

    // ========== 客服加入在线 ==========
    function joinAsService() {
        if (!currentUser) {
            console.warn('[全局Socket] 无用户信息，无法加入在线');
            return;
        }

        // ✅ 只有真正的客服账号（有service_id）才加入在线
        // 管理员账号(super_manager, manager)没有service_id，不需要发送service_join
        if (!currentUser.service_id) {
            console.log('[全局Socket] ⏸️ 当前用户不是客服账号(无service_id)，跳过service_join');
            return;
        }

        // ⚡ 管理员通过admin_join加入在线，而不是service_join
        if (currentUser.level === 'super_manager' || currentUser.level === 'manager') {
            console.log('[全局Socket] ✅ 管理员账号，调用admin_join');
            const adminData = {
                service_id: currentUser.service_id || currentUser.uid,
                service_name: currentUser.nick_name || currentUser.username || currentUser.name,
                business_id: currentUser.business_id || 1
            };
            socket.emit('admin_join', adminData);
            return;
        }

        const serviceData = {
            service_id: currentUser.service_id,  // ✅ 使用service_id
            service_name: currentUser.nick_name || currentUser.username || currentUser.name,
            business_id: currentUser.business_id || 1
        };

        console.log('[全局Socket] ✅ 客服加入在线:', serviceData);
        socket.emit('service_join', serviceData);

        // 加入客服房间
        const roomName = `service_${currentUser.service_id}`;
        socket.emit('join_room', { room: roomName });
    }

    // ========== 处理新消息 ==========
    function handleNewMessage(data) {
        console.log('[全局Socket] 收到新消息:', data);
        
        // 如果是访客发来的消息，进行通知
        if (data.from_type === 'visitor') {
            // ✅ 智能判断：检查当前客服是否应该收到通知
            const shouldNotify = checkShouldNotify(data);
            
            if (shouldNotify) {
                console.log('[全局Socket] 🎯 开始执行通知逻辑');
                unreadCount++;
                console.log('[全局Socket] 📊 未读数量+1:', unreadCount);
                
                // 标题闪动通知
                console.log('[全局Socket] 🏷️ 调用startTitleFlash');
                startTitleFlash(`(${unreadCount}条新消息) `);
                
                // ✅ 播放提示音（不再限制页面）
                console.log('[全局Socket] 🔊 调用playNotificationSound');
                playNotificationSound();
                
                // 显示桌面通知（如果用户授权）
                console.log('[全局Socket] 📬 调用showDesktopNotification');
                showDesktopNotification('新消息', `访客${data.from_name || ''}发来消息: ${data.content}`);
            } else {
                console.log('[全局Socket] 消息不相关，跳过通知');
            }
        }
    }
    
    // ========== 检查是否应该通知 ==========
    function checkShouldNotify(messageData) {
        if (!currentUser) return false;
        
        // 管理员总是收到通知
        if (currentUser.level === 'super_manager' || currentUser.level === 'manager') {
            console.log('[全局Socket] ✅ 管理员，应该通知');
            return true;
        }
        
        // 检查是否是分配给当前客服的消息
        if (messageData.service_id && messageData.service_id == currentUser.service_id) {
            console.log('[全局Socket] ✅ 分配给当前客服，应该通知');
            return true;
        }
        
        console.log('[全局Socket] ❌ 消息不相关');
        return false;
    }

    // ========== 处理新访客 ==========
    function handleNewVisitor(data) {
        console.log('[全局Socket] 新访客上线:', data);
        
        // 标题闪动通知
        startTitleFlash('(新访客) ');
        
        // 只在客服工作台页面播放声音
        if (isInChatPage) {
            playNotificationSound();
        }
        
        // 显示桌面通知
        showDesktopNotification('新访客', `访客 ${data.visitor_name || data.visitor_id} 上线了`);
    }

    // ========== 标题闪动通知 ==========
    function startTitleFlash(prefix) {
        // 如果已经在闪动，不重复启动
        if (titleFlashInterval) {
            return;
        }
        
        let isOriginal = true;
        titleFlashInterval = setInterval(() => {
            if (isOriginal) {
                document.title = prefix + originalTitle;
            } else {
                document.title = originalTitle;
            }
            isOriginal = !isOriginal;
        }, 1000);
    }

    // ========== 停止标题闪动 ==========
    function stopTitleFlash() {
        if (titleFlashInterval) {
            clearInterval(titleFlashInterval);
            titleFlashInterval = null;
        }
        document.title = originalTitle;
        unreadCount = 0;
    }

    // ========== 播放通知音 ==========
    let audioContext = null;
    let audioContextInitialized = false;

    function initAudioContext() {
        if (audioContextInitialized) return;
        
        try {
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
            audioContextInitialized = true;
            console.log('[全局Socket] AudioContext初始化成功');
        } catch (error) {
            console.error('[全局Socket] AudioContext初始化失败:', error);
        }
    }

    function playNotificationSound() {
        if (!audioContext || !audioContextInitialized) {
            console.log('[全局Socket] AudioContext未初始化，尝试初始化');
            initAudioContext();
        }

        if (!audioContext) {
            console.warn('[全局Socket] 无法播放声音：AudioContext不可用');
            return;
        }

        try {
            // 如果AudioContext被挂起，尝试恢复
            if (audioContext.state === 'suspended') {
                audioContext.resume().then(() => {
                    console.log('[全局Socket] AudioContext已恢复');
                    createAndPlayTone();
                });
            } else {
                createAndPlayTone();
            }
        } catch (error) {
            console.error('[全局Socket] 播放通知音失败:', error);
        }
    }

    function createAndPlayTone() {
        try {
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();

            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);

            oscillator.frequency.value = 800;
            oscillator.type = 'sine';

            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);

            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.5);
        } catch (error) {
            console.error('[全局Socket] 创建声音失败:', error);
        }
    }

    // ========== 桌面通知 ==========
    function showDesktopNotification(title, body) {
        // 检查浏览器是否支持通知
        if (!('Notification' in window)) {
            console.log('[全局Socket] 浏览器不支持桌面通知');
            return;
        }

        // 检查通知权限
        if (Notification.permission === 'granted') {
            createNotification(title, body);
        } else if (Notification.permission !== 'denied') {
            // 请求权限
            Notification.requestPermission().then(permission => {
                if (permission === 'granted') {
                    createNotification(title, body);
                }
            });
        }
    }

    function createNotification(title, body) {
        try {
            const notification = new Notification(title, {
                body: body,
                icon: '/static/favicon.svg',
                badge: '/static/favicon.svg',
                tag: 'new-message',
                requireInteraction: false
            });

            notification.onclick = () => {
                window.focus();
                notification.close();
                
                // 如果不在客服工作台，跳转到工作台
                if (!isInChatPage) {
                    window.location.href = '/service/chat';
                }
            };

            // 3秒后自动关闭
            setTimeout(() => notification.close(), 3000);
        } catch (error) {
            console.error('[全局Socket] 创建桌面通知失败:', error);
        }
    }

    // ========== 窗口焦点事件 ==========
    window.addEventListener('focus', () => {
        // 窗口获得焦点时停止标题闪动
        stopTitleFlash();
        
        // 初始化AudioContext（需要用户交互）
        if (!audioContextInitialized) {
            initAudioContext();
        }
    });

    window.addEventListener('blur', () => {
        // 窗口失去焦点时，不做特殊处理
    });

    // ========== 页面可见性变化 ==========
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden) {
            // 页面变为可见时停止标题闪动
            stopTitleFlash();
        }
    });

    // ========== 用户交互事件（初始化AudioContext） ==========
    ['click', 'touchstart', 'keydown'].forEach(eventType => {
        document.addEventListener(eventType, () => {
            if (!audioContextInitialized) {
                initAudioContext();
            }
        }, { once: true, passive: true });
    });

    // ========== 页面卸载时断开连接 ==========
    window.addEventListener('beforeunload', () => {
        if (socket && socket.connected) {
            socket.disconnect();
        }
    });

    // ========== 初始化 ==========
    async function init() {
        console.log('[全局Socket] 开始初始化...');
        
        // 检测当前页面
        const isChatPage = detectCurrentPage();
        
        // 如果是客服工作台页面，不建立全局Socket连接
        // 因为工作台页面有自己的Socket连接（功能更完整）
        if (isChatPage) {
            console.log('[全局Socket] 当前是客服工作台页面，不建立全局Socket连接');
            return;
        }
        
        // 获取用户信息
        await getCurrentUser();
        
        // 如果用户已登录，初始化Socket连接
        if (currentUser) {
            initSocket();
        } else {
            console.log('[全局Socket] 未登录，不建立Socket连接');
        }
    }

    // 页面加载完成后初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // ========== 未读消息统计 ==========
    async function fetchUnreadCount() {
        if (!currentUser || !currentUser.service_id) {
            return;
        }
        
        try {
            const response = await fetch('/api/service/unread_messages');
            if (response.ok) {
                const data = await response.json();
                if (data.code === 0) {
                    updateUnreadBadge(data.data.unread_count);
                }
            }
        } catch (error) {
            console.error('[全局Socket] 获取未读消息数失败:', error);
        }
    }
    
    function updateUnreadBadge(count) {
        const badge = document.getElementById('unread-badge');
        if (badge) {
            // ✅ 始终显示徽章（即使count为0）
            badge.textContent = count > 99 ? '99+' : count;
            badge.style.display = 'inline-block';
            console.log('[全局Socket] 未读消息徽章已更新:', count);
        }
    }
    
    // ========== Socket监听未读消息更新 ==========
    function setupUnreadMessageListener() {
        if (socket) {
            socket.on('unread_messages_update', function(data) {
                console.log('[全局Socket] 收到未读消息更新:', data);
                updateUnreadBadge(data.unread_count);
            });
        }
    }

    // ========== 导出全局对象 ==========
    window.GlobalSocket = {
        socket: socket,
        stopTitleFlash: stopTitleFlash,
        startTitleFlash: startTitleFlash,
        getUnreadCount: () => unreadCount,
        resetUnreadCount: () => { unreadCount = 0; },
        fetchUnreadCount: fetchUnreadCount  // ✅ 导出刷新函数
    };
    
    // ✅ 在页面加载时获取未读消息数
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(fetchUnreadCount, 1000);  // 延迟1秒，等待Socket连接建立
            setupUnreadMessageListener();  // 设置监听器
            // 定期刷新（每30秒）
            setInterval(fetchUnreadCount, 30000);
        });
    } else {
        setTimeout(fetchUnreadCount, 1000);
        setupUnreadMessageListener();
        setInterval(fetchUnreadCount, 30000);
    }

})();

