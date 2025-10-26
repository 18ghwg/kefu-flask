/**
 * 客服管理页面 - 脚本
 */

// 全局变量
let currentPage = 1;
let totalPages = 1;
let deleteServiceId = null;
let isEditMode = false;
let serviceGroups = []; // 存储所有客服分组

// 页面加载
document.addEventListener('DOMContentLoaded', async function() {
    await loadServiceGroups(); // 提前加载分组列表
    loadStatistics();
    loadServices();
});

// 加载客服分组列表
async function loadServiceGroups() {
    try {
        const response = await fetch('/api/service/groups');
        const result = await response.json();
        
        if (result.code === 0) {
            serviceGroups = result.data || [];
            console.log('客服分组列表加载成功:', serviceGroups);
        } else {
            console.error('加载客服分组失败:', result.msg);
        }
    } catch (error) {
        console.error('加载客服分组异常:', error);
    }
}

// 渲染分组下拉选项
function renderGroupOptions(selectedId = '0') {
    const groupSelect = document.getElementById('groupId');
    
    // 清空现有选项（保留"未分组"）
    groupSelect.innerHTML = '<option value="0">未分组</option>';
    
    // 添加分组选项
    serviceGroups.forEach(group => {
        const option = document.createElement('option');
        option.value = group.id;
        option.textContent = `${group.group_name}${group.description ? ' - ' + group.description : ''}`;
        
        // 设置选中状态
        if (group.id == selectedId) {
            option.selected = true;
        }
        
        groupSelect.appendChild(option);
    });
}

// 加载统计数据
async function loadStatistics() {
    try {
        const response = await fetch('/api/admin/services?page=1&per_page=1000');
        const result = await response.json();
        
        if (result.code === 0) {
            const services = result.data.services;
            const total = services.length;
            const online = services.filter(s => s.state === 'online').length;
            const busy = services.filter(s => s.state === 'busy').length;
            const offline = services.filter(s => s.state === 'offline').length;
            
            document.getElementById('totalServices').textContent = total;
            document.getElementById('onlineServices').textContent = online;
            document.getElementById('busyServices').textContent = busy;
            document.getElementById('offlineServices').textContent = offline;
        }
    } catch (error) {
        console.error('加载统计数据失败:', error);
    }
}

// 加载客服列表
async function loadServices(page = 1) {
    try {
        const stateFilter = document.getElementById('stateFilter').value;
        const levelFilter = document.getElementById('levelFilter').value;
        const keyword = document.getElementById('searchKeyword').value;
        
        const params = new URLSearchParams({
            page: page,
            per_page: 20
        });
        
        // 这里简化处理，实际需要后端支持筛选
        const response = await fetch(`/api/admin/services?${params}`);
        const result = await response.json();
        
        if (result.code === 0) {
            currentPage = page;
            totalPages = Math.ceil(result.data.total / 20);
            renderServices(result.data.services, stateFilter, levelFilter, keyword);
            updatePagination();
        }
    } catch (error) {
        console.error('加载客服列表失败:', error);
    }
}

