#!/usr/bin/env python3
"""
测试修改后的/heartbeat/status接口
"""

import requests
import json
import time
from datetime import datetime, timedelta

def test_heartbeat_status():
    """测试心跳状态查询接口"""
    base_url = "http://localhost:8000"
    
    print("开始测试修改后的/heartbeat/status接口...")
    
    # 设置时间范围（最近1小时）
    end_time = int(time.time())
    start_time = end_time - 3600  # 1小时前
    
    # 请求数据
    request_data = {
        "start_time": start_time,
        "end_time": end_time
    }
    
    print(f"查询时间范围: {datetime.fromtimestamp(start_time)} 到 {datetime.fromtimestamp(end_time)}")
    
    try:
        # 注意：这个接口需要管理员权限，需要先登录获取token
        # 这里假设你有认证机制，如果没有，可能需要修改
        
        # 尝试直接请求（可能需要认证）
        response = requests.post(
            f"{base_url}/heartbeat/status",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("请求成功！")
            
            # 重点查看后端到前端的数据
            backend_to_frontend = data.get("backend_to_frontend", [])
            print(f"\n后端到前端连接数: {len(backend_to_frontend)}")
            
            if backend_to_frontend:
                print("\n后端到前端详细数据:")
                for i, connection in enumerate(backend_to_frontend, 1):
                    print(f"  {i}. 后端IP: {connection['source_ip']} -> 前端IP: {connection['target_ip']}, 请求数量: {connection['data_count']}")
            else:
                print("  暂无后端到前端的连接数据")
            
            # 显示其他连接信息
            print(f"\n其他连接信息:")
            print(f"  数据采集到Kafka: {len(data.get('data_collection_to_kafka', []))} 个连接")
            print(f"  Kafka到数据库: {data.get('kafka_to_database', {}).get('data_count', 0)} 条数据")
            print(f"  数据库到后端: {len(data.get('database_to_backend', []))} 个连接")
            print(f"  Redis到后端: {len(data.get('redis_to_backend', []))} 个连接")
            
        elif response.status_code == 401:
            print("需要认证，请先登录获取管理员token")
            print("如果需要认证，请使用以下步骤：")
            print("1. 先调用 /auth/login 获取token")
            print("2. 在请求头中添加: Authorization: Bearer <token>")
            
        else:
            print(f"请求失败: {response.text}")
            
    except Exception as e:
        print(f"请求异常: {e}")
    
    print("\n验证SQL查询（可以在数据库中直接执行）：")
    print("""
-- 验证request_logs表中的数据
SELECT 
    backend_ip,
    frontend_ip,
    COUNT(*) as request_count
FROM request_logs 
WHERE request_time >= NOW() - INTERVAL '1 hour'
GROUP BY backend_ip, frontend_ip
ORDER BY request_count DESC;
    """)

if __name__ == "__main__":
    test_heartbeat_status()