/**
 * 虚拟滚动组件
 * 
 * 设计原则：
 * - KISS: 简单直接的虚拟滚动实现
 * - 性能优化: 只渲染可见区域的消息
 * - 兼容性: 支持动态高度的消息
 * 
 * 使用场景：
 * - 聊天消息列表（大量消息时性能优化）
 * - 访客列表
 * - 其他长列表
 */

class VirtualScroll {
    /**
     * 构造函数
     * 
     * @param {Object} options - 配置选项
     * @param {HTMLElement} options.container - 容器元素
     * @param {Array} options.data - 数据数组
     * @param {Function} options.renderItem - 渲染单个项目的函数
     * @param {Number} options.itemHeight - 预估项目高度（可选，用于优化计算）
     * @param {Number} options.bufferSize - 缓冲区大小（可见区域上下各渲染的额外项目数）
     */
    constructor(options) {
        this.container = options.container;
        this.data = options.data || [];
        this.renderItem = options.renderItem;
        this.itemHeight = options.itemHeight || 80; // 默认80px
        this.bufferSize = options.bufferSize || 5;
        
        // 内部状态
        this.scrollTop = 0;
        this.containerHeight = 0;
        this.startIndex = 0;
        this.endIndex = 0;
        this.visibleItems = [];
        
        // 创建虚拟容器
        this.viewport = document.createElement('div');
        this.viewport.style.position = 'relative';
        this.viewport.style.overflow = 'auto';
        this.viewport.style.height = '100%';
        
        // 创建内容包装器（用于撑开滚动高度）
        this.content = document.createElement('div');
        this.content.style.position = 'relative';
        this.content.style.minHeight = '100%';
        
        this.viewport.appendChild(this.content);
        this.container.appendChild(this.viewport);
        
        // 绑定事件
        this.viewport.addEventListener('scroll', this._handleScroll.bind(this));
        window.addEventListener('resize', this._handleResize.bind(this));
        
        // 初始化
        this._init();
    }
    
    /**
     * 初始化
     */
    _init() {
        this.containerHeight = this.viewport.clientHeight;
        this._updateContentHeight();
        this._updateVisibleRange();
        this._render();
    }
    
    /**
     * 处理滚动事件
     */
    _handleScroll() {
        this.scrollTop = this.viewport.scrollTop;
        this._updateVisibleRange();
        this._render();
    }
    
    /**
     * 处理窗口大小变化
     */
    _handleResize() {
        this.containerHeight = this.viewport.clientHeight;
        this._updateVisibleRange();
        this._render();
    }
    
    /**
     * 更新内容高度（撑开滚动条）
     */
    _updateContentHeight() {
        const totalHeight = this.data.length * this.itemHeight;
        this.content.style.height = totalHeight + 'px';
    }
    
    /**
     * 更新可见范围
     */
    _updateVisibleRange() {
        const visibleCount = Math.ceil(this.containerHeight / this.itemHeight);
        
        this.startIndex = Math.max(
            0, 
            Math.floor(this.scrollTop / this.itemHeight) - this.bufferSize
        );
        
        this.endIndex = Math.min(
            this.data.length,
            this.startIndex + visibleCount + this.bufferSize * 2
        );
    }
    
    /**
     * 渲染可见项目
     */
    _render() {
        // 清空内容
        this.content.innerHTML = '';
        
        // 创建文档片段（性能优化）
        const fragment = document.createDocumentFragment();
        
        // 渲染可见项目
        for (let i = this.startIndex; i < this.endIndex; i++) {
            const item = this.data[i];
            const element = this.renderItem(item, i);
            
            // 设置绝对定位
            element.style.position = 'absolute';
            element.style.top = (i * this.itemHeight) + 'px';
            element.style.width = '100%';
            
            fragment.appendChild(element);
        }
        
        this.content.appendChild(fragment);
        
        // 保存可见项目引用
        this.visibleItems = Array.from(this.content.children);
    }
    
    /**
     * 更新数据
     * 
     * @param {Array} newData - 新数据数组
     */
    updateData(newData) {
        this.data = newData;
        this._updateContentHeight();
        this._updateVisibleRange();
        this._render();
    }
    
    /**
     * 追加数据
     * 
     * @param {Object|Array} items - 要追加的项目
     */
    appendData(items) {
        const itemsArray = Array.isArray(items) ? items : [items];
        this.data = this.data.concat(itemsArray);
        this._updateContentHeight();
        this._updateVisibleRange();
        this._render();
    }
    
    /**
     * 前置数据（用于历史消息加载）
     * 
     * @param {Array} items - 要前置的项目
     */
    prependData(items) {
        const oldScrollHeight = this.content.scrollHeight;
        
        this.data = items.concat(this.data);
        this._updateContentHeight();
        
        // 计算滚动位置偏移
        const newScrollHeight = this.content.scrollHeight;
        const offset = newScrollHeight - oldScrollHeight;
        
        // 保持滚动位置
        this.viewport.scrollTop = this.scrollTop + offset;
        
        this._updateVisibleRange();
        this._render();
    }
    