// 渲染客服列表
function renderServices(services, stateFilter, levelFilter, keyword) {
    const tbody = document.getElementById('servicesTableBody');
    
    // 客户端筛选
    let filteredServices = services;
    if (stateFilter) {
        filteredServices = filteredServices.filter(s => s.state === stateFilter);
    }
    if (levelFilter) {
        filteredServices = filteredServices.filter(s => s.level === levelFilter);
    }
    if (keyword) {
        filteredServices = filteredServices.filter(s => 
            s.user_name.includes(keyword) || s.nick_name.includes(keyword)
        );
    }
    
    if (filteredServices.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10" style="text-align: center; padding: 40px;">暂无数据</td></tr>';
        return;
    }
    
    // 获取当前域名
    const baseUrl = window.location.origin;
    
    tbody.innerHTML = filteredServices.map(service => {
        // 生成专属链接
        const personalLink = `${baseUrl}/chat?business_id=${service.business_id || 1}&special=${service.service_id}`;
        
        return `
        <tr>
            <td>
                <div class="service-avatar">
                    ${service.nick_name.charAt(0).toUpperCase()}
                </div>
            </td>
            <td>${service.user_name}</td>
            <td>${service.nick_name}</td>
            <td>
                <span class="level-badge level-${service.level}">
                    ${getLevelText(service.level)}
                </span>
            </td>
            <td>
                <span class="status-badge status-${service.state}">
                    ${getStateText(service.state)}
                </span>
            </td>
            <td>${service.phone || '-'}</td>
            <td>${service.email || '-'}</td>
            <td>
                <button class="action-btn copy-link" onclick="copyPersonalLink('${personalLink}')" title="复制专属链接">
                    <i class="fas fa-link"></i> 复制链接
                </button>
            </td>
            <td>${formatDate(service.create_time)}</td>
            <td>
                <button class="action-btn edit" onclick="editService('${service.service_id}')">
                    <i class="fas fa-edit"></i> 编辑
                </button>
                <button class="action-btn delete" onclick="deleteService('${service.service_id}')">
                    <i class="fas fa-trash"></i> 删除
                </button>
            </td>
        </tr>
        `;
    }).join('');
}

// 获取权限文本
function getLevelText(level) {
    const map = {
        'super_manager': '超级管理员',
        'manager': '管理员',
        'service': '客服'
    };
    return map[level] || level;
}

// 获取状态文本
function getStateText(state) {
    const map = {
        'online': '在线',
        'busy': '忙碌',
        'offline': '离线'
    };
    return map[state] || state;
}

// 格式化日期
function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN');
}

// 搜索客服
function searchServices() {
    loadServices(1);
}

// 重置筛选
function resetFilters() {
    document.getElementById('stateFilter').value = '';
    document.getElementById('levelFilter').value = '';
    document.getElementById('searchKeyword').value = '';
    loadServices(1);
}

// 打开添加模态框
async function openAddModal() {
    isEditMode = false;
    document.getElementById('modalTitle').textContent = '添加客服';
    document.getElementById('serviceForm').reset();
    document.getElementById('serviceId').value = '';
    document.getElementById('passwordGroup').style.display = 'block';
    document.getElementById('password').required = true;
    
    // 加载并渲染分组选项
    await loadServiceGroups(); // 确保分组列表是最新的
    renderGroupOptions('0'); // 默认选中"未分组"
    
    document.getElementById('serviceModal').classList.add('show');
}

// 编辑客服
async function editService(serviceId) {
    try {
        isEditMode = true;
        document.getElementById('modalTitle').textContent = '编辑客服';
        
        // 获取客服详情
        const response = await fetch(`/api/admin/services?page=1&per_page=1000`);
        const result = await response.json();
        
        if (result.code === 0) {
            const service = result.data.services.find(s => s.service_id === serviceId);
            if (service) {
                document.getElementById('serviceId').value = service.service_id;
                document.getElementById('userName').value = service.user_name;
                document.getElementById('nickName').value = service.nick_name;
                document.getElementById('level').value = service.level;
                document.getElementById('phone').value = service.phone || '';
                document.getElementById('email').value = service.email || '';
                
                // 加载并渲染分组选项，设置当前分组为选中状态
                await loadServiceGroups();
                renderGroupOptions(service.group_id || '0');
                
                document.getElementById('password').required = false;
                document.getElementById('serviceModal').classList.add('show');
            }
        }
    } catch (error) {
        console.error('加载客服信息失败:', error);
        modal.error('加载客服信息失败，请重试');
    }
}

