/**
 * 登录页面拼图滑块验证码功能
 */

class PuzzleCaptcha {
    constructor(options) {
        this.container = options.container;
        this.slider = options.slider;
        this.progress = options.progress;
        this.text = options.text;
        this.status = options.status;
        this.canvasContainer = options.canvasContainer;
        this.onSuccess = options.onSuccess || function() {};
        this.onFail = options.onFail || function() {};
        
        // 验证参数
        this.tolerance = 5; // 容差像素
        this.isVerified = false; // 验证状态
        this.isLocked = false; // 锁定状态
        
        // 后端验证相关
        this.captchaToken = null; // 验证token
        this.verifyToken = null; // 验证成功后的令牌
        this.puzzleY = 0; // 拼图的Y坐标
        
        // 拖动状态
        this.isDragging = false;
        this.startX = 0;
        this.currentX = 0;
        this.maxPosition = 0;
        
        // Canvas 相关
        this.bgCanvas = null;
        this.puzzleCanvas = null;
        
        this.init();
    }
    
    async init() {
        // 创建Canvas
        this.createCanvases();
        
        // 计算最大滑动距离
        this.calculateMaxPosition();
        
        // 从后端获取验证码
        await this.generateCaptcha();
        
        // 绑定事件
        this.bindEvents();
        
        // 窗口大小改变时重新计算
        window.addEventListener('resize', () => {
            if (!this.isVerified && !this.isLocked) {
                this.calculateMaxPosition();
            }
        });
    }
    
    createCanvases() {
        // 创建背景Canvas
        this.bgCanvas = document.createElement('canvas');
        this.bgCanvas.width = 300;
        this.bgCanvas.height = 150;
        this.bgCanvas.className = 'captcha-bg-canvas';
        
        // 创建拼图Canvas
        this.puzzleCanvas = document.createElement('canvas');
        this.puzzleCanvas.width = 50;
        this.puzzleCanvas.height = 50;
        this.puzzleCanvas.className = 'captcha-puzzle-canvas';
        
        // 清空容器并添加Canvas
        this.canvasContainer.innerHTML = '';
        this.canvasContainer.appendChild(this.bgCanvas);
        this.canvasContainer.appendChild(this.puzzleCanvas);
    }
    
