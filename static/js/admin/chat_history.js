/**
 * 聊天记录查询页面 - 脚本
 */

// 全局变量
let currentPage = 1;
let totalPages = 1;
let currentMode = 'session'; // session 或 message

// 页面加载
document.addEventListener('DOMContentLoaded', function() {
    loadStatistics();
    loadServiceList();
    loadHistory();
    
    // 注意：不设置默认日期，让用户自己筛选或显示所有数据
});

// 加载统计数据
async function loadStatistics() {
    try {
        const response = await fetch('/api/admin/chat-history/statistics?days=7');
        const result = await response.json();
        
        if (result.code === 0) {
            const data = result.data;
            document.getElementById('totalMessages').textContent = data.total_messages || 0;
            document.getElementById('totalSessions').textContent = data.total_sessions || 0;
            document.getElementById('avgDuration').textContent = (data.avg_duration || 0) + '分钟';
            document.getElementById('avgResponse').textContent = (data.avg_response_time || 0) + '秒';
        } else {
            console.error('加载统计数据失败:', result.msg);
        }
    } catch (error) {
        console.error('加载统计数据失败:', error);
    }
}

// 加载客服列表（用于筛选）
async function loadServiceList() {
    try {
        const response = await fetch('/api/service/list');
        const result = await response.json();
        
        console.log('客服列表响应:', result);
        
        if (result.code === 0 || result.code === '0') {
            const select = document.getElementById('serviceId');
            
            // 兼容不同的数据结构
            let serviceList = [];
            if (result.data && result.data.list) {
                serviceList = result.data.list;
            } else if (result.data && result.data.services) {
                serviceList = result.data.services;
            } else if (Array.isArray(result.data)) {
                serviceList = result.data;
            } else if (Array.isArray(result.list)) {
                serviceList = result.list;
            }
            
            if (serviceList && serviceList.length > 0) {
                serviceList.forEach(service => {
                    const option = document.createElement('option');
                    option.value = service.service_id;
                    option.textContent = service.nick_name || service.user_name;
                    select.appendChild(option);
                });
            } else {
                console.warn('客服列表为空');
            }
        } else {
            console.error('获取客服列表失败:', result.msg || '未知错误');
        }
    } catch (error) {
        console.error('加载客服列表失败:', error);
    }
}

// 加载聊天记录
async function loadHistory(page = 1) {
    if (currentMode === 'session') {
        await loadSessions(page);
    } else {
        await loadMessages(page);
    }
}

// 加载会话列表
async function loadSessions(page = 1) {
    try {
        const params = getFilterParams();
        params.append('page', page);
        params.append('per_page', 20);
        
        console.log('加载会话列表，参数:', params.toString());
        const response = await fetch(`/api/admin/chat-sessions?${params}`);
        const result = await response.json();
        
        console.log('会话列表响应:', result);
        
        if (result.code === 0) {
            currentPage = page;
            totalPages = result.data.pages;
            
            if (result.data.list && result.data.list.length > 0) {
                renderSessions(result.data.list);
            } else {
                showEmptyState('sessionsList');
            }
            updatePagination();
        } else {
            console.error('加载会话列表失败:', result.msg);
            showEmptyState('sessionsList');
        }
    } catch (error) {
        console.error('加载会话列表失败:', error);
        showEmptyState('sessionsList');
    }
}

// 加载消息列表
async function loadMessages(page = 1) {
    try {
        const params = getFilterParams();
        params.append('page', page);
        params.append('per_page', 50);
        
        console.log('加载消息列表，参数:', params.toString());
        const response = await fetch(`/api/admin/chat-history?${params}`);
        const result = await response.json();
        
        console.log('消息列表响应:', result);
        
        if (result.code === 0) {
            currentPage = page;
            totalPages = result.data.pages;
            
            if (result.data.list && result.data.list.length > 0) {
                renderMessagesList(result.data.list);
            } else {
                showEmptyState('messagesList');
            }
            updatePagination();
        } else {
            console.error('加载消息列表失败:', result.msg);
            showEmptyState('messagesList');
        }
    } catch (error) {
        console.error('加载消息列表失败:', error);
        showEmptyState('messagesList');
    }
}

