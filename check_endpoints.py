#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速检查所有endpoint是否正确
"""
import os
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent

# 已知的正确endpoint列表（从app.py中提取）
VALID_ENDPOINTS = {
    'admin_panel.index',
    'admin_panel.dashboard',
    'admin_panel.visitors',
    'admin_panel.knowledge',
    'admin_panel.services',
    'admin_panel.service_groups',
    'admin_panel.queue_management',
    'admin_panel.comments',
    'admin_panel.comment_statistics',
    'admin_panel.comment_ranking',
    'admin_panel.system_settings',
    'admin_panel.faq_settings',
    'admin_panel.greeting_settings',
    'admin_panel.chat_history',
    'admin_panel.operation_logs',
    'admin_panel.profile',
    'service_panel.chat',
    'service_panel.index',
    'auth_view.login',  # 正确的endpoint
    'auth_view.logout',
    'visitor_view.chat',
    'index_view.index',
    'index_view.home',
}

# 错误的endpoint（需要修复）
INVALID_ENDPOINTS = {
    'auth_view.login_page',  # 错误！应该是 auth_view.login
}

def scan_templates():
    """扫描所有模板文件中的url_for调用"""
    templates_dir = BASE_DIR / 'templates'
    pattern = r"url_for\(['\"]([^'\"]+)['\"]\)"
    
    issues = []
    all_endpoints = set()
    
    for html_file in templates_dir.rglob('*.html'):
        if '.backup' in str(html_file):
            continue
            
        try:
            content = html_file.read_text(encoding='utf-8')
            matches = re.findall(pattern, content)
            
            for endpoint in matches:
                all_endpoints.add(endpoint)
                
                # 检查是否是无效的endpoint
                if endpoint in INVALID_ENDPOINTS:
                    issues.append({
                        'file': html_file.relative_to(BASE_DIR),
                        'endpoint': endpoint,
                        'type': 'INVALID'
                    })
                # 检查是否是未知的endpoint
                elif endpoint not in VALID_ENDPOINTS:
                    issues.append({
                        'file': html_file.relative_to(BASE_DIR),
                        'endpoint': endpoint,
                        'type': 'UNKNOWN'
                    })
        except Exception as e:
            print(f"[!] 读取文件失败: {html_file}: {e}")
    
    return issues, all_endpoints

def main():
    print("=" * 60)
    print("[*] Endpoint 检查工具")
    print("=" * 60)
    
    issues, all_endpoints = scan_templates()
    
    if not issues:
        print("\n[OK] 所有endpoint都正确！\n")
        print("发现的endpoint:")
        for endpoint in sorted(all_endpoints):
            print(f"  - {endpoint}")
    else:
        print(f"\n[!] 发现 {len(issues)} 个问题:\n")
        
        for issue in issues:
            print(f"[{issue['type']}] {issue['file']}")
            print(f"         Endpoint: {issue['endpoint']}")
            if issue['type'] == 'INVALID':
                print(f"         建议: 这是一个已知的错误endpoint，需要修复！")
            else:
                print(f"         建议: 请确认此endpoint是否在app.py中注册")
            print()
    
    print("=" * 60)
    return 0 if not issues else 1

if __name__ == '__main__':
    import sys
    sys.exit(main())