// 保存客服
async function saveService() {
    try {
        const serviceId = document.getElementById('serviceId').value;
        const userName = document.getElementById('userName').value;
        const nickName = document.getElementById('nickName').value;
        const password = document.getElementById('password').value;
        const level = document.getElementById('level').value;
        const phone = document.getElementById('phone').value;
        const email = document.getElementById('email').value;
        const groupId = document.getElementById('groupId').value;
        
        // 验证必填字段
        if (!userName || !nickName || !level) {
            modal.warning('请填写必填字段');
            return;
        }
        
        if (!isEditMode && !password) {
            modal.warning('请输入密码');
            return;
        }
        
        const data = {
            user_name: userName,
            nick_name: nickName,
            level: level,
            phone: phone,
            email: email,
            group_id: groupId
        };
        
        if (password) {
            data.password = password;
        }
        
        let url, method;
        if (isEditMode) {
            url = `/api/admin/services/${serviceId}`;
            method = 'PUT';
        } else {
            url = '/api/admin/services';
            method = 'POST';
        }
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.code === 0) {
            modal.success(isEditMode ? '编辑成功' : '添加成功');
            closeServiceModal();
            loadStatistics();
            loadServices(currentPage);
        } else {
            modal.error('操作失败: ' + result.msg);
        }
    } catch (error) {
        console.error('保存客服失败:', error);
        modal.error('保存失败，请检查网络连接');
    }
}

// 删除客服
function deleteService(serviceId) {
    deleteServiceId = serviceId;
    document.getElementById('deleteModal').classList.add('show');
}

// 确认删除
async function confirmDelete() {
    try {
        const response = await fetch(`/api/admin/services/${deleteServiceId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.code === 0) {
            modal.success('删除成功');
            closeDeleteModal();
            loadStatistics();
            loadServices(currentPage);
        } else {
            modal.error('删除失败: ' + result.msg);
        }
    } catch (error) {
        console.error('删除客服失败:', error);
        modal.error('删除失败，请检查网络连接');
    }
}

// 关闭模态框
function closeServiceModal() {
    document.getElementById('serviceModal').classList.remove('show');
}

function closeDeleteModal() {
    document.getElementById('deleteModal').classList.remove('show');
    deleteServiceId = null;
}

// 分页
function changePage(delta) {
    const newPage = currentPage + delta;
    if (newPage >= 1 && newPage <= totalPages) {
        loadServices(newPage);
    }
}

// 更新分页
function updatePagination() {
    document.getElementById('prevBtn').disabled = currentPage <= 1;
    document.getElementById('nextBtn').disabled = currentPage >= totalPages;
    document.getElementById('pageInfo').textContent = `第 ${currentPage} / ${totalPages} 页`;
}

// 点击模态框外部关闭
window.onclick = function(event) {
    const serviceModal = document.getElementById('serviceModal');
    const deleteModal = document.getElementById('deleteModal');
    
    if (event.target === serviceModal) {
        closeServiceModal();
    }
    if (event.target === deleteModal) {
        closeDeleteModal();
    }
}

// 🆕 复制专属链接到剪贴板
async function copyPersonalLink(link) {
    try {
        await navigator.clipboard.writeText(link);
        
        // 显示成功提示
        showToast('专属链接已复制到剪贴板！', 'success');
    } catch (err) {
        // 降级方案：使用传统方法复制
        const textArea = document.createElement('textarea');
        textArea.value = link;
        textArea.style.position = 'fixed';
        textArea.style.opacity = '0';
        document.body.appendChild(textArea);
        textArea.select();
        
        try {
            document.execCommand('copy');
            showToast('专属链接已复制到剪贴板！', 'success');
        } catch (err2) {
            showToast('复制失败，请手动复制', 'error');
            console.error('复制失败:', err2);
        } finally {
            document.body.removeChild(textArea);
        }
    }
}

// 显示提示消息
function showToast(message, type = 'info') {
    // 创建toast元素
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
        <span>${message}</span>
    `;
    
    // 添加到页面
    document.body.appendChild(toast);
    
    // 触发动画
    setTimeout(() => toast.classList.add('show'), 10);
    
    // 3秒后移除
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => document.body.removeChild(toast), 300);
    }, 3000);
}

