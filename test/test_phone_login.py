#!/usr/bin/env python3
"""
测试手机号登录功能
"""

import requests
import json

# API基础URL
BASE_URL = "http://localhost:8000"

def get_auth_token(username="admin", password="admin123"):
    """获取管理员token"""
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": username,
        "password": password
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("access_token")
    return None

def test_phone_login():
    """测试手机号登录功能"""
    print("=== 测试手机号登录功能 ===")
    
    # 获取管理员token
    admin_token = get_auth_token()
    if not admin_token:
        print("无法获取管理员token，请确保管理员用户存在")
        return
    
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }
    
    # 创建测试用户
    test_phone = "13800138999"
    test_username = "phone_login_test"
    test_password = "test123456"
    
    user_data = {
        "username": test_username,
        "password": test_password,
        "user_type": "user",
        "phone": test_phone
    }
    
    try:
        # 创建测试用户
        print(f"\n1. 创建测试用户: {test_username}")
        response = requests.post(f"{BASE_URL}/users/", json=user_data, headers=headers)
        if response.status_code == 201:
            print("✓ 测试用户创建成功")
        elif response.status_code == 400 and "already registered" in response.text:
            print("✓ 测试用户已存在")
        else:
            print(f"✗ 创建测试用户失败: {response.text}")
            return
        
        # 测试用户名登录
        print(f"\n2. 测试用户名登录: {test_username}")
        login_response = requests.post(f"{BASE_URL}/auth/login", json={
            "username": test_username,
            "password": test_password
        })
        
        if login_response.status_code == 200:
            token_data = login_response.json()
            print("✓ 用户名登录成功")
            print(f"  Token类型: {token_data.get('token_type')}")
        else:
            print(f"✗ 用户名登录失败: {login_response.text}")
            return
        
        # 测试手机号登录
        print(f"\n3. 测试手机号登录: {test_phone}")
        phone_login_response = requests.post(f"{BASE_URL}/auth/login", json={
            "username": test_phone,  # 使用手机号作为用户名
            "password": test_password
        })
        
        if phone_login_response.status_code == 200:
            token_data = phone_login_response.json()
            print("✓ 手机号登录成功")
            print(f"  Token类型: {token_data.get('token_type')}")
        else:
            print(f"✗ 手机号登录失败: {phone_login_response.text}")
        
        # 测试错误密码登录
        print(f"\n4. 测试错误密码登录（手机号）")
        wrong_password_response = requests.post(f"{BASE_URL}/auth/login", json={
            "username": test_phone,
            "password": "wrongpassword"
        })
        
        if wrong_password_response.status_code == 401:
            print("✓ 错误密码登录被正确拒绝")
        else:
            print(f"✗ 错误密码登录应该被拒绝: {wrong_password_response.text}")
        
        # 测试不存在的手机号登录
        print(f"\n5. 测试不存在的手机号登录")
        nonexistent_phone_response = requests.post(f"{BASE_URL}/auth/login", json={
            "username": "19999999999",
            "password": test_password
        })
        
        if nonexistent_phone_response.status_code == 401:
            print("✓ 不存在的手机号登录被正确拒绝")
        else:
            print(f"✗ 不存在的手机号登录应该被拒绝: {nonexistent_phone_response.text}")
            
    except Exception as e:
        print(f"✗ 测试过程中出错: {e}")

def test_mixed_login():
    """测试混合登录场景"""
    print("\n=== 测试混合登录场景 ===")
    
    # 创建两个用户，一个用户名是数字格式，一个有手机号
    admin_token = get_auth_token()
    if not admin_token:
        print("无法获取管理员token")
        return
    
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }
    
    # 用户1：数字格式的用户名
    user1_data = {
        "username": "123456789",
        "password": "test123456",
        "user_type": "user",
        "phone": "13800138001"
    }
    
    # 用户2：普通用户名
    user2_data = {
        "username": "normal_user",
        "password": "test123456",
        "user_type": "user",
        "phone": "12345678901"
    }
    
    try:
        # 创建用户1
        print("\n1. 创建数字格式用户名的用户")
        response1 = requests.post(f"{BASE_URL}/users/", json=user1_data, headers=headers)
        if response1.status_code in [201, 400]:
            print("✓ 用户1创建成功或已存在")
        
        # 创建用户2
        print("\n2. 创建普通用户名的用户")
        response2 = requests.post(f"{BASE_URL}/users/", json=user2_data, headers=headers)
        if response2.status_code in [201, 400]:
            print("✓ 用户2创建成功或已存在")
        
        # 测试登录"123456789" - 应该优先匹配用户名
        print("\n3. 测试登录 '123456789'（应该优先匹配用户名）")
        login_response = requests.post(f"{BASE_URL}/auth/login", json={
            "username": "123456789",
            "password": "test123456"
        })
        
        if login_response.status_code == 200:
            print("✓ 登录成功（用户名优先）")
        else:
            print(f"✗ 登录失败: {login_response.text}")
        
        # 测试登录"13800138001" - 应该匹配手机号
        print("\n4. 测试登录 '13800138001'（应该匹配手机号）")
        phone_login_response = requests.post(f"{BASE_URL}/auth/login", json={
            "username": "13800138001",
            "password": "test123456"
        })
        
        if phone_login_response.status_code == 200:
            print("✓ 手机号登录成功")
        else:
            print(f"✗ 手机号登录失败: {phone_login_response.text}")
            
    except Exception as e:
        print(f"✗ 混合登录测试出错: {e}")

if __name__ == "__main__":
    print("开始测试手机号登录功能...")
    test_phone_login()
    test_mixed_login()
    print("\n测试完成!")