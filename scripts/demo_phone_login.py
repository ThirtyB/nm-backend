#!/usr/bin/env python3
"""
手机号登录功能演示脚本
"""

import requests
import json
import time

# API基础URL
BASE_URL = "http://localhost:8000"

def create_test_user():
    """创建测试用户"""
    print("=== 创建测试用户 ===")
    
    # 获取管理员token
    admin_response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    
    if admin_response.status_code != 200:
        print("❌ 无法获取管理员权限，请确保admin用户存在")
        return None
    
    admin_token = admin_response.json()["access_token"]
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }
    
    # 创建测试用户
    user_data = {
        "username": "demo_user",
        "password": "demo123456",
        "user_type": "user",
        "phone": "13800138888"
    }
    
    response = requests.post(f"{BASE_URL}/users/", json=user_data, headers=headers)
    
    if response.status_code == 201:
        print("✅ 测试用户创建成功")
        print(f"   用户名: {user_data['username']}")
        print(f"   手机号: {user_data['phone']}")
        return user_data
    elif response.status_code == 400 and "already registered" in response.text:
        print("✅ 测试用户已存在")
        return user_data
    else:
        print(f"❌ 创建测试用户失败: {response.text}")
        return None

def demo_login_methods(user_data):
    """演示不同的登录方式"""
    print("\n=== 演示登录方式 ===")
    
    username = user_data["username"]
    phone = user_data["phone"]
    password = user_data["password"]
    
    # 1. 用户名登录
    print(f"\n1️⃣ 使用用户名登录: {username}")
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": username,
        "password": password
    })
    
    if response.status_code == 200:
        token = response.json()["access_token"]
        print("✅ 用户名登录成功")
        print(f"   Token: {token[:20]}...")
    else:
        print(f"❌ 用户名登录失败: {response.text}")
    
    # 等待一秒
    time.sleep(1)
    
    # 2. 手机号登录
    print(f"\n2️⃣ 使用手机号登录: {phone}")
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": phone,
        "password": password
    })
    
    if response.status_code == 200:
        token = response.json()["access_token"]
        print("✅ 手机号登录成功")
        print(f"   Token: {token[:20]}...")
    else:
        print(f"❌ 手机号登录失败: {response.text}")
    
    # 等待一秒
    time.sleep(1)
    
    # 3. 错误密码演示
    print(f"\n3️⃣ 错误密码演示（使用手机号）")
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": phone,
        "password": "wrongpassword"
    })
    
    if response.status_code == 401:
        print("✅ 错误密码被正确拒绝")
        print(f"   错误信息: {response.json()['detail']}")
    else:
        print(f"❌ 错误密码处理异常: {response.text}")

def demo_current_user():
    """演示获取当前用户信息"""
    print("\n=== 演示获取当前用户信息 ===")
    
    # 使用手机号登录获取token
    login_response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "13800138888",
        "password": "demo123456"
    })
    
    if login_response.status_code != 200:
        print("❌ 无法登录获取token")
        return
    
    token = login_response.json()["access_token"]
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # 获取当前用户信息
    response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    
    if response.status_code == 200:
        user_info = response.json()
        print("✅ 获取当前用户信息成功")
        print(f"   用户ID: {user_info['id']}")
        print(f"   用户名: {user_info['username']}")
        print(f"   用户类型: {user_info['user_type']}")
        print(f"   手机号: {user_info['phone']}")
        print(f"   激活状态: {user_info['is_active']}")
    else:
        print(f"❌ 获取用户信息失败: {response.text}")

def main():
    """主演示函数"""
    print("🚀 手机号登录功能演示")
    print("=" * 50)
    
    # 检查服务器是否运行
    try:
        response = requests.get(f"{BASE_URL}/docs")
        if response.status_code != 200:
            print("❌ 服务器未运行，请先启动: python start_server.py")
            return
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请先启动: python start_server.py")
        return
    
    # 创建测试用户
    user_data = create_test_user()
    if not user_data:
        return
    
    # 演示登录方式
    demo_login_methods(user_data)
    
    # 演示获取用户信息
    demo_current_user()
    
    print("\n" + "=" * 50)
    print("🎉 演示完成！")
    print("\n💡 提示:")
    print("- 用户可以使用用户名或手机号登录")
    print("- 系统优先匹配用户名，失败后尝试手机号")
    print("- 手机号在数据库中加密存储，确保安全性")

if __name__ == "__main__":
    main()