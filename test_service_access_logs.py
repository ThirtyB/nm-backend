#!/usr/bin/env python3
"""
测试服务访问日志功能
验证数据库和Redis访问日志记录的是后端IP而不是前端IP
"""

import requests
import json
import time

def test_service_access_logs():
    """测试服务访问日志功能"""
    base_url = "http://localhost:8000"
    
    print("开始测试服务访问日志功能...")
    
    # 测试1: 触发数据库访问
    print("\n1. 测试数据库访问日志")
    try:
        # 尝试访问需要查询数据库的接口
        response = requests.get(f"{base_url}/users")
        print(f"状态码: {response.status_code}")
        if response.status_code == 401:
            print("需要认证，这是正常的")
        else:
            print(f"响应: {response.json()}")
    except Exception as e:
        print(f"请求失败: {e}")
    
    # 测试2: 触发Redis访问
    print("\n2. 测试Redis访问日志")
    try:
        # 尝试访问可能使用缓存的接口
        response = requests.get(f"{base_url}/health")
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
    except Exception as e:
        print(f"请求失败: {e}")
    
    # 测试3: 多次访问以产生更多日志
    print("\n3. 多次访问以产生更多日志")
    for i in range(3):
        try:
            response = requests.get(f"{base_url}/")
            print(f"第{i+1}次访问 - 状态码: {response.status_code}")
            time.sleep(0.5)  # 短暂延迟
        except Exception as e:
            print(f"第{i+1}次访问失败: {e}")
    
    print("\n测试完成！")
    print("\n请检查数据库中的service_access_logs表来验证日志记录。")
    print("\n预期结果：")
    print("- client_ip应该记录的是后端服务器的IP地址")
    print("- service_ip应该记录的是数据库或Redis的IP地址")
    print("- 不应该记录前端客户端的IP地址")
    
    print("\n验证SQL查询：")
    print("""
-- 查看最近的服务访问日志
SELECT 
    client_ip,      -- 应该是后端IP
    service_ip,     -- 应该是数据库/Redis IP
    service_type,   -- 'database' 或 'redis'
    access_time
FROM service_access_logs 
ORDER BY access_time DESC 
LIMIT 10;

-- 查看数据库访问统计
SELECT 
    client_ip,
    service_ip,
    COUNT(*) as access_count
FROM service_access_logs 
WHERE service_type = 'database'
GROUP BY client_ip, service_ip
ORDER BY access_count DESC;

-- 查看Redis访问统计
SELECT 
    client_ip,
    service_ip,
    COUNT(*) as access_count
FROM service_access_logs 
WHERE service_type = 'redis'
GROUP BY client_ip, service_ip
ORDER BY access_count DESC;
    """)

if __name__ == "__main__":
    test_service_access_logs()