    async generateCaptcha() {
        try {
            this.showStatus('正在加载验证码...', 'info');
            
            const response = await fetch('/api/captcha/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            
            if (result.code === 0) {
                this.captchaToken = result.data.token;
                this.puzzleY = result.data.y;
                
                // 加载背景图
                await this.loadImage(this.bgCanvas, result.data.background);
                
                // 加载拼图块
                await this.loadImage(this.puzzleCanvas, result.data.puzzle);
                
                // 设置拼图初始位置
                this.puzzleCanvas.style.top = this.puzzleY + 'px';
                this.puzzleCanvas.style.left = '0px';
                
                this.showStatus('', '');
                console.log('拼图验证码生成成功');
            } else {
                this.showError('验证码生成失败，请刷新页面');
            }
        } catch (error) {
            console.error('生成验证码失败:', error);
            this.showError('网络错误，请刷新页面');
        }
    }
    
    loadImage(canvas, base64Data) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.onload = () => {
                const ctx = canvas.getContext('2d');
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                resolve();
            };
            img.onerror = reject;
            img.src = base64Data;
        });
    }
    
    calculateMaxPosition() {
        const containerWidth = this.container.offsetWidth;
        const sliderWidth = this.slider.offsetWidth;
        this.maxPosition = containerWidth - sliderWidth;
    }
    
    bindEvents() {
        // 鼠标事件
        this.slider.addEventListener('mousedown', this.onDragStart.bind(this));
        document.addEventListener('mousemove', this.onDrag.bind(this));
        document.addEventListener('mouseup', this.onDragEnd.bind(this));
        
        // 触摸事件（移动端）
        this.slider.addEventListener('touchstart', this.onDragStart.bind(this), { passive: false });
        document.addEventListener('touchmove', this.onDrag.bind(this), { passive: false });
        document.addEventListener('touchend', this.onDragEnd.bind(this));
        
        // 防止文本选择
        this.container.addEventListener('selectstart', (e) => e.preventDefault());
    }
    
    onDragStart(e) {
        if (this.isLocked) return;
        
        this.isDragging = true;
        this.startX = this.getEventX(e);
        this.currentX = 0;
        
        this.slider.style.transition = 'none';
        this.progress.style.transition = 'none';
        this.puzzleCanvas.style.transition = 'none';
        
        // 添加拖动样式
        this.slider.classList.add('dragging');
    }
    
    onDrag(e) {
        if (!this.isDragging || this.isLocked) return;
        
        e.preventDefault();
        
        const eventX = this.getEventX(e);
        this.currentX = eventX - this.startX;
        
        // 限制滑动范围
        if (this.currentX < 0) this.currentX = 0;
        if (this.currentX > this.maxPosition) this.currentX = this.maxPosition;
        
        // 计算实际像素位置（背景图宽度300px，滑动区域宽度由maxPosition决定）
        const puzzleX = (this.currentX / this.maxPosition) * (300 - 50);
        
        // 更新滑块和进度条位置
        this.slider.style.left = this.currentX + 'px';
        this.progress.style.width = (this.currentX + this.slider.offsetWidth) + 'px';
        
        // 更新拼图块位置
        this.puzzleCanvas.style.left = puzzleX + 'px';
        
        // 更新提示文字透明度
        const opacity = 1 - (this.currentX / this.maxPosition);
        this.text.style.opacity = opacity;
    }
    
    onDragEnd(e) {
        if (!this.isDragging || this.isLocked) return;
        
        this.isDragging = false;
        this.slider.classList.remove('dragging');
        
        // 启用过渡动画
        this.slider.style.transition = 'all 0.3s';
        this.progress.style.transition = 'width 0.3s';
        this.puzzleCanvas.style.transition = 'all 0.3s';
        
        // 验证位置
        this.verify();
    }
    
    async verify() {
        // 计算当前拼图的X坐标（像素）
        const puzzleX = (this.currentX / this.maxPosition) * (300 - 50);
        const roundedX = Math.round(puzzleX);
        
        console.log('🔍 验证信息:', {
            '滑块位置': this.currentX,
            '最大滑动距离': this.maxPosition,
            '计算的拼图X坐标': roundedX,
            '滑动百分比': ((this.currentX / this.maxPosition) * 100).toFixed(2) + '%'
        });
        
        try {
            const response = await fetch('/api/captcha/verify', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    token: this.captchaToken,
                    x: roundedX
                })
            });
            
            const result = await response.json();
            
            console.log('📡 后端响应:', result);
            
            if (result.code === 0) {
                // 验证成功
                console.log('✅ 验证成功！');
                this.verifyToken = result.data.verify_token;
                this.onVerifySuccess();
            } else {
                // 验证失败
                console.warn('❌ 验证失败:', result.msg, result.data);
                this.onVerifyFail(result.msg);
            }
        } catch (error) {
            console.error('❌ 验证错误:', error);
            this.onVerifyFail('网络错误，请重试');
        }
    }
    
    onVerifySuccess() {
        this.isVerified = true;
        this.isLocked = true;
        
        // 吸附到终点
        this.slider.style.left = this.maxPosition + 'px';
        this.progress.style.width = '100%';
        this.text.style.opacity = '0';
        
        // 更新样式
        this.slider.classList.add('success');
        this.slider.innerHTML = '<i class="fas fa-check"></i>';
        
        // 拼图块吸附到正确位置
        const finalPuzzleX = (this.maxPosition / this.maxPosition) * (300 - 50);
        this.puzzleCanvas.style.left = finalPuzzleX + 'px';
        
        // 显示成功状态
        this.showStatus('✓ 验证成功', 'success');
        
        // 触发成功回调
        setTimeout(() => {
            this.onSuccess(this.verifyToken);
        }, 300);
    }
    
    onVerifyFail(message = '验证失败，请重试') {
        this.isLocked = true;
        
        // 更新样式
        this.slider.classList.add('failed');
        this.slider.innerHTML = '<i class="fas fa-times"></i>';
        
        // 显示失败状态
        this.showStatus('✗ ' + message, 'error');
        
        // 触发失败回调
        this.onFail();
        
        // 1.5秒后重置
        setTimeout(() => {
            this.reset();
        }, 1500);
    }
    
    showStatus(message, type) {
        this.status.textContent = message;
        this.status.className = 'captcha-status';
        if (type) {
            this.status.classList.add(type);
        }
    }
    
    showError(message) {
        this.showStatus('✗ ' + message, 'error');
    }
    
    async reset() {
        this.isVerified = false;
        this.isLocked = false;
        this.currentX = 0;
        
        // 重新从后端获取验证码
        await this.generateCaptcha();
        
        // 重置样式
        this.slider.style.left = '0';
        this.slider.style.transition = 'all 0.3s';
        this.progress.style.width = '0';
        this.progress.style.transition = 'width 0.3s';
        this.text.style.opacity = '1';
        
        this.slider.classList.remove('success', 'failed');
        this.slider.innerHTML = '<i class="fas fa-chevron-right"></i>';
        
        this.status.textContent = '';
        this.status.className = 'captcha-status';
    }
    
    getEventX(e) {
        return e.type.indexOf('touch') !== -1 ? e.touches[0].clientX : e.clientX;
    }
}

