#!/usr/bin/env python3
"""
测试手机号解密返回功能
"""
import requests
import json

# API 基础URL
BASE_URL = "http://localhost:8000"

def test_phone_decryption():
    """测试手机号解密返回"""
    print("🔐 测试手机号解密返回功能")
    print("=" * 50)
    
    # 1. 管理员登录
    print("1. 管理员登录...")
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        if response.status_code == 200:
            token_data = response.json()
            token = token_data["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            print("✅ 登录成功")
        else:
            print(f"❌ 登录失败: {response.status_code}")
            print(response.text)
            return
    except Exception as e:
        print(f"❌ 登录请求失败: {e}")
        return
    
    # 2. 创建或获取测试用户（带手机号）
    print("\n2. 创建或获取测试用户（带手机号）...")
    user_data = {
        "username": "test_phone_user",
        "password": "test123",
        "user_type": "user",
        "phone": "13812345678"
    }
    
    try:
        # 先尝试创建用户
        response = requests.post(f"{BASE_URL}/users/", json=user_data, headers=headers)
        if response.status_code == 201:
            created_user = response.json()
            user_id = created_user["id"]
            print(f"✅ 用户创建成功，ID: {user_id}")
            print(f"   返回的手机号: {created_user.get('phone', 'None')}")
        elif response.status_code == 400 and "Username already registered" in response.text:
            # 用户已存在，获取现有用户
            print("⚠️ 用户已存在，获取现有用户...")
            users_response = requests.get(f"{BASE_URL}/users/", headers=headers)
            if users_response.status_code == 200:
                users = users_response.json()
                test_user = next((u for u in users if u["username"] == "test_phone_user"), None)
                if test_user:
                    user_id = test_user["id"]
                    print(f"✅ 获取现有用户成功，ID: {user_id}")
                    # 更新用户手机号
                    update_data = {"phone": "13812345678"}
                    update_response = requests.put(f"{BASE_URL}/users/{user_id}", json=update_data, headers=headers)
                    if update_response.status_code == 200:
                        updated_user = update_response.json()
                        print(f"✅ 用户手机号更新成功")
                        print(f"   返回的手机号: {updated_user.get('phone', 'None')}")
                else:
                    print("❌ 未找到现有用户")
                    return
            else:
                print(f"❌ 获取用户列表失败: {users_response.status_code}")
                return
        else:
            print(f"❌ 创建用户失败: {response.status_code}")
            print(response.text)
            return
    except Exception as e:
        print(f"❌ 创建用户请求失败: {e}")
        return
    
    # 3. 查询用户列表
    print("\n3. 查询用户列表...")
    try:
        response = requests.get(f"{BASE_URL}/users/", headers=headers)
        if response.status_code == 200:
            users = response.json()
            test_user = next((u for u in users if u["id"] == user_id), None)
            if test_user:
                print(f"✅ 查询成功")
                print(f"   用户名: {test_user['username']}")
                print(f"   手机号: {test_user.get('phone', 'None')}")
                if test_user.get('phone') == "13812345678":
                    print("✅ 手机号解密正确！")
                else:
                    print(f"❌ 手机号解密错误，期望: 13812345678，实际: {test_user.get('phone')}")
            else:
                print("❌ 未找到测试用户")
        else:
            print(f"❌ 查询用户列表失败: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ 查询用户列表请求失败: {e}")
    
    # 4. 查询单个用户
    print("\n4. 查询单个用户...")
    try:
        response = requests.get(f"{BASE_URL}/users/{user_id}", headers=headers)
        if response.status_code == 200:
            user = response.json()
            print(f"✅ 查询成功")
            print(f"   用户名: {user['username']}")
            print(f"   手机号: {user.get('phone', 'None')}")
            if user.get('phone') == "13812345678":
                print("✅ 手机号解密正确！")
            else:
                print(f"❌ 手机号解密错误，期望: 13812345678，实际: {user.get('phone')}")
        else:
            print(f"❌ 查询用户失败: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ 查询用户请求失败: {e}")
    
    # 5. 测试用户自己登录查看个人信息
    print("\n5. 测试用户自己登录查看个人信息...")
    user_login_data = {
        "username": "test_phone_user",
        "password": "test123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=user_login_data)
        if response.status_code == 200:
            token_data = response.json()
            user_token = token_data["access_token"]
            user_headers = {"Authorization": f"Bearer {user_token}"}
            
            # 获取个人信息
            response = requests.get(f"{BASE_URL}/profile/me", headers=user_headers)
            if response.status_code == 200:
                profile = response.json()
                print(f"✅ 获取个人信息成功")
                print(f"   用户名: {profile['username']}")
                print(f"   手机号: {profile.get('phone', 'None')}")
                if profile.get('phone') == "13812345678":
                    print("✅ 个人信息手机号解密正确！")
                else:
                    print(f"❌ 个人信息手机号解密错误，期望: 13812345678，实际: {profile.get('phone')}")
            else:
                print(f"❌ 获取个人信息失败: {response.status_code}")
                print(response.text)
        else:
            print(f"❌ 测试用户登录失败: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ 测试用户登录请求失败: {e}")
    
    # 6. 清理测试用户
    print("\n6. 清理测试用户...")
    try:
        response = requests.delete(f"{BASE_URL}/users/{user_id}", headers=headers)
        if response.status_code == 200:
            print("✅ 测试用户删除成功")
        else:
            print(f"❌ 删除测试用户失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 删除测试用户请求失败: {e}")

if __name__ == "__main__":
    test_phone_decryption()