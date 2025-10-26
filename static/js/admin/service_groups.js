/**
 * 客服分组管理页面 - 脚本
 */

// 全局变量
let groups = [];

// 页面加载
document.addEventListener('DOMContentLoaded', function() {
    loadGroups();
    
    // 添加分组按钮事件
    document.querySelector('.btn-primary').addEventListener('click', showAddGroupModal);
});

// 加载分组列表
async function loadGroups() {
    try {
        const response = await fetch('/api/service/groups');
        const result = await response.json();
        
        if (result.code === 0) {
            groups = result.data;
            renderGroups();
        } else {
            console.error('加载分组失败:', result.msg);
            showEmptyState();
        }
    } catch (error) {
        console.error('加载分组失败:', error);
        showEmptyState();
    }
}

// 渲染分组列表
function renderGroups() {
    const container = document.getElementById('groupsList');
    
    if (groups.length === 0) {
        showEmptyState();
        return;
    }
    
    container.innerHTML = groups.map(group => `
        <div class="group-card">
            <div class="group-header" style="border-left: 4px solid ${group.bgcolor || 'var(--primary-color)'}; padding-left: 12px; margin-bottom: 16px;">
                <h3 class="group-name">${group.group_name}</h3>
            </div>
            
            <div class="group-info">
                <div class="info-row">
                    <i class="fas fa-users"></i>
                    <span>成员数: ${group.member_count || 0}</span>
                </div>
                <div class="info-row">
                    <i class="fas fa-clock"></i>
                    <span>创建时间: ${formatDate(group.add_time)}</span>
                </div>
            </div>
            
            <div class="group-actions">
                <button class="btn btn-primary btn-sm" onclick="editGroup(${group.id})">
                    <i class="fas fa-edit"></i> 编辑
                </button>
                <button class="btn btn-secondary btn-sm" onclick="viewMembers(${group.id})">
                    <i class="fas fa-users"></i> 查看成员
                </button>
                <button class="btn btn-danger btn-sm" onclick="deleteGroup(${group.id})">
                    <i class="fas fa-trash"></i> 删除
                </button>
            </div>
        </div>
    `).join('');
}

// 显示空状态
function showEmptyState() {
    const container = document.getElementById('groupsList');
    container.innerHTML = `
        <div class="empty-state">
            <i class="fas fa-layer-group"></i>
            <p>暂无分组，点击"添加分组"创建</p>
        </div>
    `;
}

// 显示添加分组模态框
function showAddGroupModal() {
    const modalHtml = `
        <div class="modal" id="groupModal">
            <div class="modal-content">
                <div class="modal-header">
                    <h3>添加分组</h3>
                    <button class="modal-close" onclick="closeGroupModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="groupForm" onsubmit="saveGroup(event)">
                        <input type="hidden" id="groupId">
                        
                        <div class="form-group">
                            <label>分组名称 <span class="required">*</span></label>
                            <input type="text" id="groupName" class="form-control" required placeholder="例如：售前客服组">
                        </div>
                        
                        <div class="form-group">
                            <label>分组颜色</label>
                            <input type="color" id="groupColor" class="form-control" value="var(--primary-color)">
                        </div>
                        
                        <div class="form-group">
                            <label>描述</label>
                            <textarea id="groupDesc" class="form-control" rows="3" placeholder="分组描述（可选）"></textarea>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" onclick="closeGroupModal()">取消</button>
                    <button type="button" class="btn btn-primary" onclick="document.getElementById('groupForm').dispatchEvent(new Event('submit'))">保存</button>
                </div>
            </div>
        </div>
    `;
    
    // 添加到页面
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    document.getElementById('groupModal').classList.add('show');
}

// 编辑分组
function editGroup(groupId) {
    const group = groups.find(g => g.id === groupId);
    if (!group) return;
    
    showAddGroupModal();
    
    // 更新标题和填充数据
    document.querySelector('#groupModal .modal-header h3').textContent = '编辑分组';
    document.getElementById('groupId').value = group.id;
    document.getElementById('groupName').value = group.group_name;
    document.getElementById('groupColor').value = group.bgcolor || 'var(--primary-color)';
    if (group.description) {
        document.getElementById('groupDesc').value = group.description;
    }
}