// 获取筛选参数
function getFilterParams() {
    const params = new URLSearchParams();
    
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    const visitorKeyword = document.getElementById('visitorKeyword').value;
    const serviceId = document.getElementById('serviceId').value;
    const keyword = document.getElementById('keyword').value;
    
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    if (visitorKeyword) params.append('visitor_id', visitorKeyword);
    if (serviceId) params.append('service_id', serviceId);
    if (keyword) params.append('keyword', keyword);
    
    return params;
}

// 渲染会话列表
function renderSessions(sessions) {
    const container = document.getElementById('sessionsList');
    
    if (!sessions || sessions.length === 0) {
        showEmptyState('sessionsList');
        return;
    }
    
    container.innerHTML = sessions.map(session => {
        // 安全获取 visitor_id
        const visitorId = session.queue_id || session.visitor_id || '';
        
        // 调试：如果 visitor_id 无效，输出警告
        if (!visitorId || typeof visitorId !== 'string') {
            console.warn('无效的 visitor_id:', session);
            return ''; // 跳过这个会话
        }
        
        // 安全获取首字母
        const visitorInitial = session.visitor_name && session.visitor_name.length > 0 
            ? session.visitor_name.charAt(0).toUpperCase() 
            : 'V';
        const serviceInitial = session.service_name && session.service_name.length > 0 
            ? session.service_name.charAt(0).toUpperCase() 
            : 'S';
        
        return `
        <div class="session-item">
            <div class="session-info">
                <div class="participant">
                    <div class="avatar">${visitorInitial}</div>
                    <div class="info">
                        <h4>${session.visitor_name || '未知访客'}</h4>
                        <p>访客ID: ${session.visitor_id}</p>
                    </div>
                </div>
                <div class="arrow"><i class="fas fa-arrow-right"></i></div>
                <div class="participant">
                    <div class="avatar service">${serviceInitial}</div>
                    <div class="info">
                        <h4>${session.service_name || '未分配'}</h4>
                        <p>客服</p>
                    </div>
                </div>
            </div>
            
            <div class="session-stats">
                <div class="stat">
                    <i class="fas fa-comments"></i>
                    <span>${session.message_count || 0} 条消息</span>
                </div>
                <div class="stat">
                    <i class="fas fa-clock"></i>
                    <span>${formatDuration(session.duration)}</span>
                </div>
                <div class="stat">
                    <i class="fas fa-calendar"></i>
                    <span>${formatDateTime(session.start_time)}</span>
                </div>
            </div>
            
            <div class="session-actions">
                <button class="btn-primary btn-sm" onclick="viewSessionDetail('${visitorId}')">
                    <i class="fas fa-eye"></i> 查看详情
                </button>
                <span class="status-badge status-${session.state}">${getStateText(session.state)}</span>
            </div>
        </div>
        `;
    }).filter(html => html).join('');
}

// 渲染消息列表（消息视图）
function renderMessagesList(messages) {
    const container = document.getElementById('messagesList');
    
    if (!messages || messages.length === 0) {
        showEmptyState('messagesList');
        return;
    }
    
    // 使用DocumentFragment提高性能
    const fragment = document.createDocumentFragment();
    
    messages.forEach((msg, index) => {
        try {
        const isRobot = (msg.service_id === 0 || msg.service_id === '0' || msg.service_name === '机器人');
        const isVisitor = msg.direction === 'to_service';
        const senderName = isVisitor ? (msg.visitor_name || '访客') : (isRobot ? '智能机器人' : (msg.service_name || '客服'));
        
        const messageItem = document.createElement('div');
        messageItem.className = `message-item direction-${msg.direction}`;
        if (isRobot && !isVisitor) {
            messageItem.classList.add('robot-message');
        }
        
        let avatarHtml = '';
        if (isVisitor) {
            const visitorInitial = msg.visitor_name && msg.visitor_name.length > 0 ? msg.visitor_name.charAt(0).toUpperCase() : 'V';
            avatarHtml = `<div class="avatar visitor">${visitorInitial}</div>`;
        } else if (isRobot) {
            avatarHtml = `<div class="avatar robot"><i class="fas fa-robot"></i></div>`;
        } else {
            const serviceInitial = msg.service_name && msg.service_name.length > 0 ? msg.service_name.charAt(0).toUpperCase() : 'S';
            avatarHtml = `<div class="avatar service">${serviceInitial}</div>`;
        }
        
        messageItem.innerHTML = `
            <div class="message-avatar">
                ${avatarHtml}
            </div>
            <div class="message-content">
                <div class="message-header">
                    <span class="sender-name">${senderName}</span>
                    ${isRobot && !isVisitor ? '<span class="robot-badge"><i class="fas fa-robot"></i> 机器人</span>' : ''}
                    <span class="message-time">${formatTime(msg.timestamp)}</span>
                </div>
                <div class="message-body">
                    ${formatMessageContent(msg.content, msg.msg_type, isRobot && !isVisitor)}
                </div>
            </div>
        `;
        
        fragment.appendChild(messageItem);
        
        } catch (error) {
            console.error(`渲染消息列表项 ${index} 时出错:`, error, '消息数据:', msg);
            // 继续渲染其他消息
        }
    });
    
    container.innerHTML = '';
    container.appendChild(fragment);
}

