/**
 * 访客端智能分配模块
 * 处理访客接入、排队、专属客服等逻辑
 */

class VisitorAssignment {
    constructor() {
        this.visitorId = null;
        this.businessId = 1;
        this.exclusiveServiceId = null;  // 从URL获取专属客服ID
        this.currentService = null;
        this.queueStatus = null;
        this.queueCheckInterval = null;
    }
    
    /**
     * 初始化
     */
    init(visitorId, businessId = 1) {
        this.visitorId = visitorId;
        this.businessId = businessId;
        
        // 从URL参数获取专属客服ID
        this.exclusiveServiceId = this.getExclusiveServiceIdFromURL();
        
        console.log('访客分配模块初始化:', {
            visitorId: this.visitorId,
            businessId: this.businessId,
            exclusiveServiceId: this.exclusiveServiceId
        });
    }
    
    /**
     * 从URL获取专属客服ID
     */
    getExclusiveServiceIdFromURL() {
        const urlParams = new URLSearchParams(window.location.search);
        const serviceId = urlParams.get('service_id') || urlParams.get('sid');
        return serviceId ? parseInt(serviceId) : null;
    }
    
    /**
     * 请求分配客服
     */
    async requestService(priority = 0) {
        try {
            const response = await fetch('/api/assignment/request-service', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    visitor_id: this.visitorId,
                    business_id: this.businessId,
                    exclusive_service_id: this.exclusiveServiceId,
                    priority: priority
                })
            });
            
            const result = await response.json();
            
            if (result.code === 0) {
                return this.handleAssignmentResult(result.data);
            } else {
                this.showError(result.msg || '分配客服失败');
                return null;
            }
        } catch (error) {
            console.error('请求客服失败:', error);
            this.showError('网络错误，请稍后再试');
            return null;
        }
    }
    
    /**
     * 处理分配结果
     */
    handleAssignmentResult(data) {
        console.log('分配结果:', data);
        
        if (data.action === 'assigned') {
            // 已分配客服
            this.currentService = data.service;
            this.stopQueueCheck();
            this.showServiceAssigned(data);
            return data;
            
        } else if (data.action === 'queued') {
            // 进入排队
            this.queueStatus = data;
            this.showQueueStatus(data);
            this.startQueueCheck();
            return data;
            
        } else if (data.action === 'error') {
            // 错误
            this.showError(data.message);
            return null;
        }
    }
    
    /**
     * 显示已分配客服
     */
    showServiceAssigned(data) {
        const { service, is_exclusive, is_online, offline_tip } = data;
        
        // 更新聊天界面头部
        const chatHeader = document.querySelector('.chat-header-info');
        if (chatHeader) {
            const statusBadge = is_online ? 
                '<span class="status-badge online">在线</span>' :
                '<span class="status-badge offline">离线</span>';
            
            const exclusiveBadge = is_exclusive ?
                '<span class="exclusive-badge">专属</span>' : '';
            
            chatHeader.innerHTML = `
                <img src="${service.avatar || '/static/img/default-avatar.svg'}" 
                     alt="${service.nick_name}" class="avatar">
                <div class="service-info">
                    <div class="service-name">
                        ${service.nick_name}
                        ${statusBadge}
                        ${exclusiveBadge}
                    </div>
                </div>
            `;
        }
        
        // 显示系统消息
        const message = is_exclusive ? 
            `已为您接入专属客服 ${service.nick_name}` :
            `已为您接入客服 ${service.nick_name}`;
        
        this.appendSystemMessage(message);
        
        // 如果客服离线，显示提示
        if (!is_online && offline_tip) {
            this.appendSystemMessage(offline_tip, 'warning');
        }
        
        // 隐藏排队界面，显示聊天界面
        this.hideQueueUI();
        this.showChatUI();
    }
    
    /**
     * 显示排队状态
     */
    showQueueStatus(data) {
        const { position, estimated_wait_time, message } = data;
        
        // 隐藏聊天界面，显示排队界面
        this.hideChatUI();
        this.showQueueUI();
        
        // 更新排队信息
        const queueContainer = document.getElementById('queue-container');
        if (queueContainer) {
            const minutes = Math.ceil(estimated_wait_time / 60);
            const timeText = minutes > 0 ? 
                `预计等待 ${minutes} 分钟` : '即将为您分配';
            
            queueContainer.innerHTML = `
                <div class="queue-status">
                    <div class="queue-icon">
                        <i class="fas fa-clock"></i>
                    </div>
                    <h3>正在为您分配客服...</h3>
                    <div class="queue-info">
                        <div class="queue-position">
                            <span class="position-number">${position}</span>
                            <span class="position-label">当前位置</span>
                        </div>
                        <div class="queue-message">
                            ${message}
                        </div>
                        <div class="queue-time">
                            ${timeText}
                        </div>
                    </div>
                    <div class="queue-tips">
                        <p>💡 您也可以：</p>
                        <button class="btn-secondary" onclick="visitorAssignment.showFAQ()">
                            <i class="fas fa-question-circle"></i> 查看常见问题
                        </button>
                        <button class="btn-secondary" onclick="visitorAssignment.leaveMessage()">
                            <i class="fas fa-envelope"></i> 留言给客服
                        </button>
                    </div>
                </div>
            `;
        }
    }
    
    /**
     * 开始定时检查排队状态
     */
    startQueueCheck() {
        // 清除之前的定时器
        this.stopQueueCheck();
        
        // 每5秒检查一次
        this.queueCheckInterval = setInterval(async () => {
            await this.checkQueueStatus();
        }, 5000);
    }
    
    /**
     * 停止检查排队状态
     */
    stopQueueCheck() {
        if (this.queueCheckInterval) {
            clearInterval(this.queueCheckInterval);
            this.queueCheckInterval = null;
        }
    }
    
    /**
     * 检查排队状态
     */
    async checkQueueStatus() {
        try {
            const response = await fetch(
                `/api/assignment/queue-status?visitor_id=${this.visitorId}&business_id=${this.businessId}`
            );
            const result = await response.json();
            
            if (result.code === 0 && result.data) {
                const data = result.data;
                
                // 如果已分配客服
                if (data.assigned && data.service) {
                    this.stopQueueCheck();
                    this.showServiceAssigned({
                        service: data.service,
                        is_exclusive: false,
                        is_online: true
                    });
                }
                // 如果还在排队，更新位置
                else if (data.in_queue) {
                    this.updateQueuePosition(data);
                }
            }
        } catch (error) {
            console.error('检查排队状态失败:', error);
        }
    }
    
    /**
     * 更新排队位置
     */
    updateQueuePosition(data) {
        const positionElement = document.querySelector('.position-number');
        const messageElement = document.querySelector('.queue-message');
        const timeElement = document.querySelector('.queue-time');
        
        if (positionElement) {
            positionElement.textContent = data.position || 0;
        }
        
        if (messageElement) {
            messageElement.textContent = data.message || '';
        }
        
        if (timeElement && data.estimated_wait_time) {
            const minutes = Math.ceil(data.estimated_wait_time / 60);
            timeElement.textContent = minutes > 0 ? 
                `预计等待 ${minutes} 分钟` : '即将为您分配';
        }
    }
    
    /**
     * 追加系统消息
     */
    appendSystemMessage(content, type = 'info') {
        const messagesContainer = document.getElementById('messages');
        if (!messagesContainer) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message system-message ${type}`;
        messageDiv.innerHTML = `
            <div class="message-content">
                <i class="fas fa-info-circle"></i>
                ${content}
            </div>
        `;
        
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    /**
     * 显示错误
     */
    showError(message) {
        // 可以使用更好看的提示组件
        alert(message);
    }
    
    /**
     * 显示/隐藏UI
     */
    showQueueUI() {
        const queueContainer = document.getElementById('queue-container');
        if (queueContainer) {
            queueContainer.style.display = 'flex';
        }
    }
    
    hideQueueUI() {
        const queueContainer = document.getElementById('queue-container');
        if (queueContainer) {
            queueContainer.style.display = 'none';
        }
    }
    
    showChatUI() {
        const chatContainer = document.getElementById('chat-container');
        if (chatContainer) {
            chatContainer.style.display = 'flex';
        }
    }
    
    hideChatUI() {
        const chatContainer = document.getElementById('chat-container');
        if (chatContainer) {
            chatContainer.style.display = 'none';
        }
    }
    
    /**
     * 查看常见问题
     */
    showFAQ() {
        // TODO: 实现常见问题弹窗
        console.log('显示常见问题');
    }
    
    /**
     * 留言
     */
    leaveMessage() {
        // TODO: 实现留言功能
        console.log('留言功能');
    }
    
    /**
     * 获取当前客服信息
     */
    getCurrentService() {
        return this.currentService;
    }
    
    /**
     * 是否为专属客服会话
     */
    isExclusiveSession() {
        return this.exclusiveServiceId !== null;
    }
}

// 创建全局实例
const visitorAssignment = new VisitorAssignment();

