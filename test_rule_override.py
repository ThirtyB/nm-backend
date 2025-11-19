#!/usr/bin/env python3
"""
测试规则覆盖逻辑的脚本
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

def create_test_rules():
    """创建测试规则"""
    print("\n=== 创建测试规则 ===")
    
    # 1. 创建全局规则：CPU使用率 > 80% 报警
    global_rule = {
        "rule_name": "全局CPU使用率告警",
        "rule_type": "global",
        "condition_field": "cpu_usage_rate",
        "condition_operator": ">",
        "condition_value": 80.0,
        "alert_level": "warning",
        "alert_message": "全局规则：CPU使用率 {current_value}% 超过阈值 {threshold_value}%"
    }
    
    response = requests.post(f"{BASE_URL}/alert-management/rules", 
                           json=global_rule, headers=get_headers(ADMIN_TOKEN))
    print(f"创建全局CPU规则: {response.status_code}")
    if response.status_code == 200:
        global_cpu_id = response.json()['id']
        print(f"  规则ID: {global_cpu_id}")
    else:
        print(f"  错误: {response.text}")
        return None, None
    
    # 2. 创建个例规则：同一IP的CPU使用率 > 90% 报警（覆盖全局规则）
    specific_rule = {
        "rule_name": "特定IP CPU使用率告警（覆盖全局）",
        "rule_type": "specific",
        "target_ip": "192.168.1.100",
        "condition_field": "cpu_usage_rate",
        "condition_operator": ">",
        "condition_value": 90.0,
        "alert_level": "warning",
        "alert_message": "个例规则：CPU使用率 {current_value}% 超过阈值 {threshold_value}%"
    }
    
    response = requests.post(f"{BASE_URL}/alert-management/rules", 
                           json=specific_rule, headers=get_headers(ADMIN_TOKEN))
    print(f"创建个例CPU规则: {response.status_code}")
    if response.status_code == 200:
        specific_cpu_id = response.json()['id']
        print(f"  规则ID: {specific_cpu_id}")
    else:
        print(f"  错误: {response.text}")
        return None, None
    
    # 3. 创建另一个全局规则：内存使用率 > 85% 报警（不会被覆盖）
    memory_rule = {
        "rule_name": "全局内存使用率告警",
        "rule_type": "global",
        "condition_field": "memory_usage_rate",
        "condition_operator": ">",
        "condition_value": 85.0,
        "alert_level": "error",
        "alert_message": "全局规则：内存使用率 {current_value}% 超过阈值 {threshold_value}%"
    }
    
    response = requests.post(f"{BASE_URL}/alert-management/rules", 
                           json=memory_rule, headers=get_headers(ADMIN_TOKEN))
    print(f"创建全局内存规则: {response.status_code}")
    
    return global_cpu_id, specific_cpu_id

def test_rule_override():
    """测试规则覆盖逻辑"""
    print("\n=== 测试规则覆盖逻辑 ===")
    
    # 获取当前时间戳
    current_time = int(time.time())
    one_hour_ago = current_time - 3600
    
    # 查询192.168.1.100的告警
    response = requests.get(f"{BASE_URL}/alert-management/alerts/192.168.1.100", 
                          params={
                              "start_time": one_hour_ago,
                              "end_time": current_time
                          },
                          headers=get_headers(ADMIN_TOKEN))
    
    print(f"查询192.168.1.100告警: {response.status_code}")
    if response.status_code == 200:
        alerts = response.json()
        print(f"告警数量: {alerts['total_count']}")
        
        cpu_alerts = [alert for alert in alerts['alerts'] if alert['condition_field'] == 'cpu_usage_rate']
        memory_alerts = [alert for alert in alerts['alerts'] if alert['condition_field'] == 'memory_usage_rate']
        
        print(f"\nCPU相关告警:")
        for alert in cpu_alerts:
            print(f"  - {alert['rule_name']} (类型: {alert['rule_type']}, 阈值: {alert['threshold_value']})")
        
        print(f"\n内存相关告警:")
        for alert in memory_alerts:
            print(f"  - {alert['rule_name']} (类型: {alert['rule_type']}, 阈值: {alert['threshold_value']})")
        
        # 验证覆盖逻辑
        if len(cpu_alerts) == 1 and cpu_alerts[0]['rule_type'] == 'specific':
            print(f"\n✅ 规则覆盖逻辑正确：只显示个例CPU规则（阈值90%）")
        else:
            print(f"\n❌ 规则覆盖逻辑异常：显示了{len(cpu_alerts)}个CPU规则")
            
    else:
        print(f"错误: {response.text}")

def cleanup_test_rules(rule_ids):
    """清理测试规则"""
    print("\n=== 清理测试规则 ===")
    for rule_id in rule_ids:
        if rule_id:
            response = requests.delete(f"{BASE_URL}/alert-management/rules/{rule_id}", 
                                      headers=get_headers(ADMIN_TOKEN))
            print(f"删除规则 {rule_id}: {response.status_code}")

def main():
    """主测试函数"""
    global ADMIN_TOKEN
    
    print("开始测试规则覆盖逻辑...")
    
    # 登录管理员账户
    ADMIN_TOKEN = login("admin", "admin123")
    if not ADMIN_TOKEN:
        print("管理员登录失败")
        return
    
    # 创建测试规则
    global_cpu_id, specific_cpu_id = create_test_rules()
    if not global_cpu_id or not specific_cpu_id:
        print("创建测试规则失败")
        return
    
    # 等待一下确保规则创建完成
    time.sleep(1)
    
    # 测试规则覆盖逻辑
    test_rule_override()
    
    # 清理测试规则
    cleanup_test_rules([global_cpu_id, specific_cpu_id])
    
    print("\n测试完成！")

if __name__ == "__main__":
    main()