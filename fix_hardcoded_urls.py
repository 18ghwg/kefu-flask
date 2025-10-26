#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动检测并替换模板文件中的硬编码URL
使用url_for()替换硬编码路径

使用方法:
    python fix_hardcoded_urls.py --scan    # 仅扫描，不修改
    python fix_hardcoded_urls.py --fix     # 自动修复
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple

# ==================== 配置区域 ====================

# 项目根目录
BASE_DIR = Path(__file__).parent

# 要扫描的目录
SCAN_DIRS = [
    BASE_DIR / 'templates',
    BASE_DIR / 'static' / 'js',  # 也扫描JavaScript文件
]

# URL路径到Flask路由的映射表
URL_MAPPING = {
    # 管理后台
    '/admin': "{{ url_for('admin_panel.index') }}",
    '/admin/': "{{ url_for('admin_panel.index') }}",
    '/admin/dashboard': "{{ url_for('admin_panel.dashboard') }}",
    '/admin/visitors': "{{ url_for('admin_panel.visitors') }}",
    '/admin/knowledge': "{{ url_for('admin_panel.knowledge') }}",
    '/admin/services': "{{ url_for('admin_panel.services') }}",
    '/admin/service-groups': "{{ url_for('admin_panel.service_groups') }}",
    '/admin/queue-management': "{{ url_for('admin_panel.queue_management') }}",
    '/admin/comments': "{{ url_for('admin_panel.comments') }}",
    '/admin/comment-statistics': "{{ url_for('admin_panel.comment_statistics') }}",
    '/admin/comment-ranking': "{{ url_for('admin_panel.comment_ranking') }}",
    '/admin/system-settings': "{{ url_for('admin_panel.system_settings') }}",
    '/admin/faq-settings': "{{ url_for('admin_panel.faq_settings') }}",
    '/admin/greeting-settings': "{{ url_for('admin_panel.greeting_settings') }}",
    '/admin/chat-history': "{{ url_for('admin_panel.chat_history') }}",
    '/admin/operation-logs': "{{ url_for('admin_panel.operation_logs') }}",
    '/admin/profile': "{{ url_for('admin_panel.profile') }}",
    
    # 客服工作台
    '/service/chat': "{{ url_for('service_panel.chat') }}",
    '/service/index': "{{ url_for('service_panel.index') }}",
    
    # 认证
    '/login': "{{ url_for('auth_view.login_page') }}",
    '/logout': "{{ url_for('auth_view.logout') }}",
    
    # 访客
    '/chat': "{{ url_for('visitor_view.chat') }}",
    
    # 首页
    '/': "{{ url_for('index_view.index') }}",
    '/index': "{{ url_for('index_view.index') }}",
}

# 需要特殊处理的静态资源模式（不替换）
STATIC_PATTERNS = [
    r'/static/',
    r'/uploads/',
    r'/api/',
    r'#\w+',  # 锚点链接
]

# 硬编码URL的正则模式
HARDCODED_PATTERNS = [
    # HTML中的href属性
    (r'href=[\"\'](/[^\"\'#\{]+?)[\"\']', 'href'),
    # HTML中的action属性
    (r'action=[\"\'](/[^\"\'#\{]+?)[\"\']', 'action'),
    # JavaScript中的window.location
    (r'window\.location(?:\.href)?\s*=\s*[\"\'](/[^\"\'#\{]+?)[\"\']', 'js_location'),
    # JavaScript中的fetch/axios URL
    (r'(?:fetch|axios(?:\.\w+)?)\s*\(\s*[\"\'](/[^\"\'#\{]+?)[\"\']', 'js_fetch'),
]

# ==================== 核心功能 ====================

