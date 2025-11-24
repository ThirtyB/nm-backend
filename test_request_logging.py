#!/usr/bin/env python3
"""
测试请求日志功能
"""

import requests
import json
import time

def test_request_logging():
    """测试请求日志记录功能"""
    base_url = "http://localhost:8000"
    
    print("开始测试请求日志功能...")
    
    # 测试1: 测试根路径
    print("\n1. 测试根路径访问")
    try:
        response = requests.get(f"{base_url}/")
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
    except Exception as e:
        print(f"请求失败: {e}")
    
    # 测试2: 测试健康检查
    print("\n2. 测试健康检查")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
    except Exception as e:
        print(f"请求失败: {e}")
    
    # 测试3: 测试带查询参数的请求
    print("\n3. 测试带查询参数的请求")
    try:
        response = requests.get(f"{base_url}/users", params={"page": 1, "size": 10})
        print(f"状态码: {response.status_code}")
        if response.status_code != 401:  # 如果需要认证
            print(f"响应: {response.json()}")
        else:
            print("需要认证，这是正常的")
    except Exception as e:
        print(f"请求失败: {e}")
    
    # 测试4: 测试心跳报告（这个不应该被记录）
    print("\n4. 测试心跳报告（不应该被记录）")
    try:
        heartbeat_data = {
            "ip": "192.168.1.100",
            "services": [
                {
                    "name": "test-service",
                    "status": "healthy",
                    "last_check": "2024-01-01T00:00:00Z"
                }
            ]
        }
        response = requests.post(
            f"{base_url}/heartbeat/report",
            json=heartbeat_data,
            headers={"Content-Type": "application/json"}
        )
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
    except Exception as e:
        print(f"请求失败: {e}")
    
    print("\n测试完成！请检查数据库中的request_logs表来验证日志记录。")
    print("预期结果：")
    print("- 根路径访问应该被记录")
    print("- 健康检查应该被记录") 
    print("- 带参数的用户请求应该被记录")
    print("- 心跳报告不应该被记录")
    print("- IP地址如果是127.0.0.1或localhost应该被替换为实际IP")
    
    # 查询验证SQL
    print("\n验证SQL查询：")
    print("SELECT frontend_ip, backend_ip, request_path, request_time FROM request_logs ORDER BY request_time DESC LIMIT 10;")

if __name__ == "__main__":
    test_request_logging()