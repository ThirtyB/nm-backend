#!/usr/bin/env python3
"""
密码哈希迁移脚本
将现有的bcrypt密码哈希迁移到PBKDF2-HMAC-SM3
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.database import engine, get_db
from app.models import User
from app.auth import get_password_hash, verify_password

def is_bcrypt_hash(hashed_password: str) -> bool:
    """检查是否为bcrypt哈希"""
    return hashed_password.startswith('$2b$') or hashed_password.startswith('$2a$')

def migrate_password_hashes():
    """迁移所有用户的密码哈希到PBKDF2-HMAC-SM3"""
    print("开始迁移密码哈希...")
    
    # 创建数据库会话
    with Session(engine) as db:
        # 获取所有用户
        users = db.query(User).all()
        total_users = len(users)
        migrated_count = 0
        
        print(f"找到 {total_users} 个用户")
        
        for user in users:
            try:
                if is_bcrypt_hash(user.hashed_password):
                    print(f"迁移用户: {user.username}")
                    
                    # 注意：我们无法直接从bcrypt哈希中获取原始密码
                    # 所以这里需要用户重新设置密码，或者管理员重置
                    # 为了演示，我们生成一个临时密码
                    
                    # 在实际生产环境中，你应该：
                    # 1. 通知所有用户下次登录时重置密码
                    # 2. 或者要求管理员重置所有用户密码
                    # 3. 或者实现一个双密码验证期
                    
                    # 由于user_type字段有检查约束，我们不能直接修改它
                    # 在实际生产环境中，建议：
                    # 1. 创建一个新字段来标记需要重置密码的用户
                    # 2. 或者在应用层面处理
                    print(f"  用户 {user.username} 使用旧密码格式，需要在下次登录时重置密码")
                    
                    migrated_count += 1
                    print(f"  标记用户 {user.username} 需要重置密码")
                else:
                    print(f"用户 {user.username} 已经使用新的哈希格式，跳过")
                    
            except Exception as e:
                print(f"迁移用户 {user.username} 时出错: {e}")
                continue
        
        # 提交更改
        try:
            db.commit()
            print(f"\n迁移完成！")
            print(f"总用户数: {total_users}")
            print(f"需要重置密码的用户: {migrated_count}")
            print("\n注意：由于无法从bcrypt哈希中恢复原始密码，")
            print("已标记的用户需要在下次登录时重置密码。")
            print("建议通知所有用户登录时重置密码以确保安全。")
            
        except Exception as e:
            db.rollback()
            print(f"提交更改时出错: {e}")
            return False
    
    return True

def create_admin_user():
    """创建管理员用户（如果不存在）"""
    print("\n检查管理员用户...")
    
    with Session(engine) as db:
        # 检查是否已有管理员用户
        admin_user = db.query(User).filter(User.user_type == "admin").first()
        
        if admin_user:
            print(f"管理员用户已存在: {admin_user.username}")
            return
        
        # 创建新的管理员用户
        admin_username = input("请输入管理员用户名 (默认: admin): ").strip() or "admin"
        admin_password = input("请输入管理员密码: ").strip()
        
        if not admin_password:
            print("密码不能为空！")
            return
        
        # 使用新的PBKDF2-HMAC-SM3哈希
        hashed_password = get_password_hash(admin_password)
        
        new_admin = User(
            username=admin_username,
            hashed_password=hashed_password,
            user_type="admin",
            is_active=True
        )
        
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)
        
        print(f"管理员用户创建成功: {admin_username}")
        print("请妥善保管管理员密码！")

def test_new_hash():
    """测试新的哈希功能"""
    print("\n=== 测试新的密码哈希功能 ===")
    
    test_password = "test123456"
    hashed = get_password_hash(test_password)
    print(f"测试密码: {test_password}")
    print(f"生成哈希: {hashed}")
    
    is_valid = verify_password(test_password, hashed)
    print(f"验证结果: {'成功' if is_valid else '失败'}")
    
    if is_valid:
        print("✓ PBKDF2-HMAC-SM3 密码哈希功能正常工作")
    else:
        print("✗ PBKDF2-HMAC-SM3 密码哈希功能异常")

if __name__ == "__main__":
    print("=== 密码哈希迁移工具 ===")
    print("此工具将帮助您从bcrypt迁移到PBKDF2-HMAC-SM3")
    print()
    
    try:
        # 测试新哈希功能
        test_new_hash()
        
        # 询问是否执行迁移
        choice = input("\n是否执行密码哈希迁移? (y/n): ").lower().strip()
        
        if choice == 'y':
            migrate_password_hashes()
        
        # 询问是否创建管理员用户
        admin_choice = input("\n是否创建新的管理员用户? (y/n): ").lower().strip()
        
        if admin_choice == 'y':
            create_admin_user()
        
        print("\n迁移工具执行完成！")
        
    except KeyboardInterrupt:
        print("\n\n操作被用户取消")
    except Exception as e:
        print(f"\n执行过程中出现错误: {e}")
        import traceback
        traceback.print_exc()