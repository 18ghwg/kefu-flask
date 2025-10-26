/**
 * 数据看板页面 - 脚本
 */

// 全局变量
let currentDays = 7;
let charts = {};

// 页面加载完成
document.addEventListener('DOMContentLoaded', function() {
    initCharts();
    loadDashboardData();
    startRealtimeUpdates();
});

// 初始化图表
function initCharts() {
    // 趋势图
    const trendCtx = document.getElementById('trendChart').getContext('2d');
    charts.trend = new Chart(trendCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: '访客',
                    data: [],
                    borderColor: 'var(--primary-color)',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.4
                },
                {
                    label: '会话',
                    data: [],
                    borderColor: '#f093fb',
                    backgroundColor: 'rgba(240, 147, 251, 0.1)',
                    tension: 0.4
                },
                {
                    label: '消息',
                    data: [],
                    borderColor: '#4facfe',
                    backgroundColor: 'rgba(79, 172, 254, 0.1)',
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });

    // 客服绩效图
    const performanceCtx = document.getElementById('performanceChart').getContext('2d');
    charts.performance = new Chart(performanceCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: '会话数',
                data: [],
                backgroundColor: 'rgba(102, 126, 234, 0.8)'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });

    // 评分分布图
    const ratingCtx = document.getElementById('ratingChart').getContext('2d');
    charts.rating = new Chart(ratingCtx, {
        type: 'doughnut',
        data: {
            labels: ['5星', '4星', '3星', '2星', '1星'],
            datasets: [{
                data: [0, 0, 0, 0, 0],
                backgroundColor: [
                    '#10b981',
                    '#3b82f6',
                    '#f59e0b',
                    '#f97316',
                    '#ef4444'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });

    // 访问来源图
    const sourceCtx = document.getElementById('sourceChart').getContext('2d');
    charts.source = new Chart(sourceCtx, {
        type: 'pie',
        data: {
            labels: ['PC网页', '移动网页', 'APP', '小程序', '其他'],
            datasets: [{
                data: [0, 0, 0, 0, 0],
                backgroundColor: [
                    'var(--primary-color)',
                    '#f093fb',
                    '#4facfe',
                    '#43e97b',
                    '#fa709a'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });

    // 设备分布图
    const deviceCtx = document.getElementById('deviceChart').getContext('2d');
    charts.device = new Chart(deviceCtx, {
        type: 'doughnut',
        data: {
            labels: ['PC', '移动端', '平板'],
            datasets: [{
                data: [0, 0, 0],
                backgroundColor: [
                    'var(--primary-color)',
                    '#f093fb',
                    '#4facfe'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });

    // 地区分布图
    const regionCtx = document.getElementById('regionChart').getContext('2d');
    charts.region = new Chart(regionCtx, {
        type: 'pie',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: [
                    'var(--primary-color)',
                    '#f093fb',
                    '#4facfe',
                    '#43e97b',
                    '#fa709a',
                    '#38f9d7',
                    '#fee140',
                    '#30cfd0',
                    '#a8edea',
                    '#fbc2eb',
                    '#fdcbf1'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        boxWidth: 12,
                        padding: 10
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: ${value}人 (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// 加载数据看板数据
async function loadDashboardData() {
    try {
        await Promise.all([
            loadOverviewStatistics(),
            loadTrendData(),
            loadServicePerformance(),
            loadRatingDistribution(),
            loadSourceData(),
            loadDeviceData(),
            loadRegionData()
        ]);
    } catch (error) {
        console.error('加载看板数据失败:', error);
    }
}

// 加载概览统计
async function loadOverviewStatistics() {
    try {
        const response = await fetch(`/api/admin/statistics/overview?days=${currentDays}`);
        const result = await response.json();
        
        if (result.code === 0) {
            const data = result.data;
            
            // 更新指标卡片
            document.getElementById('totalVisitors').textContent = data.visitors.total;
            document.getElementById('totalSessions').textContent = data.sessions.total;
            document.getElementById('totalMessages').textContent = data.messages.total;
            document.getElementById('satisfaction').textContent = data.performance.satisfaction_rate.toFixed(1) + '%';
            document.getElementById('onlineServices').textContent = `${data.services.online}/${data.services.total}`;
            document.getElementById('avgResponseTime').textContent = data.performance.avg_response_time + 's';
            
            // 计算变化率（模拟）
            updateMetricChanges(data);
        }
    } catch (error) {
        console.error('加载概览统计失败:', error);
    }
}

// 更新指标变化率
function updateMetricChanges(data) {
    // 这里简化处理，实际应该计算环比变化
    const changes = {
        visitors: '+12.5%',
        sessions: '+8.3%',
        messages: '+15.7%',
        satisfaction: '+2.1%'
    };
    
    document.getElementById('visitorsChange').innerHTML = `<i class="fas fa-arrow-up"></i> ${changes.visitors}`;
    document.getElementById('sessionsChange').innerHTML = `<i class="fas fa-arrow-up"></i> ${changes.sessions}`;
    document.getElementById('messagesChange').innerHTML = `<i class="fas fa-arrow-up"></i> ${changes.messages}`;
    document.getElementById('satisfactionChange').innerHTML = `<i class="fas fa-arrow-up"></i> ${changes.satisfaction}`;
    
    // 响应时间是越低越好，所以是向下箭头
    document.getElementById('responseChange').innerHTML = `<i class="fas fa-arrow-down"></i> -5.2%`;
    document.getElementById('responseChange').classList.add('positive');
}

// 加载趋势数据
async function loadTrendData() {
    try {
        const response = await fetch(`/api/admin/statistics/trend?days=${currentDays}`);
        const result = await response.json();
        
        if (result.code === 0) {
            const data = result.data;
            
            charts.trend.data.labels = data.map(item => {
                const date = new Date(item.date);
                return `${date.getMonth()+1}/${date.getDate()}`;
            });
            
            charts.trend.data.datasets[0].data = data.map(item => item.visitors);
            charts.trend.data.datasets[1].data = data.map(item => item.sessions);
            charts.trend.data.datasets[2].data = data.map(item => item.messages);
            
            charts.trend.update();
        }
    } catch (error) {
        console.error('加载趋势数据失败:', error);
    }
}

// 加载客服绩效
async function loadServicePerformance() {
    try {
        const response = await fetch(`/api/admin/statistics/service-performance?days=${currentDays}`);
        const result = await response.json();
        
        if (result.code === 0) {
            const data = result.data.slice(0, 5); // 只显示TOP5
            
            charts.performance.data.labels = data.map(item => item.service_name);
            charts.performance.data.datasets[0].data = data.map(item => item.session_count);
            
            charts.performance.update();
        }
    } catch (error) {
        console.error('加载客服绩效失败:', error);
    }
}

// 加载评分分布
async function loadRatingDistribution() {
    try {
        const response = await fetch(`/api/admin/comment/statistics?days=${currentDays}`);
        const result = await response.json();
        
        if (result.code === 0) {
            const distribution = result.data.score_distribution;
            
            charts.rating.data.datasets[0].data = [
                distribution['5'] || 0,
                distribution['4'] || 0,
                distribution['3'] || 0,
                distribution['2'] || 0,
                distribution['1'] || 0
            ];
            
            charts.rating.update();
        }
    } catch (error) {
        console.error('加载评分分布失败:', error);
    }
}

// 加载来源数据
async function loadSourceData() {
    try {
        const response = await fetch(`/api/admin/statistics/visitor-source?days=${currentDays}`);
        const result = await response.json();
        
        if (result.code === 0) {
            const data = result.data;
            charts.source.data.datasets[0].data = [
                data.pc_web || 0,
                data.mobile_web || 0,
                data.app || 0,
                data.miniprogram || 0,
                data.other || 0
            ];
            charts.source.update();
        }
    } catch (error) {
        console.error('加载来源数据失败:', error);
        // 使用模拟数据
        charts.source.data.datasets[0].data = [0, 0, 0, 0, 0];
        charts.source.update();
    }
}

// 加载设备数据
async function loadDeviceData() {
    try {
        const response = await fetch(`/api/admin/statistics/device-stats?days=${currentDays}`);
        const result = await response.json();
        
        if (result.code === 0) {
            const data = result.data;
            charts.device.data.datasets[0].data = [
                data.pc || 0,
                data.mobile || 0,
                data.tablet || 0
            ];
            charts.device.update();
        }
    } catch (error) {
        console.error('加载设备数据失败:', error);
        charts.device.data.datasets[0].data = [0, 0, 0];
        charts.device.update();
    }
}

// 加载地区分布数据
async function loadRegionData() {
    try {
        const response = await fetch(`/api/admin/statistics/region-stats?days=${currentDays}`);
        const result = await response.json();
        
        if (result.code === 0) {
            const data = result.data;
            
            if (data.total === 0) {
                // 没有数据时显示提示
                charts.region.data.labels = ['暂无数据'];
                charts.region.data.datasets[0].data = [1];
                charts.region.data.datasets[0].backgroundColor = ['#e0e0e0'];
            } else {
                charts.region.data.labels = data.regions;
                charts.region.data.datasets[0].data = data.counts;
                // 使用预定义的颜色
                const colors = [
                    'var(--primary-color)', '#f093fb', '#4facfe', '#43e97b', '#fa709a',
                    '#38f9d7', '#fee140', '#30cfd0', '#a8edea', '#fbc2eb', '#fdcbf1'
                ];
                charts.region.data.datasets[0].backgroundColor = colors.slice(0, data.regions.length);
            }
            
            charts.region.update();
        }
    } catch (error) {
        console.error('加载地区数据失败:', error);
        charts.region.data.labels = ['暂无数据'];
        charts.region.data.datasets[0].data = [1];
        charts.region.data.datasets[0].backgroundColor = ['#e0e0e0'];
        charts.region.update();
    }
}

// 开始实时更新
let realtimeInterval = null;
let timeUpdateInterval = null;

// 格式化时间差
function formatTimeAgo(timestamp) {
    const now = new Date();
    const time = new Date(timestamp);
    const diff = Math.floor((now - time) / 1000); // 秒
    
    if (diff < 10) {
        return '刚刚';
    } else if (diff < 60) {
        return `${diff}秒前`;
    } else if (diff < 3600) {
        const minutes = Math.floor(diff / 60);
        return `${minutes}分钟前`;
    } else if (diff < 86400) {
        const hours = Math.floor(diff / 3600);
        return `${hours}小时前`;
    } else {
        const days = Math.floor(diff / 86400);
        return `${days}天前`;
    }
}

// 更新所有时间显示
function updateAllTimes() {
    document.querySelectorAll('.realtime-time').forEach(element => {
        const timestamp = element.dataset.timestamp;
        if (timestamp) {
            element.textContent = formatTimeAgo(timestamp);
        }
    });
}

function startRealtimeUpdates() {
    const container = document.getElementById('realtimeList');
    
    async function loadRealtimeEvents() {
        try {
            const response = await fetch('/api/admin/statistics/realtime-events?limit=10');
            const result = await response.json();
            
            if (result.code === 0) {
                container.innerHTML = '';
                
                if (result.data.length === 0) {
                    // 没有数据时显示提示
                    container.innerHTML = `
                        <div class="realtime-empty">
                            <p>暂无最近的活动</p>
                            <p class="text-muted">最近1小时内没有访客或消息</p>
                        </div>
                    `;
                } else {
                    result.data.forEach(event => {
                        const item = document.createElement('div');
                        item.className = 'realtime-item';
                        
                        // 根据事件类型设置不同的图标
                        let iconClass = 'fas fa-user';
                        let iconColor = 'var(--primary-color)';
                        if (event.type === 'message') {
                            iconClass = 'fas fa-comment';
                            iconColor = '#4facfe';
                        } else if (event.type === 'comment') {
                            iconClass = 'fas fa-star';
                            iconColor = '#f093fb';
                        }
                        
                        // 计算时间差
                        const timeAgo = formatTimeAgo(event.timestamp);
                        
                        item.innerHTML = `
                            <div class="realtime-info">
                                <div class="realtime-avatar" style="background-color: ${iconColor}20;">
                                    <i class="${iconClass}" style="color: ${iconColor};"></i>
                                </div>
                                <div class="realtime-details">
                                    <h4>${event.name}</h4>
                                    <p>${event.user}</p>
                                </div>
                            </div>
                            <div class="realtime-time" data-timestamp="${event.timestamp}">${timeAgo}</div>
                        `;
                        container.appendChild(item);
                    });
                }
            }
        } catch (error) {
            console.error('加载实时事件失败:', error);
        }
    }
    
    // 立即加载一次
    loadRealtimeEvents();
    
    // 清除旧的定时器（如果存在）
    if (realtimeInterval) {
        clearInterval(realtimeInterval);
    }
    if (timeUpdateInterval) {
        clearInterval(timeUpdateInterval);
    }
    
    // 每5秒刷新数据
    realtimeInterval = setInterval(loadRealtimeEvents, 5000);
    
    // 每1秒更新时间显示
    timeUpdateInterval = setInterval(updateAllTimes, 1000);
}

// 切换时间范围
function changeTimeRange() {
    const select = document.getElementById('timeRange');
    currentDays = parseInt(select.value);
    loadDashboardData();
}

// 刷新数据
function refreshData() {
    loadDashboardData();
}

// CSS动画
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(-10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
`;
document.head.appendChild(style);

