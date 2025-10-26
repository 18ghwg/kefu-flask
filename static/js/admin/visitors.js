/**
 * 访客管理页面脚本
 * 用途：管理后台 - 访客列表和管理功能
 */

let currentPage = 1;
let totalPages = 1;

// 加载统计数据
async function loadStatistics() {
    try {
        const response = await fetch('/api/visitor/statistics?days=7');
        const result = await response.json();
        
        if (result.code === 0) {
            const data = result.data;
            document.getElementById('totalVisitors').textContent = data.total_visitors;
            document.getElementById('onlineVisitors').textContent = data.online_visitors;
            document.getElementById('newVisitors').textContent = data.new_visitors;
            document.getElementById('returningVisitors').textContent = data.returning_visitors;
            document.getElementById('blacklistCount').textContent = data.blacklist_count;
        }
    } catch (error) {
        console.error('加载统计数据失败:', error);
    }
}

// 加载访客列表
async function loadVisitors(page = 1) {
    try {
        const keyword = document.getElementById('keyword').value;
        const state = document.getElementById('state').value;
        const groupId = document.getElementById('groupId').value;
        const isBlacklist = document.getElementById('isBlacklist').value;
        
        let url = `/api/visitor/list?page=${page}&per_page=20`;
        if (keyword) url += `&keyword=${encodeURIComponent(keyword)}`;
        if (state) url += `&state=${state}`;
        if (groupId) url += `&group_id=${groupId}`;
        if (isBlacklist) url += `&is_blacklist=${isBlacklist}`;
        
        const response = await fetch(url);
        const result = await response.json();
        
        if (result.code === 0) {
            const { list, total, pages } = result.data;
            currentPage = page;
            totalPages = pages;
            
            renderVisitorList(list);
            updatePagination();
        }
    } catch (error) {
        console.error('加载访客列表失败:', error);
        modal.error('加载失败：' + error.message);
    }
}