// 显示空状态
function showEmptyState(containerId) {
    const container = document.getElementById(containerId);
    container.innerHTML = `
        <div class="empty-state">
            <i class="fas fa-comments"></i>
            <p>暂无聊天记录</p>
        </div>
    `;
}

// 切换视图模式
function switchMode(mode) {
    currentMode = mode;
    currentPage = 1;
    
    // 更新按钮状态
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.mode === mode) {
            btn.classList.add('active');
        }
    });
    
    // 切换视图
    if (mode === 'session') {
        document.getElementById('sessionView').style.display = 'block';
        document.getElementById('messageView').style.display = 'none';
    } else {
        document.getElementById('sessionView').style.display = 'none';
        document.getElementById('messageView').style.display = 'block';
    }
    
    loadHistory(1);
}

// 全局变量存储当前会话信息
let currentSessionData = null;
let currentSessionPage = 1;
let totalSessionPages = 1;
let isLoadingMoreMessages = false;
let hasMoreHistoryMessages = false;

// 查看会话详情
async function viewSessionDetail(visitorId) {
    try {
        // 重置状态
        currentSessionData = null;
        currentSessionPage = 1;
        isLoadingMoreMessages = false;
        
        // 显示加载中
        const container = document.getElementById('sessionDetail');
        container.innerHTML = `
            <div class="loading-container">
                <div class="spinner"></div>
                <p>加载会话详情中...</p>
            </div>
        `;
        
        // 立即显示模态框（显示加载状态）
        document.getElementById('detailModal').classList.add('show');
        
        // 获取会话基本信息
        const response = await fetch(`/api/admin/chat-history/session/${visitorId}`);
        const result = await response.json();
        
        if (result.code === 0) {
            currentSessionData = result.data;
            // 使用分页API加载消息
            await loadSessionDetailWithPagination(visitorId, currentSessionData);
        } else {
            container.innerHTML = `
                <div class="error-container">
                    <i class="fas fa-exclamation-circle"></i>
                    <p>加载失败: ${result.msg}</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('加载会话详情失败:', error);
        const container = document.getElementById('sessionDetail');
        container.innerHTML = `
            <div class="error-container">
                <i class="fas fa-exclamation-circle"></i>
                <p>加载失败，请重试</p>
            </div>
        `;
    }
}

// 使用分页API加载会话详情（倒序加载，最新消息先）
async function loadSessionDetailWithPagination(visitorId, sessionInfo) {
    try {
        const container = document.getElementById('sessionDetail');
        
        // 首先获取总消息数，计算最后一页
        const response = await fetch(`/api/admin/chat-history/session/${visitorId}/messages?page=1&per_page=50`);
        const result = await response.json();
        
        if (result.code === 0) {
            totalSessionPages = result.data.total_pages;
            currentSessionPage = totalSessionPages; // 从最后一页开始
            hasMoreHistoryMessages = totalSessionPages > 1;
            
            // 获取最后一页（最新的消息）
            const lastPageResponse = await fetch(`/api/admin/chat-history/session/${visitorId}/messages?page=${totalSessionPages}&per_page=50`);
            const lastPageResult = await lastPageResponse.json();
            
            if (lastPageResult.code === 0) {
                // 创建头部
                const header = document.createElement('div');
                header.className = 'detail-header';
                header.innerHTML = `
                    <h4>会话信息</h4>
                    <div class="detail-info">
                        <span><strong>访客:</strong> ${sessionInfo.visitor_name}</span>
                        <span><strong>客服:</strong> ${sessionInfo.service_name}</span>
                        <span><strong>开始时间:</strong> ${formatDateTime(sessionInfo.start_time)}</span>
                        <span><strong>消息数:</strong> ${result.data.total}</span>
                    </div>
                `;
                
                // 创建消息容器
                const messagesContainer = document.createElement('div');
                messagesContainer.className = 'detail-messages';
                messagesContainer.id = 'detailMessages';
                
                // 渲染最新的消息
                renderMessagesBatch(messagesContainer, lastPageResult.data.messages, sessionInfo.visitor_name);
                
                // 清空并添加内容
                container.innerHTML = '';
                container.appendChild(header);
                container.appendChild(messagesContainer);
                
                // 滚动到底部（显示最新消息）
                setTimeout(() => {
                    messagesContainer.scrollTop = messagesContainer.scrollHeight;
                }, 100);
                
                // 如果还有历史消息，设置向上滚动加载
                if (hasMoreHistoryMessages) {
                    setupScrollLoadingForHistory(messagesContainer, visitorId, sessionInfo.visitor_name);
                }
            }
        } else {
            container.innerHTML = `
                <div class="error-container">
                    <i class="fas fa-exclamation-circle"></i>
                    <p>加载消息失败: ${result.msg}</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('加载会话消息失败:', error);
        const container = document.getElementById('sessionDetail');
        container.innerHTML = `
            <div class="error-container">
                <i class="fas fa-exclamation-circle"></i>
                <p>加载失败，请重试</p>
            </div>
        `;
    }
}

// 设置向上滚动加载历史消息
function setupScrollLoadingForHistory(messagesContainer, visitorId, visitorName) {
    messagesContainer.addEventListener('scroll', async function() {
        // 滚动到顶部时加载历史消息
        if (messagesContainer.scrollTop < 100) {
            if (!isLoadingMoreMessages && hasMoreHistoryMessages && currentSessionPage > 1) {
                isLoadingMoreMessages = true;
                
                // 保存当前滚动高度
                const oldScrollHeight = messagesContainer.scrollHeight;
                
                // 显示加载指示器（在顶部）
                const loadingIndicator = document.createElement('div');
                loadingIndicator.className = 'loading-indicator';
                loadingIndicator.innerHTML = `
                    <div style="text-align: center; padding: 20px; color: var(--text-color-light);">
                        <i class="fas fa-spinner fa-spin"></i> 加载历史消息...
                    </div>
                `;
                messagesContainer.insertBefore(loadingIndicator, messagesContainer.firstChild);
                
                try {
                    // 加载上一页（更早的消息）
                    currentSessionPage--;
                    const response = await fetch(`/api/admin/chat-history/session/${visitorId}/messages?page=${currentSessionPage}&per_page=50`);
                    const result = await response.json();
                    
                    // 移除加载指示器
                    loadingIndicator.remove();
                    
                    if (result.code === 0 && result.data.messages.length > 0) {
                        // 渲染消息到顶部
                        renderMessagesToTop(messagesContainer, result.data.messages, visitorName);
                        
                        // 恢复滚动位置（保持用户视图不变）
                        const newScrollHeight = messagesContainer.scrollHeight;
                        messagesContainer.scrollTop = newScrollHeight - oldScrollHeight;
                        
                        // 检查是否还有更多历史消息
                        hasMoreHistoryMessages = currentSessionPage > 1;
                    }
                } catch (error) {
                    console.error('加载历史消息失败:', error);
                    loadingIndicator.innerHTML = `
                        <div style="text-align: center; padding: 20px; color: var(--error-color);">
                            <i class="fas fa-exclamation-circle"></i> 加载失败
                        </div>
                    `;
                    setTimeout(() => loadingIndicator.remove(), 2000);
                    currentSessionPage++; // 恢复页码
                } finally {
                    isLoadingMoreMessages = false;
                }
            }
        }
    });
}

// 渲染消息到顶部（用于加载历史消息）
function renderMessagesToTop(container, messages, visitorName) {
    const fragment = document.createDocumentFragment();
    let lastDate = null;
    
    // 获取容器中第一条消息的日期（用于判断是否需要插入日期分隔）
    const existingMessages = container.querySelectorAll('.message-item');
    if (existingMessages.length > 0) {
        const firstMsg = existingMessages[0];
        const firstTimeStr = firstMsg.dataset.timestamp;
        if (firstTimeStr) {
            lastDate = formatDateOnly(firstTimeStr);
        }
    }
    
    messages.forEach((msg, index) => {
        try {
        // 检查是否需要插入日期分隔符
        const currentDate = formatDateOnly(msg.timestamp);
        if (currentDate && currentDate !== lastDate) {
            const dateSeparator = createDateSeparator(msg.timestamp);
            fragment.appendChild(dateSeparator);
            lastDate = currentDate;
        }
        // 判断是否为机器人消息
        const isRobot = (msg.service_id === 0 || msg.service_id === '0' || msg.service_name === '机器人');
        const isVisitor = msg.direction === 'to_service';
        const senderName = isVisitor ? visitorName : (isRobot ? '智能机器人' : (msg.service_name || '客服'));
        
        // 创建消息项
        const messageItem = document.createElement('div');
        messageItem.className = `message-item direction-${msg.direction}`;
        messageItem.dataset.timestamp = msg.timestamp;
        if (isRobot && !isVisitor) {
            messageItem.classList.add('robot-message');
        }
        
        // 创建头像
        let avatarHtml = '';
        if (isVisitor) {
            const visitorInitial = visitorName && visitorName.length > 0 ? visitorName.charAt(0).toUpperCase() : 'V';
            avatarHtml = `<div class="avatar visitor">${visitorInitial}</div>`;
        } else if (isRobot) {
            avatarHtml = `<div class="avatar robot"><i class="fas fa-robot"></i></div>`;
        } else {
            const serviceInitial = msg.service_name && msg.service_name.length > 0 ? msg.service_name.charAt(0).toUpperCase() : 'S';
            avatarHtml = `<div class="avatar service">${serviceInitial}</div>`;
        }
        
        messageItem.innerHTML = `
            <div class="message-avatar">
                ${avatarHtml}
            </div>
            <div class="message-content">
                <div class="message-header">
                    <span class="sender-name">${senderName}</span>
                    ${isRobot && !isVisitor ? '<span class="robot-badge"><i class="fas fa-robot"></i> 机器人</span>' : ''}
                    <span class="message-time">${formatTime(msg.timestamp)}</span>
                </div>
                <div class="message-body">
                    ${formatMessageContent(msg.content, msg.msg_type, isRobot && !isVisitor)}
                </div>
            </div>
        `;
        
        fragment.appendChild(messageItem);
        
        } catch (error) {
            console.error(`渲染历史消息 ${index} 时出错:`, error, '消息数据:', msg);
        }
    });
    
    // 插入到容器顶部
    container.insertBefore(fragment, container.firstChild);
}

// 渲染消息批次（用于分页加载，追加到底部）
function renderMessagesBatch(container, messages, visitorName) {
    const fragment = document.createDocumentFragment();
    let lastDate = null;
    
    // 获取容器中最后一条消息的日期（用于判断是否需要插入日期分隔）
    const existingMessages = container.querySelectorAll('.message-item');
    if (existingMessages.length > 0) {
        const lastMsg = existingMessages[existingMessages.length - 1];
        const lastTimeStr = lastMsg.dataset.timestamp;
        if (lastTimeStr) {
            lastDate = formatDateOnly(lastTimeStr);
        }
    }
    
    messages.forEach((msg, index) => {
        try {
        // 检查是否需要插入日期分隔符
        const currentDate = formatDateOnly(msg.timestamp);
        if (currentDate && currentDate !== lastDate) {
            const dateSeparator = createDateSeparator(msg.timestamp);
            fragment.appendChild(dateSeparator);
            lastDate = currentDate;
        }
        // 判断是否为机器人消息（严格判断，支持数字和字符串）
        const isRobot = (msg.service_id === 0 || msg.service_id === '0' || msg.service_name === '机器人');
        const isVisitor = msg.direction === 'to_service';
        const senderName = isVisitor ? visitorName : (isRobot ? '智能机器人' : (msg.service_name || '客服'));
        
        // 创建消息项
        const messageItem = document.createElement('div');
        messageItem.className = `message-item direction-${msg.direction}`;
        messageItem.dataset.timestamp = msg.timestamp; // 保存时间戳用于日期分隔
        if (isRobot && !isVisitor) {
            messageItem.classList.add('robot-message');
        }
        
        // 创建头像（添加安全检查）
        let avatarHtml = '';
        if (isVisitor) {
            // 访客消息
            const visitorInitial = visitorName && visitorName.length > 0 ? visitorName.charAt(0).toUpperCase() : 'V';
            avatarHtml = `<div class="avatar visitor">${visitorInitial}</div>`;
        } else if (isRobot) {
            // 机器人消息
            avatarHtml = `<div class="avatar robot"><i class="fas fa-robot"></i></div>`;
        } else {
            // 客服消息
            const serviceInitial = msg.service_name && msg.service_name.length > 0 ? msg.service_name.charAt(0).toUpperCase() : 'S';
            avatarHtml = `<div class="avatar service">${serviceInitial}</div>`;
        }
        
        messageItem.innerHTML = `
            <div class="message-avatar">
                ${avatarHtml}
            </div>
            <div class="message-content">
                <div class="message-header">
                    <span class="sender-name">${senderName}</span>
                    ${isRobot && !isVisitor ? '<span class="robot-badge"><i class="fas fa-robot"></i> 机器人</span>' : ''}
                    <span class="message-time">${formatTime(msg.timestamp)}</span>
                </div>
                <div class="message-body">
                    ${formatMessageContent(msg.content, msg.msg_type, isRobot && !isVisitor)}
                </div>
            </div>
        `;
        
        fragment.appendChild(messageItem);
        
        } catch (error) {
            console.error(`渲染消息 ${index} 时出错:`, error, '消息数据:', msg);
            // 继续渲染其他消息，不中断
        }
    });
    
    container.appendChild(fragment);
}

// 关闭详情模态框
function closeDetailModal() {
    document.getElementById('detailModal').classList.remove('show');
}

// 搜索
function searchHistory() {
    currentPage = 1;
    loadHistory(1);
}

// 重置筛选
function resetFilters() {
    document.getElementById('startDate').value = '';
    document.getElementById('endDate').value = '';
    document.getElementById('visitorKeyword').value = '';
    document.getElementById('serviceId').value = '';
    document.getElementById('keyword').value = '';
    searchHistory();
}

// 导出记录
function exportHistory() {
    const params = getFilterParams();
    window.location.href = `/api/admin/chat-history/export?${params}`;
}

// 分页
function changePage(delta) {
    const newPage = currentPage + delta;
    if (newPage >= 1 && newPage <= totalPages) {
        loadHistory(newPage);
    }
}

// 更新分页
function updatePagination() {
    document.getElementById('prevBtn').disabled = currentPage <= 1;
    document.getElementById('nextBtn').disabled = currentPage >= totalPages;
    document.getElementById('pageInfo').textContent = `第 ${currentPage} / ${totalPages} 页`;
}

// HTML转义函数
function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return unsafe
        .toString()
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// 格式化消息内容
function formatMessageContent(content, msgType, isRobot) {
    if (!content) return '';
    
    try {
        if (msgType === 'image') {
            // 尝试解析JSON格式的图片消息
            let imageUrl = content;
            try {
                const imageData = JSON.parse(content);
                if (imageData.url) {
                    imageUrl = imageData.url;
                }
            } catch (e) {
                // 如果不是JSON，直接使用content作为URL
            }
            
            const safeUrl = escapeHtml(imageUrl);
            return `<img src="${safeUrl}" alt="图片" class="message-image" onerror="this.style.display='none'">`;
        } else if (msgType === 'file') {
            // 尝试解析JSON格式的文件消息
            let fileUrl = content;
            let fileName = '查看文件';
            try {
                const fileData = JSON.parse(content);
                if (fileData.url) {
                    fileUrl = fileData.url;
                    fileName = fileData.name || fileName;
                }
            } catch (e) {
                // 如果不是JSON，直接使用content作为URL
            }
            
            const safeUrl = escapeHtml(fileUrl);
            const safeName = escapeHtml(fileName);
            return `<a href="${safeUrl}" target="_blank" class="message-file"><i class="fas fa-file"></i> ${safeName}</a>`;
        } else {
            // 文本消息：所有消息都允许HTML渲染（已经过后端验证）
            // 但进行安全清理，移除危险标签和属性
            return sanitizeHtml(content);
        }
    } catch (error) {
        console.error('格式化消息内容时出错:', error, 'content:', content);
        return escapeHtml(content);
    }
}

// 清理HTML内容（移除危险标签和属性）
function sanitizeHtml(html) {
    if (!html) return '';
    
    // 创建临时DOM来解析HTML
    const temp = document.createElement('div');
    temp.innerHTML = html;
    
    // 移除所有危险标签
    temp.querySelectorAll('script, style, iframe, object, embed, form, input, button').forEach(el => el.remove());
    
    // 移除危险属性
    temp.querySelectorAll('*').forEach(el => {
        // 移除事件处理属性
        Array.from(el.attributes).forEach(attr => {
            if (attr.name.startsWith('on') || attr.name === 'formaction' || attr.name === 'form') {
                el.removeAttribute(attr.name);
            }
        });
        
        // 清理a标签的href，只允许http/https/mailto
        if (el.tagName === 'A' && el.hasAttribute('href')) {
            const href = el.getAttribute('href');
            if (href && !href.match(/^(https?:|mailto:)/i)) {
                el.removeAttribute('href');
            }
        }
    });
    
    return temp.innerHTML;
}

// 格式化时间
function formatTime(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
}

// 格式化日期时间
function formatDateTime(timestamp) {
    if (!timestamp) return '-';
    const date = new Date(timestamp);
    return date.toLocaleString('zh-CN');
}

// 格式化时长
function formatDuration(seconds) {
    if (!seconds) return '-';
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return minutes > 0 ? `${minutes}分${secs}秒` : `${secs}秒`;
}

// 获取状态文本
function getStateText(state) {
    const map = {
        'normal': '进行中',
        'complete': '已完成',
        'blacklist': '已拉黑',
        'waiting': '等待中',
        'chatting': '进行中'
    };
    return map[state] || state;
}

// 创建日期分隔符
function createDateSeparator(timestamp) {
    const separator = document.createElement('div');
    separator.className = 'date-separator';
    
    const dateStr = formatDateSeparator(timestamp);
    separator.innerHTML = `<span class="date-separator-text">${dateStr}</span>`;
    
    return separator;
}

// 格式化日期分隔符（类似微信）
function formatDateSeparator(timestamp) {
    if (!timestamp) return '';
    
    const date = new Date(timestamp);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    
    // 重置时间到00:00:00用于日期比较
    const dateOnly = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    const todayOnly = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    const yesterdayOnly = new Date(yesterday.getFullYear(), yesterday.getMonth(), yesterday.getDate());
    
    if (dateOnly.getTime() === todayOnly.getTime()) {
        return '今天';
    } else if (dateOnly.getTime() === yesterdayOnly.getTime()) {
        return '昨天';
    } else {
        // 显示具体日期
        const year = date.getFullYear();
        const month = date.getMonth() + 1;
        const day = date.getDate();
        const weekdays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'];
        const weekday = weekdays[date.getDay()];
        
        // 如果是今年，不显示年份
        if (year === today.getFullYear()) {
            return `${month}月${day}日 ${weekday}`;
        } else {
            return `${year}年${month}月${day}日 ${weekday}`;
        }
    }
}

// 格式化为纯日期（用于比较）
function formatDateOnly(timestamp) {
    if (!timestamp) return null;
    const date = new Date(timestamp);
    return `${date.getFullYear()}-${date.getMonth() + 1}-${date.getDate()}`;
}

// 点击模态框外部关闭
window.onclick = function(event) {
    const modal = document.getElementById('detailModal');
    if (event.target === modal) {
        closeDetailModal();
    }
}

