#!/usr/bin/env python3
"""
数据库连接修复工具
用于清理泄漏的数据库连接
"""
from app import app, db
import time

def fix_connections():
    """修复数据库连接"""
    with app.app_context():
        print("=" * 60)
        print("数据库连接修复工具")
        print("=" * 60)
        
        engine = db.engine
        pool = engine.pool
        
        # 显示当前状态
        print(f"\n修复前状态:")
        print(f"  已签出连接: {pool.checkedout()}")
        print(f"  可用连接: {pool.size() - pool.checkedout()}")
        print(f"  溢出连接: {pool.overflow()}")
        
        # 方法1: 清理所有会话
        print("\n正在清理数据库会话...")
        try:
            db.session.remove()
            print("  ✅ 会话清理完成")
        except Exception as e:
            print(f"  ⚠️  会话清理失败: {e}")
        
        # 方法2: 回收所有连接
        print("\n正在回收连接池...")
        try:
            pool.dispose()
            print("  ✅ 连接池已重置")
        except Exception as e:
            print(f"  ⚠️  连接池重置失败: {e}")
        
        # 等待一下让连接完全释放
        time.sleep(1)
        
        # 显示修复后状态
        print(f"\n修复后状态:")
        print(f"  已签出连接: {pool.checkedout()}")
        print(f"  可用连接: {pool.size() - pool.checkedout()}")
        print(f"  溢出连接: {pool.overflow()}")
        
        # 测试连接
        print("\n测试数据库连接...")
        try:
            result = db.session.execute(db.text("SELECT 1"))
            result.fetchone()
            db.session.commit()
            print("  ✅ 数据库连接正常")
        except Exception as e:
            print(f"  ❌ 数据库连接失败: {e}")
            return False
        
        print("\n" + "=" * 60)
        print("✅ 修复完成！")
        print("=" * 60)
        return True

if __name__ == '__main__':
    try:
        fix_connections()
    except Exception as e:
        print(f"\n❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()
