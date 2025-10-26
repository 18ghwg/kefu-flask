/**
 * CSRF验证页面脚本
 * 处理页面自动刷新和导航功能
 */

// 自动倒计时刷新
let countdown = 5;
const countdownElement = document.getElementById('countdown');

const timer = setInterval(() => {
    countdown--;
    countdownElement.textContent = countdown;
    
    if (countdown <= 0) {
        clearInterval(timer);
        refreshPage();
    }
}, 1000);

// 刷新页面
function refreshPage() {
    // 如果有来源URL，跳转回去
    const referrer = document.referrer;
    if (referrer && referrer.includes(window.location.host)) {
        window.location.href = referrer;
    } else {
        // 否则刷新当前页面
        window.location.reload();
    }
}

// 返回上一页
function goBack() {
    if (window.history.length > 1) {
        window.history.back();
    } else {
        window.location.href = '/';
    }
}

// 点击任意按钮时停止倒计时
document.querySelectorAll('.btn').forEach(btn => {
    btn.addEventListener('click', () => {
        clearInterval(timer);
    });
});

