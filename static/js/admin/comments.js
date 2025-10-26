/**
 * 评价管理页面 - 脚本
 */

// 全局变量
let currentPage = 1;
let totalPages = 1;
let deleteCommentId = null;

// 页面加载完成
document.addEventListener('DOMContentLoaded', function() {
    loadStatistics();
    loadComments();
    loadRanking();
    loadServiceList();
});

// 加载统计数据
async function loadStatistics() {
    try {
        const days = 7;
        // ✅ 调用新的评价统计API
        const response = await fetch(`/api/rating/statistics?days=${days}`);
        const result = await response.json();
        
        console.log('📊 统计数据:', result);
        
        if (result.code === 0 && result.data) {
            const data = result.data;
            
            // 更新统计卡片
            document.getElementById('totalComments').textContent = data.total_count || 0;
            document.getElementById('avgScore').textContent = (data.avg_score || 0).toFixed(1);
            document.getElementById('satisfaction').textContent = (data.satisfaction_rate || 0).toFixed(1) + '%';
            document.getElementById('fiveStarCount').textContent = data.level_distribution['5'] || 0;
            
            // 渲染评分分布
            renderLevelDistribution(data.level_distribution, data.total_count);
            
            console.log('✅ 统计数据加载成功');
        } else {
            console.error('❌ 统计数据格式错误:', result);
            // 显示默认值
            document.getElementById('totalComments').textContent = '0';
            document.getElementById('avgScore').textContent = '0.0';
            document.getElementById('satisfaction').textContent = '0%';
            document.getElementById('fiveStarCount').textContent = '0';
        }
    } catch (error) {
        console.error('❌ 加载统计数据失败:', error);
        // 显示默认值
        document.getElementById('totalComments').textContent = '0';
        document.getElementById('avgScore').textContent = '0.0';
        document.getElementById('satisfaction').textContent = '0%';
        document.getElementById('fiveStarCount').textContent = '0';
    }
}

// 渲染评分分布
function renderLevelDistribution(distribution, total) {
    const container = document.getElementById('levelDistribution');
    container.innerHTML = '';
    
    const levels = ['5', '4', '3', '2', '1'];
    const colors = [
        'linear-gradient(90deg, #10b981 0%, #059669 100%)',
        'linear-gradient(90deg, #3b82f6 0%, #2563eb 100%)',
        'linear-gradient(90deg, #f59e0b 0%, #d97706 100%)',
        'linear-gradient(90deg, #f97316 0%, #ea580c 100%)',
        'linear-gradient(90deg, #ef4444 0%, #dc2626 100%)'
    ];
    
    levels.forEach((level, index) => {
        const count = distribution[level] || 0;
        const percentage = total > 0 ? (count / total * 100).toFixed(1) : 0;
        
        const barHtml = `
            <div class="level-bar">
                <div class="level-label">${'⭐'.repeat(parseInt(level))} (${level}星)</div>
                <div class="level-progress">
                    <div class="level-fill" style="width: ${percentage}%; background: ${colors[index]};">
                        ${percentage}%
                    </div>
                </div>
                <div class="level-count">${count}条</div>
            </div>
        `;
        
        container.innerHTML += barHtml;
    });
}

// 加载客服列表（用于筛选）
async function loadServiceList() {
    try {
        const response = await fetch('/api/service/list?per_page=100');
        const result = await response.json();
        
        if (result.code === 0 && Array.isArray(result.data)) {
            const select = document.getElementById('serviceId');
            select.innerHTML = '<option value="">全部客服</option>'; // 清空并添加默认选项
            result.data.forEach(service => {
                const option = document.createElement('option');
                option.value = service.service_id;
                option.textContent = service.nick_name;
                select.appendChild(option);
            });
            console.log('✅ 客服列表加载成功，共', result.data.length, '个客服');
        } else {
            console.error('❌ API返回数据格式错误:', result);
        }
    } catch (error) {
        console.error('❌ 加载客服列表失败:', error);
    }
}

// 加载评价列表
async function loadComments(page = 1) {
    try {
        // 获取筛选条件
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        const serviceId = document.getElementById('serviceId').value;
        const level = document.getElementById('level').value;
        
        // 构建查询参数
        const params = new URLSearchParams({
            page: page,
            per_page: 10
        });
        
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
        if (serviceId) params.append('service_id', serviceId);
        if (level) params.append('level', level);
        
        // ✅ 调用新的客服评价API
        const response = await fetch(`/api/rating/list?${params}`);
        const result = await response.json();
        
        console.log('📋 评价数据:', result);
        
        if (result.code === 0 && result.data) {
            currentPage = page;
            totalPages = result.data.pages || 1;
            // ✅ 使用 ratings 而不是 list
            const ratings = result.data.ratings || [];
            renderComments(ratings);
            updatePagination();
            console.log('✅ 评价列表加载成功，共', ratings.length, '条');
        } else {
            console.error('❌ API返回错误:', result);
            showEmptyState();
        }
    } catch (error) {
        console.error('❌ 加载评价列表失败:', error);
        showEmptyState();
    }
}

