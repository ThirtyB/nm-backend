#!/usr/bin/env python3
"""
测试使用率top接口
"""

import requests
import json
import time
from datetime import datetime, timedelta

# 配置
BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "admin123"

def get_token():
    """获取认证token"""
    login_data = {
        "username": USERNAME,
        "password": PASSWORD
    }
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"登录失败: {response.text}")
        return None

def test_usage_top():
    """测试使用率top接口"""
    token = get_token()
    if not token:
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 设置时间范围（最近24小时）
    end_time = int(time.time())
    start_time = end_time - 24 * 3600
    
    # 测试数据
    test_cases = [
        {
            "name": "测试所有维度top10",
            "data": {
                "start_time": start_time,
                "end_time": end_time,
                "top_count": 10
            }
        },
        {
            "name": "测试指定维度top5",
            "data": {
                "start_time": start_time,
                "end_time": end_time,
                "top_count": 5,
                "dimensions": ["CPU", "内存"]
            }
        },
        {
            "name": "测试单个维度top3",
            "data": {
                "start_time": start_time,
                "end_time": end_time,
                "top_count": 3,
                "dimensions": ["磁盘"]
            }
        }
    ]
    
    for test_case in test_cases:
        print(f"\n=== {test_case['name']} ===")
        response = requests.post(
            f"{BASE_URL}/node-monitor/usage-top",
            headers=headers,
            json=test_case["data"]
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"查询时间范围: {datetime.fromtimestamp(result['time_range']['start_time'])} 到 {datetime.fromtimestamp(result['time_range']['end_time'])}")
            print(f"查询时间: {result['query_time']}")
            
            for dimension_name, dimension_data in result['dimensions'].items():
                print(f"\n{dimension_name} (单位: {dimension_data['unit']}):")
                for i, item in enumerate(dimension_data['top_items'], 1):
                    print(f"  {i}. IP: {item['ip']}, 使用率: {item['usage_rate']}, 时间: {datetime.fromtimestamp(item['latest_timestamp'])}")
                print(f"     时间序列数据点数: {len(item['time_series'])}")
                if item['time_series']:
                    print(f"     时间序列范围: {datetime.fromtimestamp(item['time_series'][0]['timestamp'])} 到 {datetime.fromtimestamp(item['time_series'][-1]['timestamp'])}")
                    print(f"     前3个数据点: {item['time_series'][:3]}")
        else:
            print(f"请求失败: {response.status_code}")
            print(f"错误信息: {response.text}")

def test_interface_format():
    """测试接口输入输出格式"""
    token = get_token()
    if not token:
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 设置时间范围
    end_time = int(time.time())
    start_time = end_time - 3600  # 最近1小时
    
    request_data = {
        "start_time": start_time,
        "end_time": end_time,
        "top_count": 3,
        "dimensions": ["CPU", "内存", "磁盘"]
    }
    
    print("\n=== 接口输入输出格式测试 ===")
    print("输入格式:")
    print(json.dumps(request_data, indent=2, ensure_ascii=False))
    
    response = requests.post(
        f"{BASE_URL}/node-monitor/usage-top",
        headers=headers,
        json=request_data
    )
    
    if response.status_code == 200:
        result = response.json()
        print("\n输出格式:")
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    else:
        print(f"请求失败: {response.status_code}")
        print(f"错误信息: {response.text}")

if __name__ == "__main__":
    print("开始测试使用率top接口...")
    test_usage_top()
    test_interface_format()
    print("\n测试完成!")