#!/usr/bin/env python3
"""
测试用户删除功能和禁用用户限制
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

def test_user_deletion():
    """测试用户删除功能"""
    print("=== 测试用户删除功能 ===")
    
    admin_token = get_auth_token()
    if not admin_token:
        print("无法获取管理员token")
        return
    
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }
    
    # 创建测试用户
    user_data = {
        "username": "delete_test_user",
        "password": "test123456",
        "user_type": "user",
        "phone": "13800139999"
    }
    
    try:
        # 创建用户
        print("\n1. 创建测试用户")
        response = requests.post(f"{BASE_URL}/users/", json=user_data, headers=headers)
        if response.status_code == 201:
            user = response.json()
            user_id = user['id']
            print(f"✓ 用户创建成功，ID: {user_id}")
        else:
            print(f"✗ 创建用户失败: {response.text}")
            return
        
        # 验证用户存在
        print(f"\n2. 验证用户存在")
        response = requests.get(f"{BASE_URL}/users/{user_id}", headers=headers)
        if response.status_code == 200:
            print("✓ 用户存在")
        else:
            print(f"✗ 用户不存在: {response.text}")
            return
        
        # 删除用户
        print(f"\n3. 删除用户")
        response = requests.delete(f"{BASE_URL}/users/{user_id}", headers=headers)
        if response.status_code == 200:
            print("✓ 用户删除成功")
        else:
            print(f"✗ 用户删除失败: {response.text}")
            return
        
        # 验证用户已删除
        print(f"\n4. 验证用户已删除")
        response = requests.get(f"{BASE_URL}/users/{user_id}", headers=headers)
        if response.status_code == 404:
            print("✓ 用户已成功删除")
        else:
            print(f"✗ 用户删除验证失败: {response.text}")
        
    except Exception as e:
        print(f"✗ 删除测试出错: {e}")

def test_disabled_user_restrictions():
    """测试禁用用户的限制"""
    print("\n=== 测试禁用用户限制 ===")
    
    admin_token = get_auth_token()
    if not admin_token:
        print("无法获取管理员token")
        return
    
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }
    
    # 创建测试用户
    user_data = {
        "username": "disabled_test_user",
        "password": "test123456",
        "user_type": "user",
        "phone": "13800138888"
    }
    
    try:
        # 创建用户
        print("\n1. 创建测试用户")
        response = requests.post(f"{BASE_URL}/users/", json=user_data, headers=headers)
        if response.status_code == 201:
            user = response.json()
            user_id = user['id']
            print(f"✓ 用户创建成功，ID: {user_id}")
        else:
            print(f"✗ 创建用户失败: {response.text}")
            return
        
        # 禁用用户
        print(f"\n2. 禁用用户")
        response = requests.post(f"{BASE_URL}/users/{user_id}/deactivate", headers=headers)
        if response.status_code == 200:
            print("✓ 用户禁用成功")
        else:
            print(f"✗ 用户禁用失败: {response.text}")
            return
        
        # 测试禁用用户登录
        print(f"\n3. 测试禁用用户登录")
        login_response = requests.post(f"{BASE_URL}/auth/login", json={
            "username": user_data["username"],
            "password": user_data["password"]
        })
        
        if login_response.status_code == 401:
            error_detail = login_response.json().get("detail")
            if error_detail == "Account is disabled":
                print("✓ 禁用用户登录被正确拒绝")
            else:
                print(f"✗ 错误信息不正确: {error_detail}")
        else:
            print(f"✗ 禁用用户登录应该被拒绝: {login_response.text}")
        
        # 测试手机号登录
        print(f"\n4. 测试禁用用户手机号登录")
        phone_login_response = requests.post(f"{BASE_URL}/auth/login", json={
            "username": user_data["phone"],
            "password": user_data["password"]
        })
        
        if phone_login_response.status_code == 401:
            error_detail = phone_login_response.json().get("detail")
            if error_detail == "Account is disabled":
                print("✓ 禁用用户手机号登录被正确拒绝")
            else:
                print(f"✗ 错误信息不正确: {error_detail}")
        else:
            print(f"✗ 禁用用户手机号登录应该被拒绝: {phone_login_response.text}")
        
        # 测试使用禁用用户的用户名注册
        print(f"\n5. 测试使用禁用用户的用户名注册")
        register_response = requests.post(f"{BASE_URL}/auth/register", json={
            "username": user_data["username"],
            "password": "newpassword123",
            "phone": "13900139999"
        })
        
        if register_response.status_code == 400:
            error_detail = register_response.json().get("detail")
            if error_detail == "Username is disabled and cannot be registered":
                print("✓ 使用禁用用户名注册被正确拒绝")
            else:
                print(f"✗ 错误信息不正确: {error_detail}")
        else:
            print(f"✗ 使用禁用用户名注册应该被拒绝: {register_response.text}")
        
        # 测试使用禁用用户的手机号注册
        print(f"\n6. 测试使用禁用用户的手机号注册")
        register_phone_response = requests.post(f"{BASE_URL}/auth/register", json={
            "username": "new_test_user",
            "password": "newpassword123",
            "phone": user_data["phone"]
        })
        
        if register_phone_response.status_code == 400:
            error_detail = register_phone_response.json().get("detail")
            if error_detail == "Phone number is disabled and cannot be registered":
                print("✓ 使用禁用用户手机号注册被正确拒绝")
            else:
                print(f"✗ 错误信息不正确: {error_detail}")
        else:
            print(f"✗ 使用禁用用户手机号注册应该被拒绝: {register_phone_response.text}")
        
        # 重新激活用户
        print(f"\n7. 重新激活用户")
        activate_response = requests.post(f"{BASE_URL}/users/{user_id}/activate", headers=headers)
        if activate_response.status_code == 200:
            print("✓ 用户重新激活成功")
        else:
            print(f"✗ 用户重新激活失败: {activate_response.text}")
        
        # 测试重新激活后登录
        print(f"\n8. 测试重新激活后登录")
        relogin_response = requests.post(f"{BASE_URL}/auth/login", json={
            "username": user_data["username"],
            "password": user_data["password"]
        })
        
        if relogin_response.status_code == 200:
            print("✓ 重新激活后登录成功")
        else:
            print(f"✗ 重新激活后登录失败: {relogin_response.text}")
            
    except Exception as e:
        print(f"✗ 禁用用户限制测试出错: {e}")

def test_self_delete_prevention():
    """测试防止用户删除自己"""
    print("\n=== 测试防止用户删除自己 ===")
    
    admin_token = get_auth_token()
    if not admin_token:
        print("无法获取管理员token")
        return
    
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }
    
    # 获取当前管理员用户信息
    try:
        me_response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
        if me_response.status_code == 200:
            admin_user = me_response.json()
            admin_id = admin_user['id']
            print(f"✓ 获取管理员用户ID: {admin_id}")
            
            # 尝试删除自己
            print(f"\n尝试删除自己")
            delete_response = requests.delete(f"{BASE_URL}/users/{admin_id}", headers=headers)
            
            if delete_response.status_code == 400:
                error_detail = delete_response.json().get("detail")
                if error_detail == "Cannot delete yourself":
                    print("✓ 防止用户删除自己功能正常")
                else:
                    print(f"✗ 错误信息不正确: {error_detail}")
            else:
                print(f"✗ 应该防止用户删除自己: {delete_response.text}")
        else:
            print(f"✗ 获取管理员用户信息失败: {me_response.text}")
            
    except Exception as e:
        print(f"✗ 防止自删除测试出错: {e}")

if __name__ == "__main__":
    print("开始测试用户删除功能和禁用用户限制...")
    test_user_deletion()
    test_disabled_user_restrictions()
    test_self_delete_prevention()
    print("\n测试完成!")