// 保存分组
async function saveGroup(event) {
    event.preventDefault();
    
    const groupId = document.getElementById('groupId').value;
    const groupName = document.getElementById('groupName').value;
    const bgcolor = document.getElementById('groupColor').value;
    const description = document.getElementById('groupDesc').value;
    
    try {
        let url, method;
        if (groupId) {
            // 更新
            url = `/api/service/groups/${groupId}`;
            method = 'PUT';
        } else {
            // 创建
            url = '/api/service/groups';
            method = 'POST';
        }
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                group_name: groupName,
                bgcolor: bgcolor,
                description: description
            })
        });
        
        const result = await response.json();
        
        if (result.code === 0) {
            modal.success(groupId ? '更新成功' : '创建成功');
            closeGroupModal();
            loadGroups();
        } else {
            modal.error('操作失败: ' + result.msg);
        }
    } catch (error) {
        console.error('保存分组失败:', error);
        modal.error('操作失败，请检查网络连接');
    }
}

// 删除分组
async function deleteGroup(groupId) {
    modal.confirm('确定要删除这个分组吗？分组内的客服将移至未分组。', async () => {
        await performDeleteGroup(groupId);
    });
}

async function performDeleteGroup(groupId) {
    
    try {
        const response = await fetch(`/api/service/groups/${groupId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.code === 0) {
            modal.success('删除成功');
            loadGroups();
        } else {
            modal.error('删除失败: ' + result.msg);
        }
    } catch (error) {
        console.error('删除分组失败:', error);
        modal.error('删除失败，请检查网络连接');
    }
}

// 查看成员
function viewMembers(groupId) {
    // 跳转到客服管理页面并过滤该分组
    window.location.href = `/admin/services?group_id=${groupId}`;
}

// 关闭模态框
function closeGroupModal() {
    const modal = document.getElementById('groupModal');
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => modal.remove(), 300);
    }
}

// 格式化日期
function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN');
}

// 添加样式
const style = document.createElement('style');
style.textContent = `
    .modal {
        display: none;
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.5);
        z-index: 1000;
        align-items: center;
        justify-content: center;
    }
    
    .modal.show {
        display: flex;
    }
    
    .modal-content {
        background: white;
        border-radius: 12px;
        width: 90%;
        max-width: 500px;
        max-height: 90vh;
        overflow-y: auto;
    }
    
    .modal-header {
        padding: 20px 24px;
        border-bottom: 1px solid #e5e7eb;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .modal-header h3 {
        margin: 0;
        font-size: 20px;
        font-weight: 600;
    }
    
    .modal-close {
        background: none;
        border: none;
        font-size: 24px;
        cursor: pointer;
        color: #6b7280;
    }
    
    .modal-body {
        padding: 24px;
    }
    
    .modal-footer {
        padding: 16px 24px;
        border-top: 1px solid #e5e7eb;
        display: flex;
        justify-content: flex-end;
        gap: 12px;
    }
    
    .form-group {
        margin-bottom: 20px;
    }
    
    .form-group label {
        display: block;
        margin-bottom: 8px;
        font-weight: 500;
        color: #374151;
    }
    
    .required {
        color: #ef4444;
    }
    
    .form-control {
        width: 100%;
        padding: 10px 12px;
        border: 1px solid #d1d5db;
        border-radius: 6px;
        font-size: 14px;
    }
    
    .form-control:focus {
        outline: none;
        border-color: var(--primary-color);
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    textarea.form-control {
        resize: vertical;
    }
    
    .btn-sm {
        padding: 6px 12px;
        font-size: 13px;
    }
    
    .btn-danger {
        background: #ef4444;
        color: white;
    }
    
    .info-row {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
        color: #6b7280;
        font-size: 14px;
    }
    
    .info-row i {
        width: 16px;
        text-align: center;
    }
`;
document.head.appendChild(style);

