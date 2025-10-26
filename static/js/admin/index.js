/**
 * 管理后台首页 - Script
 */

// 检测是否是移动端
        function isMobile() {
            return window.innerWidth <= 768;
        }
        
        // 切换侧边栏
        function toggleSidebar() {
            const sidebar = document.getElementById('sidebar');
            const mainContent = document.getElementById('mainContent');
            const overlay = document.getElementById('sidebarOverlay');
            
            if (isMobile()) {
                // 移动端：显示/隐藏侧边栏
                sidebar.classList.toggle('mobile-show');
                overlay.classList.toggle('show');
            } else {
                // PC端：折叠/展开侧边栏
                sidebar.classList.toggle('collapsed');
                mainContent.classList.toggle('expanded');
            }
        }
        
        // 关闭移动端侧边栏
        function closeMobileSidebar() {
            if (isMobile()) {
                const sidebar = document.getElementById('sidebar');
                const overlay = document.getElementById('sidebarOverlay');
                sidebar.classList.remove('mobile-show');
                overlay.classList.remove('show');
            }
        }
        
        // 切换子菜单
        function toggleSubmenu(element) {
            const submenu = element.nextElementSibling;
            const arrow = element.querySelector('.menu-arrow');
            
            // 关闭其他子菜单
            document.querySelectorAll('.submenu').forEach(menu => {
                if (menu !== submenu && menu.classList.contains('show')) {
                    menu.classList.remove('show');
                    menu.previousElementSibling.querySelector('.menu-arrow').style.transform = 'rotate(0deg)';
                }
            });
            
            // 切换当前子菜单
            submenu.classList.toggle('show');
            
            if (submenu.classList.contains('show')) {
                arrow.style.transform = 'rotate(180deg)';
            } else {
                arrow.style.transform = 'rotate(0deg)';
            }
        }
        
        // 监听窗口大小变化
        window.addEventListener('resize', function() {
            const sidebar = document.getElementById('sidebar');
            const mainContent = document.getElementById('mainContent');
            const overlay = document.getElementById('sidebarOverlay');
            
            if (!isMobile()) {
                // 切换到PC端时，移除移动端相关类
                sidebar.classList.remove('mobile-show');
                overlay.classList.remove('show');
            } else {
                // 切换到移动端时，重置PC端折叠状态
                sidebar.classList.remove('collapsed');
                mainContent.classList.remove('expanded');
            }
        });
        
        // 点击子菜单项后，如果是移动端则关闭侧边栏
        document.querySelectorAll('.submenu-link').forEach(link => {
            link.addEventListener('click', function() {
                closeMobileSidebar();
            });
        });