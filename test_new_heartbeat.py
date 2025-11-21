#!/usr/bin/env python3
"""
测试新的心跳和流量统计功能
"""

import requests
import json
import time
from datetime import datetime, timedelta

# API基础URL
BASE_URL = "http://localhost:8000"

def login():
    """登录获取token"""
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    if response.status_code == 200:
        token_data = response.json()
        return token_data["access_token"]
    else:
        print(f"登录失败: {response.status_code} - {response.text}")
        return None

def test_heartbeat_report(token, ip_address, service_name):
    """测试心跳报告"""
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "ip_address": ip_address,
        "service_name": service_name
    }
    
    response = requests.post(f"{BASE_URL}/heartbeat/report", 
                           headers=headers, json=data)
    
    print(f"心跳报告 ({service_name}): {response.status_code}")
    if response.status_code == 200:
        print(f"  响应: {response.json()}")
    else:
        print(f"  错误: {response.text}")

def test_system_status(token):
    """测试系统状态查询"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # 设置时间范围为最近24小时
    end_time = int(time.time())
    start_time = end_time - 86400  # 24小时
    
    data = {
        "start_time": start_time,
        "end_time": end_time
    }
    
    response = requests.post(f"{BASE_URL}/heartbeat/status", 
                           headers=headers, json=data)
    
    print(f"\n系统状态查询: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print("服务状态:")
        print(f"  数据采集: {len(result.get('service_status', {}).get('data_collection', []))} 个服务")
        print(f"  kafka进程: {len(result.get('service_status', {}).get('kafka_process', []))} 个服务")
        print(f"  redis: {len(result.get('service_status', {}).get('redis', []))} 个服务")
        print(f"  前端: {len(result.get('service_status', {}).get('frontend', []))} 个服务")
        print(f"  后端: {len(result.get('service_status', {}).get('backend', []))} 个服务")
        print(f"  数据库连接: {result.get('service_status', {}).get('database', {}).get('is_connected', False)}")
        
        print("\n流量统计:")
        traffic = result.get('traffic_status', {})
        print(f"  数据采集到kafka: {len(traffic.get('data_collection_to_kafka', []))} 条记录")
        print(f"  kafka到数据库: {len(traffic.get('kafka_to_database', []))} 条记录")
        print(f"  数据库到后端: {len(traffic.get('database_to_backend', []))} 条记录")
        print(f"  redis到后端: {len(traffic.get('redis_to_backend', []))} 条记录")
        print(f"  后端到前端: {len(traffic.get('backend_to_frontend', []))} 条记录")
    else:
        print(f"  错误: {response.text}")

def main():
    """主测试函数"""
    print("开始测试新的心跳和流量统计功能...")
    
    # 登录
    token = login()
    if not token:
        return
    
    print(f"登录成功，获取到token: {token[:20]}...")
    
    # 模拟各种服务发送心跳
    services = [
        ("192.168.1.10", "数据采集服务1"),
        ("192.168.1.11", "数据采集服务2"),
        ("192.168.1.20", "kafka服务器"),
        ("192.168.1.30", "redis主节点"),
        ("192.168.1.40", "后端服务1"),
        ("192.168.1.41", "后端服务2"),
        ("192.168.1.50", "前端应用1"),
        ("192.168.1.51", "前端应用2"),
    ]
    
    print("\n发送心跳报告...")
    for ip, service in services:
        test_heartbeat_report(token, ip, service)
        time.sleep(0.1)  # 避免请求过快
    
    # 等待一下让数据入库
    time.sleep(1)
    
    # 测试系统状态查询
    test_system_status(token)
    
    print("\n测试完成！")

if __name__ == "__main__":
    main()