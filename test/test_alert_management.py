#!/usr/bin/env python3
"""
告警管理功能测试脚本
"""

import requests
import json
import time
from datetime import datetime

# 配置
BASE_URL = "http://localhost:8000"
ADMIN_TOKEN = None
USER_TOKEN = None

def login(username, password):
    """登录获取token"""
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": username,
        "password": password
    })
    
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"登录失败: {response.text}")
        return None

def get_headers(token):
    """获取请求头"""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

def test_create_rule():
    """测试创建告警规则"""
    print("\n=== 测试创建告警规则 ===")
    
    # 创建全局规则
    global_rule = {
        "rule_name": "CPU使用率过高告警",
        "rule_type": "global",
        "condition_field": "cpu_usage_rate",
        "condition_operator": ">",
        "condition_value": 80.0,
        "alert_level": "warning",
        "alert_message": "CPU使用率 {current_value}% 超过阈值 {threshold_value}%"
    }
    
    response = requests.post(f"{BASE_URL}/alert-management/rules", 
                           json=global_rule, headers=get_headers(ADMIN_TOKEN))
    print(f"创建全局规则: {response.status_code}")
    if response.status_code == 200:
        print(f"规则ID: {response.json()['id']}")
    
    # 创建个例规则
    specific_rule = {
        "rule_name": "特定服务器内存告警",
        "rule_type": "specific",
        "target_ip": "192.168.1.100",
        "condition_field": "memory_usage_rate",
        "condition_operator": ">",
        "condition_value": 85.0,
        "alert_level": "error",
        "alert_message": "服务器 {ip} 内存使用率 {current_value}% 超过阈值 {threshold_value}%"
    }
    
    response = requests.post(f"{BASE_URL}/alert-management/rules", 
                           json=specific_rule, headers=get_headers(ADMIN_TOKEN))
    print(f"创建个例规则: {response.status_code}")
    if response.status_code == 200:
        print(f"规则ID: {response.json()['id']}")

def test_get_rules():
    """测试获取规则列表"""
    print("\n=== 测试获取规则列表 ===")
    
    response = requests.get(f"{BASE_URL}/alert-management/rules", 
                          headers=get_headers(ADMIN_TOKEN))
    print(f"获取规则列表: {response.status_code}")
    if response.status_code == 200:
        rules = response.json()
        print(f"规则数量: {len(rules)}")
        for rule in rules:
            print(f"  - {rule['rule_name']} ({rule['rule_type']})")

def test_get_alerts():
    """测试获取告警信息"""
    print("\n=== 测试获取告警信息 ===")
    
    # 获取当前时间戳
    current_time = int(time.time())
    one_hour_ago = current_time - 3600
    
    # 使用普通用户token测试
    response = requests.get(f"{BASE_URL}/alert-management/alerts", 
                          params={
                              "start_time": one_hour_ago,
                              "end_time": current_time
                          },
                          headers=get_headers(USER_TOKEN))
    print(f"获取告警信息: {response.status_code}")
    if response.status_code == 200:
        alerts = response.json()
        print(f"告警数量: {alerts['total_count']}")
        for alert in alerts['alerts'][:3]:  # 只显示前3个
            print(f"  - {alert['ip']}: {alert['alert_message']}")
    else:
        print(f"错误: {response.text}")

def test_permission_control():
    """测试权限控制"""
    print("\n=== 测试权限控制 ===")
    
    # 普通用户尝试创建规则（应该失败）
    rule = {
        "rule_name": "测试规则",
        "rule_type": "global",
        "condition_field": "cpu_usage_rate",
        "condition_operator": ">",
        "condition_value": 90.0
    }
    
    response = requests.post(f"{BASE_URL}/alert-management/rules", 
                           json=rule, headers=get_headers(USER_TOKEN))
    print(f"普通用户创建规则: {response.status_code} (应该是403)")
    
    # 普通用户尝试获取规则列表（应该失败）
    response = requests.get(f"{BASE_URL}/alert-management/rules", 
                          headers=get_headers(USER_TOKEN))
    print(f"普通用户获取规则: {response.status_code} (应该是403)")

def main():
    """主测试函数"""
    global ADMIN_TOKEN, USER_TOKEN
    
    print("开始测试告警管理功能...")
    
    # 登录获取token
    print("登录管理员账户...")
    ADMIN_TOKEN = login("admin", "admin123")
    if not ADMIN_TOKEN:
        print("管理员登录失败，请先创建管理员账户")
        return
    
    print("登录普通用户账户...")
    USER_TOKEN = login("user", "user123")
    if not USER_TOKEN:
        print("普通用户登录失败，使用管理员token测试")
        USER_TOKEN = ADMIN_TOKEN
    
    # 执行测试
    test_create_rule()
    test_get_rules()
    test_get_alerts()
    test_permission_control()
    
    print("\n测试完成！")

if __name__ == "__main__":
    main()