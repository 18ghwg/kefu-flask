/**
 * 客服端权限检查和会话管理模块
 * 处理客服看到的访客列表、回复权限等
 */

class ServicePermission {
    constructor() {
        this.currentServiceId = null;
        this.currentLevel = null;  // 'service' | 'manager' | 'super_manager'
        this.selectedVisitorId = null;
        this.replyPermissionCache = new Map();
    }
    
    /**
     * 初始化
     */
    init(serviceId, level) {
        this.currentServiceId = serviceId;
        this.currentLevel = level;
        
        console.log('客服权限模块初始化:', {
            serviceId: this.currentServiceId,
            level: this.currentLevel
        });
    }
    
    /**
     * 获取访客列表
     */
    async getVisitorList(includeAll = false) {
        try {
            // 管理员可以选择查看所有访客
            const url = `/api/assignment/service-visitors?include_all=${includeAll}`;
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include'
            });
            
            const result = await response.json();
            
            if (result.code === 0) {
                return result.data.visitors || [];
            } else {
                console.error('获取访客列表失败:', result.msg);
                return [];
            }
        } catch (error) {
            console.error('获取访客列表异常:', error);
            return [];
        }
    }
    
    /**
     * 检查回复权限
     */
    async checkReplyPermission(visitorId) {
        // 检查缓存
        if (this.replyPermissionCache.has(visitorId)) {
            const cached = this.replyPermissionCache.get(visitorId);
            // 缓存5秒
            if (Date.now() - cached.timestamp < 5000) {
                return cached.data;
            }
        }
        
        try {
            const response = await fetch('/api/assignment/check-reply-permission', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    visitor_id: visitorId
                })
            });
            
            const result = await response.json();
            
            if (result.code === 0) {
                // 缓存结果
                this.replyPermissionCache.set(visitorId, {
                    data: result.data,
                    timestamp: Date.now()
                });
                return result.data;
            } else {
                console.error('检查权限失败:', result.msg);
                return { can_reply: false, reason: '权限检查失败' };
            }
        } catch (error) {
            console.error('检查权限异常:', error);
            return { can_reply: false, reason: '网络错误' };
        }
    }
    
    /**
     * 渲染访客列表
     */
    async renderVisitorList(containerId, includeAll = false) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        // 显示加载状态
        container.innerHTML = '<div class="loading">加载中...</div>';
        
        // 获取列表
        const visitors = await this.getVisitorList(includeAll);
        
        if (visitors.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-inbox"></i>
                    <p>暂无访客</p>
                </div>
            `;
            return;
        }
        
        // 渲染列表
        let html = '';
        for (const item of visitors) {
            const visitor = item.visitor;
            const session = item.session;
            const canReply = item.can_reply;
            const isMine = item.is_mine;
            const assignedService = item.assigned_service;
            
            // 标签
            let badges = '';
            if (session.is_exclusive) {
                badges += '<span class="badge badge-exclusive">专属</span>';
            }
            if (!canReply && assignedService) {
                badges += `<span class="badge badge-assigned">由 ${assignedService.nick_name} 接待</span>`;
            }
            if (isMine) {
                badges += '<span class="badge badge-mine">我的</span>';
            }
            
            // 权限提示图标
            const lockIcon = !canReply ? '<i class="fas fa-lock" title="无回复权限"></i>' : '';
            
            html += `
                <div class="visitor-item ${isMine ? 'is-mine' : ''} ${!canReply ? 'locked' : ''}" 
                     data-visitor-id="${visitor.visitor_id}"
                     onclick="servicePermission.selectVisitor('${visitor.visitor_id}')">
                    <div class="visitor-avatar">
                        <img src="${visitor.avatar || '/static/img/default-avatar.svg'}" 
                             alt="${visitor.visitor_name}">
                    </div>
                    <div class="visitor-info">
                        <div class="visitor-name">
                            ${visitor.visitor_name}
                            ${lockIcon}
                        </div>
                        <div class="visitor-badges">
                            ${badges}
                        </div>
                    </div>
                    <div class="visitor-meta">
                        <span class="visitor-time">${this.formatTime(session.updated_at)}</span>
                    </div>
                </div>
            `;
        }
        
        container.innerHTML = html;
    }
    
    /**
     * 选择访客
     */
    async selectVisitor(visitorId) {
        this.selectedVisitorId = visitorId;
        
        // 检查权限
        const permission = await this.checkReplyPermission(visitorId);
        
        // 更新UI
        this.updateChatUI(visitorId, permission);
        
        // 高亮选中的访客
        document.querySelectorAll('.visitor-item').forEach(item => {
            item.classList.remove('active');
        });
        const selectedItem = document.querySelector(`[data-visitor-id="${visitorId}"]`);
        if (selectedItem) {
            selectedItem.classList.add('active');
        }
    }
    
    /**
     * 更新聊天UI
     */
    updateChatUI(visitorId, permission) {
        const inputContainer = document.getElementById('chat-input-container');
        const permissionWarning = document.getElementById('permission-warning');
        
        if (!permission.can_reply) {
            // 无权限：禁用输入，显示提示
            if (inputContainer) {
                const textarea = inputContainer.querySelector('textarea');
                const sendBtn = inputContainer.querySelector('.send-btn');
                if (textarea) textarea.disabled = true;
                if (sendBtn) sendBtn.disabled = true;
                inputContainer.classList.add('disabled');
            }
            
            if (permissionWarning) {
                const reason = permission.reason || '无权限回复该访客';
                const assignedInfo = permission.assigned_service ? 
                    `（当前由 ${permission.assigned_service.nick_name} 接待）` : '';
                
                permissionWarning.innerHTML = `
                    <div class="warning-content">
                        <i class="fas fa-lock"></i>
                        <span>${reason}${assignedInfo}</span>
                    </div>
                `;
                permissionWarning.style.display = 'block';
            }
        } else {
            // 有权限：启用输入
            if (inputContainer) {
                const textarea = inputContainer.querySelector('textarea');
                const sendBtn = inputContainer.querySelector('.send-btn');
                if (textarea) textarea.disabled = false;
                if (sendBtn) sendBtn.disabled = false;
                inputContainer.classList.remove('disabled');
            }
            
            if (permissionWarning) {
                permissionWarning.style.display = 'none';
            }
        }
    }
    
    /**
     * 实时检查权限（访客可能被其他客服接管）
     */
    async monitorPermission(visitorId, interval = 10000) {
        // 清除之前的监控
        if (this.permissionMonitor) {
            clearInterval(this.permissionMonitor);
        }
        
        // 定时检查
        this.permissionMonitor = setInterval(async () => {
            if (this.selectedVisitorId === visitorId) {
                const permission = await this.checkReplyPermission(visitorId);
                this.updateChatUI(visitorId, permission);
            } else {
                clearInterval(this.permissionMonitor);
            }
        }, interval);
    }
    
    /**
     * 获取工作负载
     */
    async getWorkload() {
        try {
            const response = await fetch('/api/assignment/service-workload', {
                credentials: 'include'
            });
            
            const result = await response.json();
            
            if (result.code === 0) {
                return result.data;
            }
            return null;
        } catch (error) {
            console.error('获取工作负载失败:', error);
            return null;
        }
    }
    
    /**
     * 更新工作负载显示
     */
    async updateWorkloadDisplay(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        const workload = await this.getWorkload();
        if (!workload) return;
        
        const { current_chat_count, max_concurrent_chats, work_status, 
                utilization_rate, available_slots } = workload;
        
        // 状态颜色
        let statusColor = '#10b981';  // 空闲 - 绿色
        let statusText = '空闲';
        
        if (work_status === 'busy') {
            statusColor = '#f59e0b';  // 忙碌 - 橙色
            statusText = '忙碌';
        } else if (work_status === 'full') {
            statusColor = '#ef4444';  // 满载 - 红色
            statusText = '满载';
        } else if (work_status === 'offline') {
            statusColor = '#9ca3af';  // 离线 - 灰色
            statusText = '离线';
        }
        
        container.innerHTML = `
            <div class="workload-card">
                <div class="workload-header">
                    <span class="workload-label">工作状态</span>
                    <span class="workload-status" style="color: ${statusColor}">
                        ${statusText}
                    </span>
                </div>
                <div class="workload-stats">
                    <div class="stat-item">
                        <span class="stat-value">${current_chat_count}</span>
                        <span class="stat-label">当前接待</span>
                    </div>
                    <div class="stat-divider">/</div>
                    <div class="stat-item">
                        <span class="stat-value">${max_concurrent_chats}</span>
                        <span class="stat-label">上限</span>
                    </div>
                </div>
                <div class="workload-bar">
                    <div class="workload-progress" style="width: ${utilization_rate}%; background: ${statusColor}"></div>
                </div>
                <div class="workload-footer">
                    <span>负载率: ${utilization_rate}%</span>
                    <span>可用: ${available_slots} 位</span>
                </div>
            </div>
        `;
    }
    
    /**
     * 格式化时间
     */
    formatTime(timeStr) {
        if (!timeStr) return '';
        
        const date = new Date(timeStr);
        const now = new Date();
        const diff = now - date;
        
        // 小于1分钟
        if (diff < 60000) {
            return '刚刚';
        }
        // 小于1小时
        if (diff < 3600000) {
            return Math.floor(diff / 60000) + '分钟前';
        }
        // 小于1天
        if (diff < 86400000) {
            return Math.floor(diff / 3600000) + '小时前';
        }
        // 显示日期
        return date.toLocaleDateString();
    }
    
    /**
     * 清除权限缓存
     */
    clearPermissionCache() {
        this.replyPermissionCache.clear();
    }
    
    /**
     * 是否为管理员
     */
    isAdmin() {
        return this.currentLevel in ['super_manager', 'manager'];
    }
}

// 创建全局实例
const servicePermission = new ServicePermission();

