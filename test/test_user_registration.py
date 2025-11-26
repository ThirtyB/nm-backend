#!/usr/bin/env python3
"""
测试用户注册功能，特别是手机号字段
"""

import requests
import json

# API基础URL
BASE_URL = "http://localhost:8000"

def test_user_registration():
    """测试用户注册功能"""
    
    # 测试数据
    test_cases = [
        {
            "name": "带手机号的注册",
            "data": {
                "username": "test_user_with_phone",
                "password": "test123456",
                "phone": "13800138000"
            }
        },
        {
            "name": "不带手机号的注册",
            "data": {
                "username": "test_user_no_phone",
                "password": "test123456"
            }
        },
        {
            "name": "空手机号注册",
            "data": {
                "username": "test_user_empty_phone",
                "password": "test123456",
                "phone": ""
            }
        }
    ]
    
    for test_case in test_cases:
        print(f"\n=== {test_case['name']} ===")
        
        try:
            # 发送注册请求
            response = requests.post(
                f"{BASE_URL}/auth/register",
                json=test_case["data"],
                headers={"Content-Type": "application/json"}
            )
            
            print(f"状态码: {response.status_code}")
            
            if response.status_code == 201:
                user_data = response.json()
                print(f"注册成功!")
                print(f"用户名: {user_data.get('username')}")
                print(f"手机号: {user_data.get('phone')}")
                print(f"用户类型: {user_data.get('user_type')}")
                print(f"激活状态: {user_data.get('is_active')}")
            else:
                print(f"注册失败: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("连接失败，请确保服务器正在运行")
        except Exception as e:
            print(f"测试出错: {e}")

def test_duplicate_registration():
    """测试重复注册"""
    print("\n=== 重复注册测试 ===")
    
    # 先注册一个用户
    user_data = {
        "username": "duplicate_test",
        "password": "test123456",
        "phone": "13900139000"
    }
    
    try:
        # 第一次注册
        response1 = requests.post(f"{BASE_URL}/auth/register", json=user_data)
        print(f"第一次注册状态码: {response1.status_code}")
        
        # 第二次注册相同用户名
        response2 = requests.post(f"{BASE_URL}/auth/register", json=user_data)
        print(f"第二次注册状态码: {response2.status_code}")
        
        if response2.status_code == 400:
            print("重复注册被正确拒绝")
        else:
            print(f"意外结果: {response2.text}")
            
    except Exception as e:
        print(f"重复注册测试出错: {e}")

if __name__ == "__main__":
    print("开始测试用户注册功能...")
    test_user_registration()
    test_duplicate_registration()
    print("\n测试完成!")