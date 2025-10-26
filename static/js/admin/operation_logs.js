/**
 * 操作日志管理 - JavaScript
 */

let currentPage = 1;
let totalPages = 1;
let currentFilters = {};

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', () => {
    loadLogs();
});

/**
 * 加载操作日志列表
 */
async function loadLogs(page = 1) {
    currentPage = page;
    const queryParams = new URLSearchParams({
        page: currentPage,
        limit: 10,
        ...currentFilters
    }).toString();
    
    try {
        const response = await fetch(`/api/operation-log/list?${queryParams}`);
        const result = await response.json();
        
        if (result.code === 0) {
            renderLogList(result.data.list);
            totalPages = result.data.pages;
            updatePagination();
        } else {
            modal.error('加载日志失败: ' + result.msg);
            renderLogList([]);
        }
    } catch (error) {
        console.error('Error loading logs:', error);
        modal.error('加载日志失败: ' + error.message);
        renderLogList([]);
    }
}

/**
 * 渲染日志列表
 */
function renderLogList(logs) {
    const tbody = document.getElementById('logList');
    tbody.innerHTML = '';
    
    // 防御性检查：确保logs是数组
    if (!logs || !Array.isArray(logs) || logs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="10" class="empty-state"><i class="fas fa-box-open"></i><p>暂无操作日志</p></td></tr>`;
        return;
    }
    
    logs.forEach(log => {
        // 防御性检查：确保description存在
        const description = log.description || '';
        const descriptionPreview = description.substring(0, 50) + (description.length > 50 ? '...' : '');
        
        const row = `
            <tr>
                <td>${log.id || '-'}</td>
                <td>${log.operator_name || '-'}</td>
                <td>${log.operator_type || '-'}</td>
                <td>${log.module || '-'}</td>
                <td>${log.action || '-'}</td>
                <td>${descriptionPreview}</td>
                <td>${log.ip || '-'}</td>
                <td class="${log.result === 'success' ? 'log-result success' : 'log-result fail'}">${log.result === 'success' ? '成功' : '失败'}</td>
                <td>${log.created_at || '-'}</td>
                <td class="actions">
                    <button class="btn-info" onclick="showLogDetail(${log.id})">详情</button>
                    <button class="btn-danger" onclick="deleteLog(${log.id})">删除</button>
                </td>
            </tr>
        `;
        tbody.innerHTML += row;
    });
}

/**
 * 更新分页信息
 */
function updatePagination() {
    document.getElementById('pageInfo').textContent = `第 ${currentPage} / ${totalPages} 页`;
    document.getElementById('prevBtn').disabled = currentPage === 1;
    document.getElementById('nextBtn').disabled = currentPage === totalPages || totalPages === 0;
}

/**
 * 切换页面
 */
function changePage(delta) {
    const newPage = currentPage + delta;
    if (newPage >= 1 && newPage <= totalPages) {
        loadLogs(newPage);
    }
}

/**
 * 搜索日志
 */
function searchLogs() {
    currentFilters = {
        operator_name: document.getElementById('operatorNameInput').value,
        module: document.getElementById('moduleSelect').value,
        action: document.getElementById('actionSelect').value,
        start_time: document.getElementById('startDateInput').value,
        end_time: document.getElementById('endDateInput').value
    };
    loadLogs(1);
}

/**
 * 重置搜索条件
 */
function resetSearch() {
    document.getElementById('operatorNameInput').value = '';
    document.getElementById('moduleSelect').value = '';
    document.getElementById('actionSelect').value = '';
    document.getElementById('startDateInput').value = '';
    document.getElementById('endDateInput').value = '';
    currentFilters = {};
    loadLogs(1);
}

/**
 * 显示日志详情
 */
async function showLogDetail(logId) {
    try {
        const response = await fetch(`/api/operation-log/get/${logId}`);
        const result = await response.json();
        
        if (result.code === 0) {
            const log = result.data;
            document.getElementById('detailId').textContent = log.id;
            document.getElementById('detailBusinessId').textContent = log.business_id;
            document.getElementById('detailOperatorName').textContent = log.operator_name;
            document.getElementById('detailOperatorType').textContent = log.operator_type;
            document.getElementById('detailOperatorId').textContent = log.operator_id;
            document.getElementById('detailModule').textContent = log.module;
            document.getElementById('detailAction').textContent = log.action;
            document.getElementById('detailDescription').textContent = log.description;
            document.getElementById('detailMethod').textContent = log.method;
            document.getElementById('detailPath').textContent = log.path;
            document.getElementById('detailIp').textContent = log.ip;
            document.getElementById('detailUserAgent').textContent = log.user_agent;
            document.getElementById('detailTargetId').textContent = log.target_id;
            document.getElementById('detailTargetType').textContent = log.target_type;
            document.getElementById('detailParams').textContent = log.params ? JSON.stringify(JSON.parse(log.params), null, 2) : '无';
            document.getElementById('detailResult').textContent = log.result === 'success' ? '成功' : '失败';
            document.getElementById('detailResult').className = `log-result ${log.result}`;
            document.getElementById('detailErrorMsg').textContent = log.error_msg || '无';
            document.getElementById('detailCreatedAt').textContent = log.created_at;
            
            document.getElementById('logDetailModal').style.display = 'flex';
        } else {
            modal.error('获取日志详情失败: ' + result.msg);
        }
    } catch (error) {
        console.error('Error fetching log detail:', error);
        modal.error('获取日志详情失败: ' + error.message);
    }
}

/**
 * 关闭详情模态框
 */
function closeDetailModal() {
    document.getElementById('logDetailModal').style.display = 'none';
}

/**
 * 删除日志
 */
async function deleteLog(logId) {
    modal.confirm({
        title: '确认删除',
        message: '确定要删除这条操作日志吗？',
        onConfirm: async () => {
            try {
                const response = await fetch(`/api/operation-log/delete/${logId}`, {
                    method: 'DELETE'
                });
                const result = await response.json();
                
                if (result.code === 0) {
                    modal.success('删除成功！');
                    loadLogs(currentPage);
                } else {
                    modal.error('删除失败: ' + result.msg);
                }
            } catch (error) {
                console.error('Error deleting log:', error);
                modal.error('删除失败: ' + error.message);
            }
        }
    });
}

// 监听点击模态框外部关闭
window.addEventListener('click', (event) => {
    const modal = document.getElementById('logDetailModal');
    if (event.target === modal) {
        closeDetailModal();
    }
});

