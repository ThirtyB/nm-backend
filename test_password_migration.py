#!/usr/bin/env python3
"""
测试密码迁移和登录功能
"""
import sys
import os
import requests
import json

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.database import engine
from app.models import User
from app.auth import get_password_hash, verify_password, is_bcrypt_hash

def test_password_migration():
    """测试密码迁移功能"""
    print("=== 测试密码迁移功能 ===\n")
    
    # 创建测试用户
    with Session(engine) as db:
        # 删除已存在的测试用户
        test_user = db.query(User).filter(User.username == "test_migration").first()
        if test_user:
            db.delete(test_user)
            db.commit()
        
        # 创建使用bcrypt哈希的测试用户
        import bcrypt
        test_password = "test123456"
        salt = bcrypt.gensalt()
        bcrypt_hash = bcrypt.hashpw(test_password.encode('utf-8'), salt).decode('utf-8')
        
        new_user = User(
            username="test_migration",
            hashed_password=bcrypt_hash,
            user_type="user",
            is_active=True
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        print(f"创建测试用户: test_migration")
        print(f"使用bcrypt哈希: {bcrypt_hash[:50]}...")
        
        # 验证是bcrypt哈希
        is_bcrypt = is_bcrypt_hash(new_user.hashed_password)
        print(f"是bcrypt哈希: {'✓' if is_bcrypt else '✗'}")
        
        # 验证密码
        is_valid = verify_password(test_password, new_user.hashed_password)
        print(f"密码验证: {'✓' if is_valid else '✗'}")
        
        return new_user.id

def test_api_login():
    """测试API登录和自动迁移"""
    print("\n=== 测试API登录和自动迁移 ===\n")
    
    # 启动服务器（如果还没启动）
    import subprocess
    import time
    import threading
    
    # 检查服务器是否运行
    try:
        response = requests.get("http://localhost:8000/docs", timeout=2)
        server_running = True
        print("✓ 服务器已运行")
    except:
        server_running = False
        print("✗ 服务器未运行，请先启动服务器:")
        print("  python start_server.py")
        return
    
    if server_running:
        # 测试登录
        login_data = {
            "username": "test_migration",
            "password": "test123456"
        }
        
        try:
            response = requests.post(
                "http://localhost:8000/auth/login",
                json=login_data,
                timeout=10
            )
            
            if response.status_code == 200:
                token_data = response.json()
                print("✓ 登录成功")
                print(f"获取到token: {token_data['access_token'][:20]}...")
                
                # 检查密码是否已迁移
                with Session(engine) as db:
                    user = db.query(User).filter(User.username == "test_migration").first()
                    if user:
                        is_bcrypt = is_bcrypt_hash(user.hashed_password)
                        print(f"登录后密码格式: {'bcrypt' if is_bcrypt else 'PBKDF2-SM3'}")
                        if not is_bcrypt:
                            print("✓ 密码已自动迁移到PBKDF2-SM3")
                            print(f"新哈希: {user.hashed_password[:50]}...")
                        else:
                            print("✗ 密码未迁移")
            else:
                print(f"✗ 登录失败: {response.status_code}")
                print(f"错误信息: {response.text}")
                
        except Exception as e:
            print(f"✗ 登录请求失败: {e}")

def cleanup_test_user():
    """清理测试用户"""
    print("\n=== 清理测试数据 ===\n")
    
    with Session(engine) as db:
        test_user = db.query(User).filter(User.username == "test_migration").first()
        if test_user:
            db.delete(test_user)
            db.commit()
            print("✓ 测试用户已清理")

if __name__ == "__main__":
    try:
        # 创建测试用户
        user_id = test_password_migration()
        
        # 测试API登录
        test_api_login()
        
        # 清理测试数据
        cleanup_test_user()
        
        print("\n=== 测试完成 ===")
        
    except KeyboardInterrupt:
        print("\n\n测试被用户取消")
    except Exception as e:
        print(f"\n测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 确保清理测试数据
        try:
            cleanup_test_user()
        except:
            pass