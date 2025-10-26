/**
 * 主题管理器
 * 支持多主题切换和持久化保存
 */

const ThemeManager = {
    // 可用的主题配置
    themes: {
        blue: {
            name: '深蓝商务',
            icon: '💼',
            colors: {
                '--primary-color': '#1e40af',
                '--primary-hover-color': '#1e3a8a',
                '--primary-light-color': '#3b82f6',
                '--primary-bg-color': '#eff6ff'
            }
        },
        green: {
            name: '清新绿色',
            icon: '🍃',
            colors: {
                '--primary-color': '#059669',
                '--primary-hover-color': '#047857',
                '--primary-light-color': '#10b981',
                '--primary-bg-color': '#d1fae5'
            }
        },
        purple: {
            name: '优雅紫色',
            icon: '💜',
            colors: {
                '--primary-color': '#7c3aed',
                '--primary-hover-color': '#6d28d9',
                '--primary-light-color': '#8b5cf6',
                '--primary-bg-color': '#ede9fe'
            }
        },
        orange: {
            name: '活力橙色',
            icon: '🧡',
            colors: {
                '--primary-color': '#ea580c',
                '--primary-hover-color': '#c2410c',
                '--primary-light-color': '#f97316',
                '--primary-bg-color': '#ffedd5'
            }
        },
        pink: {
            name: '浪漫粉色',
            icon: '💗',
            colors: {
                '--primary-color': '#db2777',
                '--primary-hover-color': '#be185d',
                '--primary-light-color': '#ec4899',
                '--primary-bg-color': '#fce7f3'
            }
        },
        cyan: {
            name: '科技青色',
            icon: '🌊',
            colors: {
                '--primary-color': '#0891b2',
                '--primary-hover-color': '#0e7490',
                '--primary-light-color': '#06b6d4',
                '--primary-bg-color': '#cffafe'
            }
        },
        red: {
            name: '热情红色',
            icon: '❤️',
            colors: {
                '--primary-color': '#dc2626',
                '--primary-hover-color': '#b91c1c',
                '--primary-light-color': '#ef4444',
                '--primary-bg-color': '#fee2e2'
            }
        },
        indigo: {
            name: '深邃靛蓝',
            icon: '🌌',
            colors: {
                '--primary-color': '#4f46e5',
                '--primary-hover-color': '#4338ca',
                '--primary-light-color': '#6366f1',
                '--primary-bg-color': '#e0e7ff'
            }
        }
    },

    // 当前主题
    currentTheme: 'green', // 默认绿色

    // 初始化
    init() {
        // 从localStorage读取用户选择的主题
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme && this.themes[savedTheme]) {
            this.currentTheme = savedTheme;
        }
        
        // 应用主题
        this.applyTheme(this.currentTheme);
        
        // 监听主题切换事件
        this.bindEvents();
    },

    // 应用主题
    applyTheme(themeName) {
        const theme = this.themes[themeName];
        if (!theme) {
            console.error(`主题 ${themeName} 不存在`);
            return;
        }

        // 设置CSS变量
        const root = document.documentElement;
        Object.entries(theme.colors).forEach(([key, value]) => {
            root.style.setProperty(key, value);
        });

        // 保存到localStorage
        localStorage.setItem('theme', themeName);
        this.currentTheme = themeName;

        // 触发主题改变事件
        window.dispatchEvent(new CustomEvent('themeChanged', { 
            detail: { theme: themeName, colors: theme.colors }
        }));

        console.log(`✅ 主题已切换为: ${theme.name}`);
    },

    // 切换主题
    switchTheme(themeName) {
        this.applyTheme(themeName);
        
        // 显示提示
        this.showToast(`主题已切换为: ${this.themes[themeName].name}`);
    },

    // 获取当前主题
    getCurrentTheme() {
        return this.currentTheme;
    },

    // 获取所有主题
    getAllThemes() {
        return this.themes;
    },

    // 绑定事件
    bindEvents() {
        // 监听主题选择器的变化
        document.addEventListener('change', (e) => {
            if (e.target.id === 'themeSelector') {
                this.switchTheme(e.target.value);
            }
        });

        // 监听主题按钮点击
        document.addEventListener('click', (e) => {
            if (e.target.closest('.theme-option')) {
                const themeName = e.target.closest('.theme-option').dataset.theme;
                this.switchTheme(themeName);
            }
        });
    },

    // 显示提示消息
    showToast(message) {
        // 检查是否已有toast容器
        let toast = document.getElementById('theme-toast');
        
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'theme-toast';
            toast.style.cssText = `
                position: fixed;
                top: 80px;
                right: 20px;
                background: rgba(15, 23, 42, 0.95);
                color: white;
                padding: 12px 20px;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                z-index: 10000;
                opacity: 0;
                transform: translateX(100%);
                transition: all 0.3s ease;
                font-size: 14px;
                font-weight: 500;
            `;
            document.body.appendChild(toast);
        }

        toast.textContent = message;
        
        // 显示
        setTimeout(() => {
            toast.style.opacity = '1';
            toast.style.transform = 'translateX(0)';
        }, 10);

        // 3秒后隐藏
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
        }, 3000);
    }
};

// 页面加载完成后初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => ThemeManager.init());
} else {
    ThemeManager.init();
}

// 导出到全局
window.ThemeManager = ThemeManager;

