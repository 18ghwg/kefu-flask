#!/usr/bin/env python3
"""
Git Clean Filter for config.py
自动清理config.py中的敏感信息

用途：
- 在git add时自动将敏感配置值替换为空字符串
- 本地config.py保持不变，只影响提交到Git的版本

使用方法：
1. 配置 .gitattributes: config.py filter=clean-config
2. 配置 git config: filter.clean-config.clean "python clean_config.py"
"""
import sys
import re

def clean_config(content):
    """清理config.py中的敏感信息"""
    
    # 定义需要清理的配置项（将值替换为空字符串）
    sensitive_patterns = [
        # 数据库配置
        (r"(HOSTNAME\s*=\s*)['\"].*?['\"]", r"\1''"),
        (r"(PORT\s*=\s*)['\"].*?['\"]", r"\1''"),
        (r"(DATABASE\s*=\s*)['\"].*?['\"]", r"\1''"),
        (r"(USERNAME\s*=\s*)['\"].*?['\"]", r"\1''"),
        (r"(PASSWORD\s*=\s*)['\"].*?['\"]", r"\1''"),
        
        # 密钥配置
        (r"(SECRET_KEY\s*=\s*)['\"].*?['\"]", r"\1'your-secret-key-here'"),
        (r"(API_SIGNATURE_SECRET\s*=\s*)['\"].*?['\"]", r"\1'your-api-secret-here'"),
        (r"(PASSWORD_SALT\s*=\s*)['\"].*?['\"]", r"\1'your-password-salt-here'"),
        
        # Redis配置（可选）
        # (r"(REDIS_HOST\s*=\s*os\.getenv\(['\"]REDIS_HOST['\"],\s*)['\"].*?['\"]", r"\1'localhost'"),
        # (r"(REDIS_PASSWORD\s*=\s*os\.getenv\(['\"]REDIS_PASSWORD['\"],\s*)['\"].*?['\"]", r"\1''"),
        
        # 其他敏感配置（可选）
        # (r"(WECHAT_API_URL\s*=\s*)['\"].*?['\"]", r"\1'http://localhost:5603/send'"),
    ]
    
    result = content
    for pattern, replacement in sensitive_patterns:
        result = re.sub(pattern, replacement, result)
    
    return result

if __name__ == '__main__':
    # 从stdin读取文件内容
    content = sys.stdin.read()
    
    # 清理敏感信息
    cleaned = clean_config(content)
    
    # 输出到stdout（Git会捕获这个输出）
    sys.stdout.write(cleaned)

