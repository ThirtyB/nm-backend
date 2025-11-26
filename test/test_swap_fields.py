#!/usr/bin/env python3
"""
测试Swap相关字段配置的脚本
"""

import requests
import json
import time
from datetime import datetime

# 配置
BASE_URL = "http://localhost:8000"
ADMIN_TOKEN = None

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

def create_swap_test_rules():
    """创建Swap相关测试规则"""
    print("\n=== 创建Swap相关测试规则 ===")
    rule_ids = []
    
    # 1. Swap使用率告警（衍生指标）
    swap_usage_rule = {
        "rule_name": "Swap使用率过高告警",
        "rule_type": "global",
        "condition_field": "swap_usage_rate",
        "condition_operator": ">",
        "condition_value": 50.0,
        "alert_level": "warning",
        "alert_message": "Swap使用率 {current_value}% 超过阈值 {threshold_value}%"
    }
    
    response = requests.post(f"{BASE_URL}/alert-management/rules", 
                           json=swap_usage_rule, headers=get_headers(ADMIN_TOKEN))
    print(f"创建Swap使用率规则: {response.status_code}")
    if response.status_code == 200:
        rule_ids.append(response.json()['id'])
        print(f"  规则ID: {response.json()['id']}")
    else:
        print(f"  错误: {response.text}")
    
    # 2. Swap使用量告警（原始字段）
    swap_used_rule = {
        "rule_name": "Swap使用量告警",
        "rule_type": "global",
        "condition_field": "swap_used",
        "condition_operator": ">",
        "condition_value": 1073741824,  # 1GB
        "alert_level": "error",
        "alert_message": "Swap使用量 {current_value} 字节超过阈值 {threshold_value} 字节"
    }
    
    response = requests.post(f"{BASE_URL}/alert-management/rules", 
                           json=swap_used_rule, headers=get_headers(ADMIN_TOKEN))
    print(f"创建Swap使用量规则: {response.status_code}")
    if response.status_code == 200:
        rule_ids.append(response.json()['id'])
        print(f"  规则ID: {response.json()['id']}")
    else:
        print(f"  错误: {response.text}")
    
    # 3. Swap换入速率告警
    swap_in_rule = {
        "rule_name": "Swap换入速率告警",
        "rule_type": "global",
        "condition_field": "swap_in",
        "condition_operator": ">",
        "condition_value": 1024,  # 1KB/s
        "alert_level": "info",
        "alert_message": "Swap换入速率 {current_value} 字节/秒超过阈值 {threshold_value} 字节/秒"
    }
    
    response = requests.post(f"{BASE_URL}/alert-management/rules", 
                           json=swap_in_rule, headers=get_headers(ADMIN_TOKEN))
    print(f"创建Swap换入速率规则: {response.status_code}")
    if response.status_code == 200:
        rule_ids.append(response.json()['id'])
        print(f"  规则ID: {response.json()['id']}")
    else:
        print(f"  错误: {response.text}")
    
    # 4. 特定IP的Swap个例规则
    specific_swap_rule = {
        "rule_name": "特定IP Swap使用率告警",
        "rule_type": "specific",
        "target_ip": "192.168.1.100",
        "condition_field": "swap_usage_rate",
        "condition_operator": ">",
        "condition_value": 30.0,  # 更严格的阈值
        "alert_level": "warning",
        "alert_message": "特定IP {ip} Swap使用率 {current_value}% 超过阈值 {threshold_value}%"
    }
    
    response = requests.post(f"{BASE_URL}/alert-management/rules", 
                           json=specific_swap_rule, headers=get_headers(ADMIN_TOKEN))
    print(f"创建特定IP Swap规则: {response.status_code}")
    if response.status_code == 200:
        rule_ids.append(response.json()['id'])
        print(f"  规则ID: {response.json()['id']}")
    else:
        print(f"  错误: {response.text}")
    
    return rule_ids

def test_swap_alerts():
    """测试Swap告警"""
    print("\n=== 测试Swap告警查询 ===")
    
    # 获取当前时间戳
    current_time = int(time.time())
    one_hour_ago = current_time - 3600
    
    # 查询所有告警
    response = requests.get(f"{BASE_URL}/alert-management/alerts", 
                          params={
                              "start_time": one_hour_ago,
                              "end_time": current_time
                          },
                          headers=get_headers(ADMIN_TOKEN))
    
    print(f"查询所有告警: {response.status_code}")
    if response.status_code == 200:
        alerts = response.json()
        print(f"告警总数: {alerts['total_count']}")
        
        swap_alerts = [alert for alert in alerts['alerts'] 
                      if 'swap' in alert['condition_field'].lower()]
        
        print(f"\nSwap相关告警:")
        for alert in swap_alerts:
            print(f"  - {alert['rule_name']}")
            print(f"    字段: {alert['condition_field']}")
            print(f"    当前值: {alert['current_value']}")
            print(f"    阈值: {alert['threshold_value']}")
            print(f"    级别: {alert['alert_level']}")
            print(f"    类型: {alert['rule_type']}")
            print()
    else:
        print(f"错误: {response.text}")

def cleanup_rules(rule_ids):
    """清理测试规则"""
    print("\n=== 清理测试规则 ===")
    for rule_id in rule_ids:
        response = requests.delete(f"{BASE_URL}/alert-management/rules/{rule_id}", 
                                  headers=get_headers(ADMIN_TOKEN))
        print(f"删除规则 {rule_id}: {response.status_code}")

def main():
    """主测试函数"""
    global ADMIN_TOKEN
    
    print("开始测试Swap字段配置...")
    
    # 登录管理员账户
    ADMIN_TOKEN = login("admin", "admin123")
    if not ADMIN_TOKEN:
        print("管理员登录失败")
        return
    
    # 创建Swap测试规则
    rule_ids = create_swap_test_rules()
    if not rule_ids:
        print("创建测试规则失败")
        return
    
    # 等待一下确保规则创建完成
    time.sleep(1)
    
    # 测试Swap告警
    test_swap_alerts()
    
    # 清理测试规则
    cleanup_rules(rule_ids)
    
    print("\nSwap字段配置测试完成！")

if __name__ == "__main__":
    main()