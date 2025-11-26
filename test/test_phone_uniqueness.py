#!/usr/bin/env python3
"""
测试手机号唯一性功能
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

def test_phone_uniqueness():
    """测试手机号唯一性"""
    print("=== 测试手机号唯一性 ===")
    
    # 获取管理员token
    admin_token = get_auth_token()
    if not admin_token:
        print("无法获取管理员token，请确保管理员用户存在")
        return
    
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }
    
    # 测试数据
    phone_number = "13800138000"
    
    # 第一个用户，应该成功
    user1_data = {
        "username": "test_phone_user1",
        "password": "test123456",
        "user_type": "user",
        "phone": phone_number
    }
    
    try:
        response1 = requests.post(f"{BASE_URL}/users/", json=user1_data, headers=headers)
        print(f"第一个用户注册状态码: {response1.status_code}")
        if response1.status_code == 201:
            print("✓ 第一个用户注册成功")
        else:
            print(f"✗ 第一个用户注册失败: {response1.text}")
            return
    except Exception as e:
        print(f"✗ 第一个用户注册出错: {e}")
        return
    
    # 第二个用户，使用相同手机号，应该失败
    user2_data = {
        "username": "test_phone_user2", 
        "password": "test123456",
        "user_type": "user",
        "phone": phone_number
    }
    
    try:
        response2 = requests.post(f"{BASE_URL}/users/", json=user2_data, headers=headers)
        print(f"第二个用户注册状态码: {response2.status_code}")
        if response2.status_code == 400:
            print("✓ 第二个用户注册被正确拒绝（手机号重复）")
        else:
            print(f"✗ 第二个用户注册应该被拒绝: {response2.text}")
    except Exception as e:
        print(f"✗ 第二个用户注册出错: {e}")

def test_user_phone_update():
    """测试用户更新手机号"""
    print("\n=== 测试用户更新手机号 ===")
    
    # 获取管理员token
    admin_token = get_auth_token()
    if not admin_token:
        print("无法获取管理员token")
        return
    
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }
    
    # 先创建两个用户
    user1_data = {
        "username": "update_test_user1",
        "password": "test123456",
        "user_type": "user",
        "phone": "13900139000"
    }
    
    user2_data = {
        "username": "update_test_user2",
        "password": "test123456", 
        "user_type": "user",
        "phone": "13900139001"
    }
    
    try:
        # 创建用户1
        response1 = requests.post(f"{BASE_URL}/users/", json=user1_data, headers=headers)
        if response1.status_code != 201:
            print(f"创建用户1失败: {response1.text}")
            return
        
        user1 = response1.json()
        user1_id = user1['id']
        print(f"✓ 用户1创建成功，ID: {user1_id}")
        
        # 创建用户2
        response2 = requests.post(f"{BASE_URL}/users/", json=user2_data, headers=headers)
        if response2.status_code != 201:
            print(f"创建用户2失败: {response2.text}")
            return
        
        user2 = response2.json()
        user2_id = user2['id']
        print(f"✓ 用户2创建成功，ID: {user2_id}")
        
        # 尝试将用户1的手机号更新为用户2的手机号（应该失败）
        update_data = {
            "phone": "13900139001"  # 用户2的手机号
        }
        
        response3 = requests.put(f"{BASE_URL}/users/{user1_id}", json=update_data, headers=headers)
        print(f"用户1更新手机号状态码: {response3.status_code}")
        if response3.status_code == 400:
            print("✓ 手机号更新被正确拒绝（手机号重复）")
        else:
            print(f"✗ 手机号更新应该被拒绝: {response3.text}")
        
        # 将用户1的手机号更新为新号码（应该成功）
        update_data2 = {
            "phone": "13900139002"
        }
        
        response4 = requests.put(f"{BASE_URL}/users/{user1_id}", json=update_data2, headers=headers)
        print(f"用户1更新为新手机号状态码: {response4.status_code}")
        if response4.status_code == 200:
            print("✓ 手机号更新成功")
        else:
            print(f"✗ 手机号更新失败: {response4.text}")
            
    except Exception as e:
        print(f"✗ 更新测试出错: {e}")

def test_user_list_ordering():
    """测试用户列表按ID排序"""
    print("\n=== 测试用户列表排序 ===")
    
    # 获取管理员token
    admin_token = get_auth_token()
    if not admin_token:
        print("无法获取管理员token")
        return
    
    headers = {
        "Authorization": f"Bearer {admin_token}"
    }
    
    try:
        response = requests.get(f"{BASE_URL}/users/", headers=headers)
        if response.status_code == 200:
            users = response.json()
            print(f"✓ 获取用户列表成功，共 {len(users)} 个用户")
            
            # 检查是否按ID排序
            if len(users) > 1:
                ids = [user['id'] for user in users]
                is_sorted = all(ids[i] <= ids[i+1] for i in range(len(ids)-1))
                if is_sorted:
                    print("✓ 用户列表按ID正确排序")
                else:
                    print("✗ 用户列表未按ID排序")
                    print(f"ID序列: {ids}")
        else:
            print(f"✗ 获取用户列表失败: {response.text}")
            
    except Exception as e:
        print(f"✗ 排序测试出错: {e}")

if __name__ == "__main__":
    print("开始测试手机号唯一性功能...")
    test_phone_uniqueness()
    test_user_phone_update()
    test_user_list_ordering()
    print("\n测试完成!")