    /**
     * 滚动到指定索引
     * 
     * @param {Number} index - 目标索引
     * @param {String} behavior - 滚动行为（'auto'|'smooth'）
     */
    scrollToIndex(index, behavior = 'auto') {
        const targetScrollTop = index * this.itemHeight;
        this.viewport.scrollTo({
            top: targetScrollTop,
            behavior: behavior
        });
    }
    
    /**
     * 滚动到底部
     * 
     * @param {String} behavior - 滚动行为（'auto'|'smooth'）
     */
    scrollToBottom(behavior = 'auto') {
        this.viewport.scrollTo({
            top: this.content.scrollHeight,
            behavior: behavior
        });
    }
    
    /**
     * 销毁实例
     */
    destroy() {
        this.viewport.removeEventListener('scroll', this._handleScroll);
        window.removeEventListener('resize', this._handleResize);
        this.container.innerHTML = '';
    }
}


// ========== 轻量级虚拟滚动（用于消息列表） ==========

/**
 * 消息列表虚拟滚动优化
 * 
 * 原则：
 * - YAGNI: 只在消息数量超过阈值时启用
 * - 性能: 使用简单的分页策略
 */
class MessageVirtualScroll {
    /**
     * 构造函数
     * 
     * @param {HTMLElement} container - 消息容器
     * @param {Number} threshold - 启用虚拟滚动的消息数量阈值
     * @param {Number} chunkSize - 每次渲染的消息块大小
     */
    constructor(container, threshold = 100, chunkSize = 50) {
        this.container = container;
        this.threshold = threshold;
        this.chunkSize = chunkSize;
        this.messages = [];
        this.renderedRange = { start: 0, end: 0 };
        this.isEnabled = false;
    }
    
    /**
     * 添加消息
     * 
     * @param {HTMLElement} messageElement - 消息元素
     */
    addMessage(messageElement) {
        this.messages.push(messageElement);
        
        // 检查是否需要启用虚拟滚动
        if (this.messages.length > this.threshold && !this.isEnabled) {
            this._enableVirtualScroll();
        }
        
        // 如果未启用，直接添加到容器
        if (!this.isEnabled) {
            this.container.appendChild(messageElement);
        } else {
            // 启用了虚拟滚动，只渲染末尾的消息
            this._renderLatest();
        }
    }
    
    /**
     * 启用虚拟滚动
     */
    _enableVirtualScroll() {
        console.log(`✅ 启用虚拟滚动：消息数量=${this.messages.length}`);
        this.isEnabled = true;
        
        // 监听滚动到顶部加载更多
        this.container.addEventListener('scroll', this._handleScroll.bind(this));
    }
    
    /**
     * 处理滚动
     */
    _handleScroll() {
        // 滚动到顶部时加载更多历史消息
        if (this.container.scrollTop < 100 && this.renderedRange.start > 0) {
            this._loadMore();
        }
    }
    
    /**
     * 加载更多历史消息
     */
    _loadMore() {
        const oldScrollHeight = this.container.scrollHeight;
        const newStart = Math.max(0, this.renderedRange.start - this.chunkSize);
        
        // 渲染更早的消息
        for (let i = newStart; i < this.renderedRange.start; i++) {
            this.container.insertBefore(this.messages[i], this.container.firstChild);
        }
        
        this.renderedRange.start = newStart;
        
        // 保持滚动位置
        const newScrollHeight = this.container.scrollHeight;
        this.container.scrollTop = newScrollHeight - oldScrollHeight;
        
        console.log(`✅ 加载更多历史消息：${newStart}-${this.renderedRange.start}`);
    }
    
    /**
     * 渲染最新的消息
     */
    _renderLatest() {
        const start = Math.max(0, this.messages.length - this.chunkSize);
        const end = this.messages.length;
        
        // 清空容器
        this.container.innerHTML = '';
        
        // 渲染最新的消息
        for (let i = start; i < end; i++) {
            this.container.appendChild(this.messages[i]);
        }
        
        this.renderedRange = { start, end };
        
        // 滚动到底部
        this.container.scrollTop = this.container.scrollHeight;
    }
    
    /**
     * 获取消息数量
     */
    getMessageCount() {
        return this.messages.length;
    }
    
    /**
     * 清空消息
     */
    clear() {
        this.messages = [];
        this.renderedRange = { start: 0, end: 0 };
        this.container.innerHTML = '';
    }
}


// 导出
window.VirtualScroll = VirtualScroll;
window.MessageVirtualScroll = MessageVirtualScroll;


