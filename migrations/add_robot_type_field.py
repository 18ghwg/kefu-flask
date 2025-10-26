"""
添加机器人类型字段，区分常见问题和智能关键词
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def upgrade():
    """添加 type 字段"""
    from exts import app, db
    
    with app.app_context():
        try:
            # 添加 type 字段
            with db.engine.connect() as conn:
                # 检查字段是否已存在
                result = conn.execute(db.text("""
                    SELECT COUNT(*) as count
                    FROM information_schema.COLUMNS 
                    WHERE TABLE_SCHEMA = DATABASE()
                    AND TABLE_NAME = 'robots' 
                    AND COLUMN_NAME = 'type'
                """))
                exists = result.fetchone()[0] > 0
                
                if exists:
                    print("⚠️  type 字段已存在，跳过添加")
                else:
                    conn.execute(db.text("""
                        ALTER TABLE robots 
                        ADD COLUMN `type` VARCHAR(20) DEFAULT 'keyword' 
                        COMMENT '类型：faq-常见问题，keyword-智能关键词' 
                        AFTER `status`
                    """))
                    conn.commit()
                    print("✅ 成功添加 type 字段")
                
                # 将现有数据默认设置为 keyword
                conn.execute(db.text("UPDATE robots SET type = 'keyword' WHERE type IS NULL OR type = ''"))
                conn.commit()
                print("✅ 已更新现有数据")
                
        except Exception as e:
            print(f"❌ 添加字段失败: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()

def downgrade():
    """移除 type 字段"""
    from exts import app, db
    
    with app.app_context():
        try:
            with db.engine.connect() as conn:
                conn.execute(db.text("ALTER TABLE robots DROP COLUMN `type`"))
                conn.commit()
                print("✅ 成功移除 type 字段")
        except Exception as e:
            print(f"❌ 移除字段失败: {e}")

if __name__ == '__main__':
    print("开始执行数据库迁移...")
    upgrade()
    print("迁移完成！")