// 渲染访客列表
function renderVisitorList(list) {
    const tbody = document.getElementById('visitorList');
    
    if (list.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" class="empty-state">
                    <i class="fas fa-users"></i>
                    <p>暂无访客数据</p>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = list.map(visitor => `
        <tr>
            <td>
                <div class="visitor-info">
                    <div class="visitor-avatar ${visitor.is_blacklisted ? 'blacklisted' : ''}" data-name="${visitor.visitor_name.charAt(0).toUpperCase()}">
                        <span class="avatar-placeholder">${visitor.visitor_name.charAt(0).toUpperCase()}</span>
                        ${visitor.avatar && visitor.avatar !== '/static/img/default-avatar.svg' && visitor.avatar.startsWith('http') ? 
                            `<img src="${visitor.avatar}" alt="" onerror="this.style.display='none';">` : ''
                        }
                    </div>
                    <div class="visitor-details">
                        <h4>${escapeHtml(visitor.visitor_name)}</h4>
                        <p>ID: ${visitor.visitor_id.substring(0, 8)}...</p>
                    </div>
                </div>
            </td>
            <td>
                ${visitor.name ? `姓名: ${escapeHtml(visitor.name)}<br>` : ''}
                ${visitor.tel ? `电话: ${escapeHtml(visitor.tel)}` : '-'}
            </td>
            <td>
                IP: ${visitor.ip}<br>
                ${visitor.utm_source ? `来源: ${visitor.utm_source}` : '直接访问'}
            </td>
            <td>
                ${visitor.device || '未知'}<br>
                ${visitor.browser || '未知浏览器'}
            </td>
            <td style="text-align: center;">${visitor.login_times}</td>
            <td>
                <span class="status-badge status-${visitor.state}">
                    ${visitor.state === 'online' ? '在线' : '离线'}
                </span>
                ${visitor.is_blacklisted ? '<br><span class="status-badge" style="background:#fee2e2;color:#991b1b;margin-top:5px;">🚫 黑名单</span>' : ''}
            </td>
            <td>
                <div class="tags">
                    ${visitor.tags && visitor.tags.length ? visitor.tags.map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join('') : '-'}
                </div>
            </td>
            <td style="font-size: 12px;">
                ${visitor.last_visit_time ? new Date(visitor.last_visit_time).toLocaleString('zh-CN') : '-'}
            </td>
            <td>
                <div class="actions">
                    <button class="icon-btn" onclick="viewDetail('${visitor.visitor_id}')" title="查看详情">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="icon-btn" onclick="editVisitor('${visitor.visitor_id}')" title="编辑">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="icon-btn ${visitor.is_blacklisted ? 'success' : 'danger'}" onclick="toggleBlacklist('${visitor.visitor_id}', ${visitor.is_blacklisted})" title="${visitor.is_blacklisted ? '移出黑名单' : '加入黑名单'}">
                        <i class="fas fa-${visitor.is_blacklisted ? 'check' : 'ban'}"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

// 更新分页
function updatePagination() {
    document.getElementById('pageInfo').textContent = `第 ${currentPage} / ${totalPages} 页`;
    document.getElementById('prevBtn').disabled = currentPage === 1;
    document.getElementById('nextBtn').disabled = currentPage === totalPages || totalPages === 0;
}

// 翻页
function changePage(delta) {
    const newPage = currentPage + delta;
    if (newPage >= 1 && newPage <= totalPages) {
        loadVisitors(newPage);
    }
}

// 搜索
function searchVisitors() {
    loadVisitors(1);
}

// 刷新数据
function refreshData() {
    loadStatistics();
    loadVisitors(currentPage);
}

// 查看详情
function viewDetail(visitorId) {
    window.location.href = `/admin/visitor/${visitorId}`;
}

// 编辑访客
async function editVisitor(visitorId) {
    try {
        const response = await fetch(`/api/visitor/detail/${visitorId}`);
        const result = await response.json();
        
        if (result.code === 0) {
            const visitor = result.data;
            
            // 填充表单
            document.getElementById('editVisitorId').value = visitor.visitor_id;
            document.getElementById('editVisitorName').value = visitor.visitor_name;
            document.getElementById('editRealName').value = visitor.name || '';
            document.getElementById('editTel').value = visitor.tel || '';
            document.getElementById('editConnect').value = visitor.connect || '';
            document.getElementById('editTags').value = visitor.tags.join(', ');
            document.getElementById('editGroupId').value = visitor.group_id || '';
            document.getElementById('editComment').value = visitor.comment || '';
            
            // 渲染访客头像和信息
            renderEditVisitorAvatar(visitor);
            
            // 显示模态框
            document.getElementById('editModal').classList.add('show');
        } else {
            modal.error('获取访客信息失败：' + result.msg);
        }
    } catch (error) {
        console.error('编辑访客失败:', error);
        modal.error('操作失败：' + error.message);
    }
}

// 关闭编辑模态框
function closeEditModal() {
    document.getElementById('editModal').classList.remove('show');
    document.getElementById('editForm').reset();
}

// 保存访客信息
async function saveVisitor(event) {
    event.preventDefault();
    
    const visitorId = document.getElementById('editVisitorId').value;
    const data = {
        name: document.getElementById('editRealName').value,
        tel: document.getElementById('editTel').value,
        connect: document.getElementById('editConnect').value,
        tags: document.getElementById('editTags').value,
        group_id: document.getElementById('editGroupId').value || null,
        comment: document.getElementById('editComment').value
    };
    
    try {
        const response = await fetch(`/api/visitor/update/${visitorId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.code === 0) {
            modal.success('保存成功！');
            closeEditModal();
            loadVisitors(currentPage);  // 重新加载列表
        } else {
            modal.error('保存失败：' + result.msg);
        }
    } catch (error) {
        console.error('保存失败:', error);
        modal.error('操作失败：' + error.message);
    }
}

// 打开标签管理模态框
async function openTagModal(visitorId) {
    try {
        const response = await fetch(`/api/visitor/detail/${visitorId}`);
        const result = await response.json();
        
        if (result.code === 0) {
            const visitor = result.data;
            document.getElementById('tagVisitorId').value = visitor.visitor_id;
            
            // 显示当前标签
            const tagsContainer = document.getElementById('currentTags');
            tagsContainer.innerHTML = '';
            
            if (visitor.tags && visitor.tags.length > 0) {
                tagsContainer.classList.remove('empty');
                visitor.tags.forEach(tag => {
                    const tagElement = document.createElement('div');
                    tagElement.className = 'removable-tag';
                    tagElement.innerHTML = `
                        ${tag}
                        <button class="remove-btn" onclick="removeTag('${tag}')" title="删除">
                            <i class="fas fa-times"></i>
                        </button>
                    `;
                    tagsContainer.appendChild(tagElement);
                });
            } else {
                tagsContainer.classList.add('empty');
            }
            
            // 显示模态框
            document.getElementById('tagModal').classList.add('show');
        } else {
            modal.error('获取访客信息失败：' + result.msg);
        }
    } catch (error) {
        console.error('打开标签管理失败:', error);
        modal.error('操作失败：' + error.message);
    }
}

// 关闭标签管理模态框
function closeTagModal() {
    document.getElementById('tagModal').classList.remove('show');
    document.getElementById('newTag').value = '';
}

// 添加标签
async function addTag() {
    const visitorId = document.getElementById('tagVisitorId').value;
    const newTag = document.getElementById('newTag').value.trim();
    
    if (!newTag) {
        modal.warning('请输入标签名称');
        return;
    }
    
    try {
        const response = await fetch(`/api/visitor/tag/add/${visitorId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tag: newTag })
        });
        
        const result = await response.json();
        
        if (result.code === 0) {
            document.getElementById('newTag').value = '';
            openTagModal(visitorId);  // 重新加载标签
            loadVisitors(currentPage);  // 重新加载列表
        } else {
            modal.error('添加标签失败：' + result.msg);
        }
    } catch (error) {
        console.error('添加标签失败:', error);
        modal.error('操作失败：' + error.message);
    }
}

// 移除标签
async function removeTag(tag) {
    const visitorId = document.getElementById('tagVisitorId').value;
    
    try {
        const response = await fetch(`/api/visitor/tag/remove/${visitorId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tag: tag })
        });
        
        const result = await response.json();
        
        if (result.code === 0) {
            openTagModal(visitorId);  // 重新加载标签
            loadVisitors(currentPage);  // 重新加载列表
        } else {
            modal.error('移除标签失败：' + result.msg);
        }
    } catch (error) {
        console.error('移除标签失败:', error);
        modal.error('操作失败：' + error.message);
    }
}

