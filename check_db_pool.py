#!/usr/bin/env python3
"""
数据库连接池健康检查工具
用于诊断和监控连接池状态
"""
import sys
from app import app, db
from sqlalchemy import inspect

def check_pool_status():
    """检查数据库连接池状态"""
    with app.app_context():
        engine = db.engine
        pool = engine.pool
        
        print("=" * 60)
        print("数据库连接池状态检查")
        print("=" * 60)
        
        # 连接池配置
        print("\n【连接池配置】")
        print(f"  连接池大小 (pool_size): {pool.size()}")
        print(f"  最大溢出 (max_overflow): {pool._max_overflow}")
        print(f"  总容量: {pool.size() + pool._max_overflow}")
        print(f"  连接超时 (timeout): {pool._timeout}秒")
        
        # 当前状态
        print("\n【当前状态】")
        print(f"  已签出连接 (checked out): {pool.checkedout()}")
        print(f"  可用连接 (available): {pool.size() - pool.checkedout()}")
        print(f"  溢出连接 (overflow): {pool.overflow()}")
        
        # 健康评估
        print("\n【健康评估】")
        utilization = (pool.checkedout() / (pool.size() + pool._max_overflow)) * 100
        print(f"  连接池利用率: {utilization:.1f}%")
        
        if utilization > 90:
            print("  ⚠️  警告：连接池利用率过高，可能即将耗尽！")
        elif utilization > 70:
            print("  ⚠️  注意：连接池利用率较高")
        else:
            print("  ✅ 连接池状态正常")
        
        # 测试连接
        print("\n【连接测试】")
        try:
            result = db.session.execute(db.text("SELECT 1"))
            result.fetchone()
            db.session.commit()
            print("  ✅ 数据库连接正常")
        except Exception as e:
            print(f"  ❌ 数据库连接失败: {e}")
            return False
        
        print("\n" + "=" * 60)
        return True

if __name__ == '__main__':
    try:
        success = check_pool_status()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
