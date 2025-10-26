/**
 * CSRF Token 处理模块
 * 自动为所有AJAX请求添加CSRF Token
 */

(function() {
    'use strict';
    
    // 全局CSRF Token存储
    let csrfToken = null;
    
    /**
     * 从Cookie中获取CSRF Token
     */
    function getCsrfTokenFromCookie() {
        const name = 'csrf_token=';
        const decodedCookie = decodeURIComponent(document.cookie);
        const cookieArray = decodedCookie.split(';');
        
        for (let i = 0; i < cookieArray.length; i++) {
            let cookie = cookieArray[i].trim();
            if (cookie.indexOf(name) === 0) {
                return cookie.substring(name.length, cookie.length);
            }
        }
        return null;
    }
    
    /**
     * 从meta标签中获取CSRF Token
     */
    function getCsrfTokenFromMeta() {
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        return metaTag ? metaTag.getAttribute('content') : null;
    }
    
    /**
     * 从服务器获取CSRF Token
     */
    async function fetchCsrfToken() {
        try {
            const response = await fetch('/api/csrf-token', {
                method: 'GET',
                credentials: 'same-origin'
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.code === 0 && data.csrf_token) {
                    csrfToken = data.csrf_token;
                    console.log('✅ CSRF Token已获取');
                    return csrfToken;
                }
            }
        } catch (error) {
            console.error('❌ 获取CSRF Token失败:', error);
        }
        return null;
    }
    
    /**
     * 获取CSRF Token（优先级：内存 > Cookie > Meta > 服务器）
     */
    async function getCsrfToken() {
        // 1. 从内存中获取
        if (csrfToken) {
            return csrfToken;
        }
        
        // 2. 从Cookie中获取
        const cookieToken = getCsrfTokenFromCookie();
        if (cookieToken) {
            csrfToken = cookieToken;
            return csrfToken;
        }
        
        // 3. 从Meta标签中获取
        const metaToken = getCsrfTokenFromMeta();
        if (metaToken) {
            csrfToken = metaToken;
            return csrfToken;
        }
        
        // 4. 从服务器获取
        return await fetchCsrfToken();
    }
    
    /**
     * 为请求添加CSRF Token头部
     */
    function addCsrfHeader(headers = {}) {
        if (csrfToken) {
            headers['X-CSRFToken'] = csrfToken;
        }
        return headers;
    }
    
    /**
     * 封装fetch，自动添加CSRF Token
     */
    const originalFetch = window.fetch;
    window.fetch = async function(url, options = {}) {
        // 对于需要CSRF验证的请求（POST/PUT/PATCH/DELETE）
        const method = (options.method || 'GET').toUpperCase();
        const needsCsrf = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method);
        
        if (needsCsrf) {
            // 确保有CSRF Token
            if (!csrfToken) {
                await getCsrfToken();
            }
            
            // 添加CSRF Token到请求头
            options.headers = options.headers || {};
            if (csrfToken) {
                options.headers['X-CSRFToken'] = csrfToken;
            }
            
            // 确保credentials设置正确（需要发送cookie）
            if (!options.credentials) {
                options.credentials = 'same-origin';
            }
        }
        
        return originalFetch(url, options);
    };
    
    /**
     * 为jQuery AJAX添加CSRF Token支持（如果使用了jQuery）
     */
    if (window.jQuery) {
        jQuery.ajaxSetup({
            beforeSend: function(xhr, settings) {
                // 对于需要CSRF验证的请求
                const method = settings.type.toUpperCase();
                const needsCsrf = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method);
                
                if (needsCsrf && csrfToken) {
                    xhr.setRequestHeader('X-CSRFToken', csrfToken);
                }
            }
        });
    }
    
    /**
     * 为表单添加CSRF Token隐藏字段
     */
    function addCsrfToForms() {
        const forms = document.querySelectorAll('form[method="post"], form[method="POST"]');
        forms.forEach(form => {
            // 检查是否已经有CSRF Token字段
            let csrfInput = form.querySelector('input[name="csrf_token"]');
            
            if (!csrfInput) {
                // 创建隐藏的CSRF Token字段
                csrfInput = document.createElement('input');
                csrfInput.type = 'hidden';
                csrfInput.name = 'csrf_token';
                form.appendChild(csrfInput);
            }
            
            // 设置CSRF Token值
            if (csrfToken) {
                csrfInput.value = csrfToken;
            }
        });
    }
    
    /**
     * 初始化CSRF保护
     */
    async function initCsrfProtection() {
        console.log('🔐 初始化CSRF保护...');
        
        // 获取CSRF Token
        await getCsrfToken();
        
        // 为现有表单添加CSRF Token
        addCsrfToForms();
        
        // 监听DOM变化，为新添加的表单自动添加CSRF Token
        const observer = new MutationObserver(() => {
            addCsrfToForms();
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
        
        console.log('✅ CSRF保护已启用');
    }
    
    // 页面加载完成后初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCsrfProtection);
    } else {
        initCsrfProtection();
    }
    
    // 暴露全局接口
    window.CSRF = {
        getToken: getCsrfToken,
        addHeader: addCsrfHeader,
        refresh: fetchCsrfToken
    };
    
})();