// 切换黑名单
async function toggleBlacklist(visitorId, currentStatus) {
    const action = currentStatus ? '移出' : '加入';
    modal.confirm(`确定要${action}黑名单吗？`, async () => {
        await performToggleBlacklist(visitorId, currentStatus);
    });
}

async function performToggleBlacklist(visitorId, currentStatus) {
    
    try {
        const response = await fetch(`/api/visitor/blacklist/${visitorId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ is_blacklist: currentStatus ? 0 : 1 })
        });
        
        const result = await response.json();
        if (result.code === 0) {
            modal.success(result.msg);
            loadVisitors(currentPage);
        } else {
            modal.error('操作失败：' + result.msg);
        }
    } catch (error) {
        modal.error('操作失败：' + error.message);
    }
}

// 导出访客
function exportVisitors() {
    // TODO: 实现导出功能
    modal.info('导出功能开发中...', '功能提示');
}

// HTML转义
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text ? String(text).replace(/[&<>"']/g, m => map[m]) : '';
}

// 渲染编辑弹窗中的访客头像
function renderEditVisitorAvatar(visitor) {
    const avatarDiv = document.getElementById('editVisitorAvatar');
    const displayNameEl = document.getElementById('editVisitorDisplayName');
    const statusEl = document.getElementById('editVisitorStatus');
    
    // 设置显示名称
    displayNameEl.textContent = visitor.visitor_name;
    
    // 设置在线状态
    const isOnline = visitor.state === 'online';
    statusEl.className = `visitor-status ${isOnline ? 'online' : 'offline'}`;
    statusEl.querySelector('.status-text').textContent = isOnline ? '在线' : '离线';
    
    // 设置黑名单状态
    if (visitor.is_blacklisted) {
        avatarDiv.classList.add('blacklisted');
    } else {
        avatarDiv.classList.remove('blacklisted');
    }
    
    // 渲染头像
    const firstLetter = visitor.visitor_name.charAt(0).toUpperCase();
    
    // 始终渲染placeholder作为背景
    avatarDiv.innerHTML = `<span class="avatar-placeholder">${firstLetter}</span>`;
    
    // 如果有真实头像，添加img覆盖在上面
    if (visitor.avatar && visitor.avatar !== '/static/img/default-avatar.svg' && visitor.avatar.startsWith('http')) {
        avatarDiv.innerHTML += `<img src="${visitor.avatar}" alt="" onerror="this.style.display='none';">`;
    }
}

// 页面加载
window.addEventListener('DOMContentLoaded', () => {
    loadStatistics();
    loadVisitors(1);
    
    // 加载分组列表
    fetch('/api/visitor/group/list')
        .then(res => res.json())
        .then(result => {
            if (result.code === 0) {
                const select = document.getElementById('groupId');
                const editSelect = document.getElementById('editGroupId');
                
                result.data.forEach(group => {
                    const option1 = document.createElement('option');
                    option1.value = group.id;
                    option1.textContent = group.group_name;
                    select.appendChild(option1);
                    
                    const option2 = document.createElement('option');
                    option2.value = group.id;
                    option2.textContent = group.group_name;
                    editSelect.appendChild(option2);
                });
            }
        });
});