// 渲染评价列表
function renderComments(comments) {
    const container = document.getElementById('commentsList');
    
    if (!comments || comments.length === 0) {
        showEmptyState();
        return;
    }
    
    container.innerHTML = comments.map(comment => `
        <div class="comment-item">
            <div class="comment-header">
                <div class="comment-user-info">
                    <div class="user-avatar">
                        ${(comment.visitor_name || '访客').charAt(0).toUpperCase()}
                    </div>
                    <div class="user-details">
                        <h4>${comment.visitor_name || '匿名访客'}</h4>
                        <div class="user-meta">
                            客服: ${comment.service_name || '未知'} | 
                            访客ID: ${comment.visitor_id || '-'}
                        </div>
                    </div>
                </div>
                <div class="comment-rating">
                    <div class="stars">${'⭐'.repeat(comment.rating || 0)}</div>
                    <div class="rating-text">${comment.rating || 0}星</div>
                </div>
            </div>
            
            ${comment.comment ? `
                <div class="comment-content">
                    ${comment.comment}
                </div>
            ` : ''}
            
            <div class="comment-footer">
                <div class="comment-time">
                    <i class="fas fa-clock"></i>
                    ${formatTime(comment.created_at)}
                </div>
                <div class="comment-actions">
                    <button class="icon-btn" onclick="viewCommentDetail(${comment.id})" title="查看详情">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="icon-btn danger" onclick="deleteComment(${comment.id})" title="删除">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        </div>
    `).join('');
}

// 显示空状态
function showEmptyState() {
    const container = document.getElementById('commentsList');
    container.innerHTML = `
        <div class="empty-state">
            <i class="fas fa-comments"></i>
            <p>暂无评价数据</p>
        </div>
    `;
}

// 加载客服排行榜
async function loadRanking() {
    try {
        // ✅ 调用新的评价排行榜API
        const response = await fetch('/api/rating/ranking?days=7&limit=10');
        const result = await response.json();
        
        console.log('🏆 排行榜数据:', result);
        
        if (result.code === 0 && Array.isArray(result.data)) {
            renderRanking(result.data);
            console.log('✅ 排行榜加载成功，共', result.data.length, '名客服');
        } else {
            console.error('❌ 排行榜数据格式错误:', result);
        }
    } catch (error) {
        console.error('❌ 加载排行榜失败:', error);
    }
}

// 渲染排行榜
function renderRanking(ranking) {
    const container = document.getElementById('rankingList');
    
    if (!ranking || ranking.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>暂无排行数据</p></div>';
        return;
    }
    
    const positionClasses = ['gold', 'silver', 'bronze'];
    
    container.innerHTML = ranking.map((item, index) => {
        const positionClass = index < 3 ? positionClasses[index] : 'normal';
        return `
            <div class="ranking-item">
                <div class="ranking-position ${positionClass}">
                    ${index + 1}
                </div>
                <div class="ranking-info">
                    <div class="ranking-name">${item.service_name}</div>
                    <div class="ranking-score">
                        ${item.total_count}条评价 | 满意度 ${item.satisfaction_rate}%
                    </div>
                </div>
                <div class="ranking-stars">
                    ${item.avg_score.toFixed(1)} ⭐
                </div>
            </div>
        `;
    }).join('');
}

// 搜索评价
function searchComments() {
    loadComments(1);
}

// 重置筛选条件
function resetFilters() {
    document.getElementById('startDate').value = '';
    document.getElementById('endDate').value = '';
    document.getElementById('serviceId').value = '';
    document.getElementById('level').value = '';
    loadComments(1);
}

// 刷新数据
function refreshData() {
    loadStatistics();
    loadComments(currentPage);
    loadRanking();
}

// 删除评价
function deleteComment(id) {
    deleteCommentId = id;
    document.getElementById('deleteModal').classList.add('show');
}

// 确认删除
async function confirmDelete() {
    if (!deleteCommentId) return;
    
    try {
        const response = await fetch(`/api/comment/delete/${deleteCommentId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.code === 0) {
            modal.success('删除成功');
            closeDeleteModal();
            refreshData();
        } else {
            modal.error('删除失败: ' + result.msg);
        }
    } catch (error) {
        console.error('删除评价失败:', error);
        modal.error('删除失败，请检查网络连接');
    }
}

// 关闭删除模态框
function closeDeleteModal() {
    document.getElementById('deleteModal').classList.remove('show');
    deleteCommentId = null;
}

// 查看评价详情（预留）
function viewCommentDetail(id) {
    modal.info('查看评价详情功能开发中...', '功能提示');
    // TODO: 实现详情查看
}

// 分页
function changePage(delta) {
    const newPage = currentPage + delta;
    if (newPage >= 1 && newPage <= totalPages) {
        loadComments(newPage);
    }
}

// 更新分页按钮状态
function updatePagination() {
    document.getElementById('prevBtn').disabled = currentPage <= 1;
    document.getElementById('nextBtn').disabled = currentPage >= totalPages;
    document.getElementById('pageInfo').textContent = `第 ${currentPage} / ${totalPages} 页`;
}

// 格式化时间
function formatTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    // 1分钟内
    if (diff < 60000) {
        return '刚刚';
    }
    
    // 1小时内
    if (diff < 3600000) {
        return Math.floor(diff / 60000) + '分钟前';
    }
    
    // 今天
    if (date.toDateString() === now.toDateString()) {
        return '今天 ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    }
    
    // 昨天
    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    if (date.toDateString() === yesterday.toDateString()) {
        return '昨天 ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    }
    
    // 其他日期
    return date.toLocaleDateString('zh-CN') + ' ' + 
           date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
}

// 关闭模态框（点击外部）
window.onclick = function(event) {
    const modal = document.getElementById('deleteModal');
    if (event.target === modal) {
        closeDeleteModal();
    }
}

