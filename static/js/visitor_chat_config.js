/**
 * 访客聊天配置文件
 * 用于初始化访客聊天页面的配置参数
 */

// 从URL或模板传递的参数
window.CHAT_CONFIG = window.CHAT_CONFIG || {
    special: ''  // 指定客服ID（专属链接）
};

// 在页面加载后初始化分配模块
window.addEventListener('DOMContentLoaded', function() {
    // 从URL获取专属客服ID
    const urlParams = new URLSearchParams(window.location.search);
    const serviceId = urlParams.get('service_id') || urlParams.get('sid') || window.CHAT_CONFIG.special;
    
    // 如果有专属客服ID，通过socket.io通知后端
    if (serviceId && window.socket) {
        console.log('✅ 检测到专属客服链接，客服ID:', serviceId);
        // 这个逻辑会在socket连接后在visitor_chat.js中处理
    }
});

