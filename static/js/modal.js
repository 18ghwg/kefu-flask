/**
 * 通用模态弹窗组件
 * 用于替代原生 alert()、confirm()、prompt()
 * 
 * 使用示例：
 *   modal.info('这是一条信息');
 *   modal.success('操作成功！');
 *   modal.error('操作失败');
 *   modal.warning('请注意');
 *   modal.confirm('确定要删除吗？', () => { console.log('已确认'); });
 */

class Modal {
    constructor() {
        this.overlay = null;
        this.container = null;
        this.confirmCallback = null;
        this.cancelCallback = null;
        this.init();
    }

    /**
     * 初始化模态弹窗DOM结构
     */
    init() {
        // 创建模态遮罩层
        this.overlay = document.createElement('div');
        this.overlay.className = 'modal-overlay';
        this.overlay.id = 'globalModalOverlay';
        
        // 创建模态容器
        this.container = document.createElement('div');
        this.container.className = 'modal-container';
        
        this.overlay.appendChild(this.container);
        document.body.appendChild(this.overlay);
        
        // 点击背景关闭
        this.overlay.addEventListener('click', (e) => {
            if (e.target === this.overlay) {
                this.close();
            }
        });
        
        // ESC键关闭
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.overlay.classList.contains('show')) {
                this.close();
            }
        });
    }

    /**
     * 显示模态弹窗
     * @param {Object} options - 配置选项
     */
    show(options) {
        const {
            type = 'info',           // 类型: info, success, warning, error, confirm
            title = '提示',           // 标题
            message = '',            // 消息内容
            icon = null,             // 自定义图标
            showClose = true,        // 显示关闭按钮
            buttons = null,          // 自定义按钮
            onConfirm = null,        // 确认回调
            onCancel = null,         // 取消回调
            html = null,             // 自定义HTML内容
            closeOnOverlay = true    // 点击背景是否关闭
        } = options;

        // 保存回调函数
        this.confirmCallback = onConfirm;
        this.cancelCallback = onCancel;

        // 图标映射
        const iconMap = {
            info: 'fas fa-info-circle',
            success: 'fas fa-check-circle',
            warning: 'fas fa-exclamation-triangle',
            error: 'fas fa-times-circle',
            confirm: 'fas fa-question-circle'
        };

        // 标题颜色映射
        const titleColorMap = {
            info: '#3b82f6',
            success: '#10b981',
            warning: '#f59e0b',
            error: '#ef4444',
            confirm: '#f59e0b'
        };

        // 构建HTML
        let modalHTML = `
            <div class="modal-header">
                <div class="modal-title" style="color: ${titleColorMap[type]}">
                    ${icon || `<i class="${iconMap[type]}"></i>`}
                    <span>${title}</span>
                </div>
                ${showClose ? '<button class="modal-close" onclick="modal.close()">×</button>' : ''}
            </div>
            <div class="modal-body">
                ${html || `
                    <div class="modal-icon ${type}">
                        <i class="${iconMap[type]}"></i>
                    </div>
                    <p class="modal-message">${message}</p>
                `}
            </div>
            <div class="modal-footer">
                ${this.renderButtons(type, buttons)}
            </div>
        `;

        this.container.innerHTML = modalHTML;
        
        // 控制是否可点击背景关闭
        if (!closeOnOverlay) {
            this.overlay.style.pointerEvents = 'none';
            this.container.style.pointerEvents = 'auto';
        } else {
            this.overlay.style.pointerEvents = 'auto';
        }
        
        this.overlay.classList.add('show');
    }

    /**
     * 渲染按钮
     */
    renderButtons(type, customButtons) {
        if (customButtons) {
            return customButtons.map(btn => 
                `<button class="modal-btn modal-btn-${btn.type || 'primary'}" 
                         onclick="${btn.onclick || 'modal.close()'}">${btn.text}</button>`
            ).join('');
        }

        // 默认按钮
        if (type === 'confirm') {
            return `
                <button class="modal-btn modal-btn-secondary" onclick="modal.handleCancel()">取消</button>
                <button class="modal-btn modal-btn-primary" onclick="modal.handleConfirm()">确定</button>
            `;
        }

        return `<button class="modal-btn modal-btn-primary" onclick="modal.close()">确定</button>`;
    }

    /**
     * 关闭模态弹窗
     */
    close() {
        // 添加关闭动画
        this.overlay.classList.add('closing');
        
        setTimeout(() => {
            this.overlay.classList.remove('show');
            this.overlay.classList.remove('closing');
            this.confirmCallback = null;
            this.cancelCallback = null;
        }, 200);
    }

    /**
     * 处理确认
     */
    handleConfirm() {
        const callback = this.confirmCallback;
        this.close();
        // 延迟执行回调，确保弹窗先关闭
        if (callback) {
            setTimeout(() => callback(), 100);
        }
    }

    /**
     * 处理取消
     */
    handleCancel() {
        const callback = this.cancelCallback;
        this.close();
        // 延迟执行回调，确保弹窗先关闭
        if (callback) {
            setTimeout(() => callback(), 100);
        }
    }

    /**
     * 快捷方法：信息提示
     * @param {string} message - 消息内容
     * @param {string} title - 标题（可选）
     */
    info(message, title = '提示') {
        this.show({ type: 'info', title, message });
    }

    /**
     * 快捷方法：成功提示
     * @param {string} message - 消息内容
     * @param {string} title - 标题（可选）
     */
    success(message, title = '成功') {
        this.show({ type: 'success', title, message });
    }

    /**
     * 快捷方法：警告提示
     * @param {string} message - 消息内容
     * @param {string} title - 标题（可选）
     */
    warning(message, title = '警告') {
        this.show({ type: 'warning', title, message });
    }

    /**
     * 快捷方法：错误提示
     * @param {string} message - 消息内容
     * @param {string} title - 标题（可选）
     */
    error(message, title = '错误') {
        this.show({ type: 'error', title, message });
    }

    /**
     * 快捷方法：确认对话框
     * @param {string} message - 消息内容
     * @param {function} onConfirm - 确认回调
     * @param {function} onCancel - 取消回调（可选）
     * @param {string} title - 标题（可选）
     */
    confirm(message, onConfirm, onCancel = null, title = '确认') {
        this.show({ 
            type: 'confirm', 
            title, 
            message,
            onConfirm,
            onCancel,
            closeOnOverlay: false  // 确认对话框不允许点击背景关闭
        });
    }

    /**
     * 快捷方法：加载提示
     * @param {string} message - 消息内容
     * @param {string} title - 标题（可选）
     */
    loading(message = '加载中...', title = '请稍候') {
        this.show({
            type: 'info',
            title,
            html: `
                <div class="modal-loading">
                    <div class="spinner"></div>
                    <p class="modal-message">${message}</p>
                </div>
            `,
            showClose: false,
            closeOnOverlay: false
        });
    }
}

// 创建全局实例
const modal = new Modal();

// 导出（如果使用模块化）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Modal;
}

// 控制台提示
console.log('[Modal] 通用模态弹窗组件已加载 ✓');
console.log('[Modal] 使用方法: modal.success("操作成功"), modal.error("操作失败"), modal.confirm("确定吗?", callback)');