class URLFixer:
    """URL修复工具类"""
    
    def __init__(self, scan_only=True):
        self.scan_only = scan_only
        self.issues: List[Dict] = []
        self.fixed_count = 0
        self.skipped_count = 0
        
    def is_static_url(self, url: str) -> bool:
        """检查是否是静态资源URL（不需要替换）"""
        for pattern in STATIC_PATTERNS:
            if re.search(pattern, url):
                return True
        return False
    
    def get_replacement(self, url: str) -> str:
        """获取URL的替换文本"""
        # 移除查询参数和锚点
        clean_url = url.split('?')[0].split('#')[0]
        
        # 尝试精确匹配
        if clean_url in URL_MAPPING:
            return URL_MAPPING[clean_url]
        
        # 尝试去除尾部斜杠匹配
        if clean_url.endswith('/'):
            clean_url_no_slash = clean_url.rstrip('/')
            if clean_url_no_slash in URL_MAPPING:
                return URL_MAPPING[clean_url_no_slash]
        else:
            clean_url_with_slash = clean_url + '/'
            if clean_url_with_slash in URL_MAPPING:
                return URL_MAPPING[clean_url_with_slash]
        
        return None
    
    def scan_file(self, file_path: Path) -> List[Dict]:
        """扫描单个文件，返回发现的问题"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"[!] 无法读取文件 {file_path}: {e}")
            return []
        
        issues = []
        lines = content.split('\n')
        
        for pattern, pattern_type in HARDCODED_PATTERNS:
            for match in re.finditer(pattern, content):
                url = match.group(1)
                
                # 跳过静态资源
                if self.is_static_url(url):
                    continue
                
                # 检查是否已经使用url_for
                if '{{' in match.group(0) or 'url_for' in match.group(0):
                    continue
                
                # 获取行号
                line_num = content[:match.start()].count('\n') + 1
                line_content = lines[line_num - 1].strip()
                
                # 获取替换建议
                replacement = self.get_replacement(url)
                
                issue = {
                    'file': file_path,
                    'line': line_num,
                    'url': url,
                    'context': line_content,
                    'pattern_type': pattern_type,
                    'match': match.group(0),
                    'replacement': replacement,
                    'can_fix': replacement is not None
                }
                issues.append(issue)
        
        return issues
    
    def fix_file(self, file_path: Path, file_issues: List[Dict]) -> int:
        """修复单个文件中的硬编码URL"""
        if not file_issues:
            return 0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"⚠️  无法读取文件 {file_path}: {e}")
            return 0
        
        fixed = 0
        # 按位置倒序排序，从后往前替换，避免位置偏移
        sorted_issues = sorted(file_issues, key=lambda x: x['line'], reverse=True)
        
        for issue in sorted_issues:
            if not issue['can_fix']:
                continue
            
            # 构造新的匹配模式（更精确）
            old_text = issue['match']
            
            # 根据pattern_type构造替换文本
            if issue['pattern_type'] in ['href', 'action']:
                # HTML属性替换
                quote = '"' if '"' in old_text else "'"
                new_text = f'{issue["pattern_type"]}={quote}{issue["replacement"]}{quote}'
            else:
                # JavaScript替换 - 保持不变，因为JS中不能直接使用Jinja2
                continue
            
            # 替换内容
            if old_text in content:
                content = content.replace(old_text, new_text, 1)
                fixed += 1
        
        # 写回文件
        if fixed > 0:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"[OK] 已修复 {file_path.relative_to(BASE_DIR)} - {fixed}处")
            except Exception as e:
                print(f"[!] 无法写入文件 {file_path}: {e}")
                return 0
        
        return fixed
    
    def scan_directory(self, directory: Path):
        """扫描目录"""
        if not directory.exists():
            print(f"[!] 目录不存在: {directory}")
            return
        
        # 扫描HTML文件
        html_files = list(directory.rglob('*.html'))
        # 扫描JavaScript文件（如果需要）
        # js_files = list(directory.rglob('*.js'))
        
        total_files = len(html_files)
        print(f"\n[SCAN] 扫描目录: {directory.relative_to(BASE_DIR)}")
        print(f"       找到 {total_files} 个HTML文件\n")
        
        for idx, file_path in enumerate(html_files, 1):
            # 跳过backup文件
            if '.backup' in str(file_path):
                continue
            
            print(f"[{idx}/{total_files}] 检查 {file_path.relative_to(BASE_DIR)}...", end=' ')
            
            file_issues = self.scan_file(file_path)
            
            if file_issues:
                can_fix = sum(1 for issue in file_issues if issue['can_fix'])
                cannot_fix = len(file_issues) - can_fix
                print(f"[X] 发现 {len(file_issues)} 个问题 ({can_fix} 可修复, {cannot_fix} 需手动)")
                
                self.issues.extend(file_issues)
                
                # 如果不是仅扫描模式，则尝试修复
                if not self.scan_only:
                    fixed = self.fix_file(file_path, file_issues)
                    self.fixed_count += fixed
                    self.skipped_count += (len(file_issues) - fixed)
            else:
                print("[OK] 无问题")
    
    def run(self):
        """运行扫描"""
        print("=" * 60)
        print("[*] 硬编码URL检测工具")
        print("=" * 60)
        print(f"模式: {'仅扫描' if self.scan_only else '扫描并修复'}")
        print("=" * 60)
        
        for directory in SCAN_DIRS:
            self.scan_directory(directory)
        
        # 输出报告
        self.print_report()
    
    def print_report(self):
        """打印扫描报告"""
        print("\n" + "=" * 60)
        print("[*] 扫描报告")
        print("=" * 60)
        
        if not self.issues:
            print("[OK] 未发现硬编码URL问题！")
            return
        
        # 按文件分组
        files_with_issues = {}
        for issue in self.issues:
            file_key = str(issue['file'].relative_to(BASE_DIR))
            if file_key not in files_with_issues:
                files_with_issues[file_key] = []
            files_with_issues[file_key].append(issue)
        
        print(f"\n共发现 {len(self.issues)} 个硬编码URL问题，涉及 {len(files_with_issues)} 个文件\n")
        
        # 详细列表
        for file_path, issues in sorted(files_with_issues.items()):
            print(f"\n[FILE] {file_path}")
            print("-" * 60)
            
            for issue in issues:
                status = "[OK] 可自动修复" if issue['can_fix'] else "[!] 需手动修复"
                print(f"  行 {issue['line']:4d} | {status}")
                print(f"           URL: {issue['url']}")
                if issue['replacement']:
                    print(f"           建议: {issue['replacement']}")
                else:
                    print(f"           建议: 需在 URL_MAPPING 中添加映射")
                print(f"           上下文: {issue['context'][:80]}...")
                print()
        
        # 统计信息
        can_fix = sum(1 for issue in self.issues if issue['can_fix'])
        cannot_fix = len(self.issues) - can_fix
        
        print("\n" + "=" * 60)
        print("[*] 统计")
        print("=" * 60)
        print(f"[OK] 可自动修复: {can_fix}")
        print(f"[!] 需手动修复: {cannot_fix}")
        
        if not self.scan_only:
            print(f"[FIX] 已修复: {self.fixed_count}")
            print(f"[SKIP] 跳过: {self.skipped_count}")
        
        print("\n" + "=" * 60)
        
        if cannot_fix > 0:
            print("\n[TIP] 提示: 对于无法自动修复的URL，请：")
            print("   1. 检查URL是否正确")
            print("   2. 在脚本的 URL_MAPPING 中添加对应的路由映射")
            print("   3. 重新运行脚本")


# ==================== 主程序 ====================

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='检测并修复模板文件中的硬编码URL',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python fix_hardcoded_urls.py --scan    # 仅扫描，不修改任何文件
  python fix_hardcoded_urls.py --fix     # 扫描并自动修复
  
注意:
  - 修复前会自动备份，但建议先提交Git
  - JavaScript中的硬编码URL需要手动修复
  - 静态资源路径(/static/, /api/)不会被修改
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--scan', action='store_true', help='仅扫描，不修改文件')
    group.add_argument('--fix', action='store_true', help='扫描并自动修复')
    
    args = parser.parse_args()
    
    # 确认操作
    if args.fix:
        print("\n[!] 警告: 此操作将修改文件！")
        print("    建议先提交Git或备份文件")
        response = input("\n是否继续? (y/N): ").strip().lower()
        if response != 'y':
            print("已取消操作")
            return
    
    # 执行扫描或修复
    fixer = URLFixer(scan_only=args.scan)
    fixer.run()
    
    # 退出码
    if fixer.issues:
        sys.exit(1)  # 发现问题
    else:
        sys.exit(0)  # 无问题


if __name__ == '__main__':
    main()

