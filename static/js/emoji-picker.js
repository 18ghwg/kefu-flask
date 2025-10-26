/**
 * 简单的Emoji选择器
 */

class EmojiPicker {
    constructor() {
        this.emojis = [
            // 笑脸和情感
            '😀', '😃', '😄', '😁', '😆', '😅', '🤣', '😂',
            '🙂', '🙃', '😉', '😊', '😇', '🥰', '😍', '🤩',
            '😘', '😗', '😚', '😙', '😋', '😛', '😜', '🤪',
            '😝', '🤑', '🤗', '🤭', '🤫', '🤔', '🤐', '🤨',
            
            // 表情
            '😐', '😑', '😶', '😏', '😒', '🙄', '😬', '🤥',
            '😌', '😔', '😪', '🤤', '😴', '😷', '🤒', '🤕',
            '🤢', '🤮', '🤧', '🥵', '🥶', '😵', '🤯', '🤠',
            '🥳', '😎', '🤓', '🧐', '😕', '😟', '🙁', '☹️',
            
            // 悲伤和愤怒
            '😮', '😯', '😲', '😳', '🥺', '😦', '😧', '😨',
            '😰', '😥', '😢', '😭', '😱', '😖', '😣', '😞',
            '😓', '😩', '😫', '🥱', '😤', '😡', '😠', '🤬',
            
            // 手势
            '👍', '👎', '👌', '✌️', '🤞', '🤟', '🤘', '🤙',
            '👈', '👉', '👆', '👇', '☝️', '✋', '🤚', '🖐',
            '🖖', '👋', '🤝', '🙏', '✍️', '💪', '🦾', '🦿',
            
            // 其他常用
            '❤️', '🧡', '💛', '💚', '💙', '💜', '🖤', '🤍',
            '💔', '❣️', '💕', '💞', '💓', '💗', '💖', '💘',
            '💯', '💢', '💥', '💫', '💦', '💨', '🕊️', '🦋',
            
            // 日常物品
            '🎉', '🎊', '🎈', '🎁', '🏆', '🥇', '🥈', '🥉',
            '⚽', '🏀', '🏈', '⚾', '🎾', '🏐', '🏉', '🥏',
            '🎯', '🎮', '🎲', '🎰', '🎳', '🎸', '🎹', '🎺',
            
            // 食物
            '🍏', '🍎', '🍊', '🍋', '🍌', '🍉', '🍇', '🍓',
            '🍈', '🍒', '🍑', '🥭', '🍍', '🥥', '🥝', '🍅',
            '🍆', '🥑', '🥦', '🥬', '🥒', '🌶️', '🌽', '🥕',
            '🍕', '🍔', '🍟', '🌭', '🥪', '🌮', '🌯', '🥙',
            
            // 动物
            '🐶', '🐱', '🐭', '🐹', '🐰', '🦊', '🐻', '🐼',
            '🐨', '🐯', '🦁', '🐮', '🐷', '🐸', '🐵', '🐔',
            '🐧', '🐦', '🐤', '🦆', '🦅', '🦉', '🦇', '🐺',
            
            // 天气和自然
            '☀️', '🌤️', '⛅', '🌥️', '☁️', '🌦️', '🌧️', '⛈️',
            '🌩️', '🌨️', '❄️', '☃️', '⛄', '🌬️', '💨', '🌪️',
            '🌈', '☔', '⚡', '🔥', '💧', '🌊', '🌙', '⭐',
            
            // 符号
            '✅', '❌', '⭕', '🔴', '🟠', '🟡', '🟢', '🔵',
            '🟣', '⚫', '⚪', '🟤', '💬', '💭', '🗨️', '🗯️'
        ];
        
        this.picker = null;
        this.targetInput = null;
        this.onSelect = null;
    }
    
    /**
     * 创建选择器DOM
     */
    create() {
        if (this.picker) {
            return this.picker;
        }
        
        const picker = document.createElement('div');
        picker.className = 'emoji-picker';
        picker.style.display = 'none';
        
        // 创建emoji网格
        const grid = document.createElement('div');
        grid.className = 'emoji-grid';
        
        this.emojis.forEach(emoji => {
            const btn = document.createElement('button');
            btn.className = 'emoji-btn';
            btn.textContent = emoji;
            btn.type = 'button';
            btn.onclick = () => this.selectEmoji(emoji);
            grid.appendChild(btn);
        });
        
        picker.appendChild(grid);
        document.body.appendChild(picker);
        
        this.picker = picker;
        
        // 点击外部关闭
        document.addEventListener('click', (e) => {
            if (!picker.contains(e.target) && !e.target.closest('.emoji-trigger')) {
                this.hide();
            }
        });
        
        return picker;
    }
    
    /**
     * 显示选择器
     */
    show(triggerElement, targetInput, onSelectCallback) {
        if (!this.picker) {
            this.create();
        }
        
        this.targetInput = targetInput;
        this.onSelect = onSelectCallback;
        
        // 定位到触发元素附近
        const rect = triggerElement.getBoundingClientRect();
        this.picker.style.display = 'block';
        this.picker.style.position = 'fixed';
        this.picker.style.bottom = (window.innerHeight - rect.top + 10) + 'px';
        this.picker.style.left = rect.left + 'px';
        this.picker.style.zIndex = '10000';
    }
    
    /**
     * 隐藏选择器
     */
    hide() {
        if (this.picker) {
            this.picker.style.display = 'none';
        }
    }
    
    /**
     * 选择emoji
     */
    selectEmoji(emoji) {
        if (this.targetInput) {
            // 在光标位置插入emoji
            const start = this.targetInput.selectionStart;
            const end = this.targetInput.selectionEnd;
            const text = this.targetInput.value;
            
            this.targetInput.value = text.substring(0, start) + emoji + text.substring(end);
            
            // 重新设置光标位置
            const newPos = start + emoji.length;
            this.targetInput.selectionStart = newPos;
            this.targetInput.selectionEnd = newPos;
            
            // 触发input事件（用于自动调整高度）
            this.targetInput.dispatchEvent(new Event('input'));
            this.targetInput.focus();
        }
        
        // 调用回调
        if (this.onSelect) {
            this.onSelect(emoji);
        }
        
        this.hide();
    }
}

// 创建全局实例
window.emojiPicker = new EmojiPicker();