// 初始化拼图滑块验证码
document.addEventListener('DOMContentLoaded', function() {
    const captchaContainer = document.querySelector('.captcha-track');
    const captchaSlider = document.getElementById('captchaSlider');
    const captchaProgress = document.getElementById('captchaProgress');
    const captchaText = document.getElementById('captchaText');
    const captchaStatus = document.getElementById('captchaStatus');
    const canvasContainer = document.getElementById('captchaCanvas');
    const verifyTokenInput = document.getElementById('verifyToken');
    const loginBtn = document.getElementById('loginBtn');
    const loginForm = document.getElementById('loginForm');
    const captchaModal = document.getElementById('captchaModal');
    const closeModalBtn = document.getElementById('closeModal');
    const refreshCaptchaBtn = document.getElementById('refreshCaptcha');
    
    let puzzleCaptcha = null;
    
    // 显示验证码弹窗
    function showCaptchaModal() {
        captchaModal.classList.add('show');
        
        // 创建拼图验证码实例（如果还没创建）
        if (!puzzleCaptcha) {
            puzzleCaptcha = new PuzzleCaptcha({
                container: captchaContainer,
                slider: captchaSlider,
                progress: captchaProgress,
                text: captchaText,
                status: captchaStatus,
                canvasContainer: canvasContainer,
                onSuccess: function(verifyToken) {
                    // 验证成功，保存验证令牌
                    verifyTokenInput.value = verifyToken;
                    
                    // 延迟关闭弹窗并提交表单
                    setTimeout(() => {
                        closeCaptchaModal();
                        
                        // 提交表单
                        setTimeout(() => {
                            loginForm.submit();
                        }, 300);
                    }, 800);
                },
                onFail: function() {
                    // 验证失败，清空令牌
                    verifyTokenInput.value = '';
                }
            });
        } else {
            // 如果已存在，重置验证码
            puzzleCaptcha.reset();
        }
    }
    
    // 关闭验证码弹窗
    function closeCaptchaModal() {
        captchaModal.classList.remove('show');
    }
    
    // 点击登录按钮
    loginBtn.addEventListener('click', function(e) {
        e.preventDefault();
        
        // 验证表单字段
        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value.trim();
        
        if (!username) {
            modal.warning('请输入用户名');
            document.getElementById('username').focus();
            return;
        }
        
        if (!password) {
            modal.warning('请输入密码');
            document.getElementById('password').focus();
            return;
        }
        
        // 如果已经验证过且token有效，直接提交
        if (verifyTokenInput.value) {
            loginForm.submit();
            return;
        }
        
        // 显示验证码弹窗
        showCaptchaModal();
    });
    
    // 关闭按钮
    closeModalBtn.addEventListener('click', closeCaptchaModal);
    
    // 点击弹窗背景关闭
    captchaModal.addEventListener('click', function(e) {
        if (e.target === captchaModal) {
            closeCaptchaModal();
        }
    });
    
    // ESC键关闭弹窗
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && captchaModal.classList.contains('show')) {
            closeCaptchaModal();
        }
    });
    
    // 刷新验证码按钮
    refreshCaptchaBtn.addEventListener('click', function() {
        if (puzzleCaptcha) {
            puzzleCaptcha.reset();
        }
    });
    
    // 添加抖动动画
    const style = document.createElement('style');
    style.textContent = `
        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
            20%, 40%, 60%, 80% { transform: translateX(5px); }
        }
    `;
    document.head.appendChild(style);
    
    // 密码输入框回车触发登录
    document.getElementById('password').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            loginBtn.click();
        }
    });
});