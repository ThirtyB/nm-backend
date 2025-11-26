#!/usr/bin/env python3
"""
节点监控API测试脚本
"""

import requests
import json
import time
from datetime import datetime, timedelta

# API基础URL
BASE_URL = "http://localhost:8000"

def test_api_endpoints():
    """测试所有API端点"""
    
    print("🚀 开始测试节点监控API...")
    
    # 1. 测试健康检查
    print("\n1. 测试健康检查...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
    except Exception as e:
        print(f"   ❌ 错误: {e}")
        return
    
    # 2. 用户登录获取token
    print("\n2. 用户登录...")
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        if response.status_code == 200:
            token = response.json()["access_token"]
            print(f"   ✅ 登录成功，获取token")
            headers = {"Authorization": f"Bearer {token}"}
        else:
            print(f"   ❌ 登录失败: {response.status_code} - {response.text}")
            return
    except Exception as e:
        print(f"   ❌ 登录错误: {e}")
        return
    
    # 3. 准备测试时间范围（最近24小时）
    end_time = int(time.time())
    start_time = end_time - 24 * 60 * 60  # 24小时前
    
    print(f"\n3. 测试时间范围: {start_time} 到 {end_time}")
    print(f"   开始时间: {datetime.fromtimestamp(start_time)}")
    print(f"   结束时间: {datetime.fromtimestamp(end_time)}")
    
    # 4. 测试获取活跃IP列表
    print("\n4. 测试获取活跃IP列表...")
    try:
        url = f"{BASE_URL}/node-monitor/active-ips"
        params = {
            "start_time": start_time,
            "end_time": end_time
        }
        response = requests.get(url, params=params, headers=headers)
        print(f"   状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ 成功获取活跃IP列表")
            print(f"   活跃IP数量: {data['total_count']}")
            
            if data['active_ips']:
                first_ip = data['active_ips'][0]
                print(f"   第一个IP: {first_ip['ip']}")
                print(f"   最新时间戳: {first_ip['latest_ts']}")
                print(f"   CPU使用率: {first_ip['cpu_usage_rate']}%")
                print(f"   内存使用率: {first_ip['memory_usage_rate']}%")
                print(f"   磁盘使用率: {first_ip['disk_usage_rate']}%")
                print(f"   Swap使用率: {first_ip['swap_usage_rate']}%")
                print(f"   网络速率: {first_ip['network_rate']} kbps")
                
                # 检查网络速率是否为负数
                if first_ip['network_rate'] is not None and first_ip['network_rate'] < 0:
                    print(f"   ⚠️  发现负数网络速率: {first_ip['network_rate']}")
                else:
                    print(f"   ✅ 网络速率正常: {first_ip['network_rate']}")
                
                # 保存第一个IP用于下一个测试
                test_ip = first_ip['ip']
            else:
                print("   ⚠️  没有找到活跃的IP")
                test_ip = None
        else:
            print(f"   ❌ 请求失败: {response.text}")
            test_ip = None
    except Exception as e:
        print(f"   ❌ 错误: {e}")
        test_ip = None
    
    # 5. 测试获取特定IP的详细监控数据
    if test_ip:
        print(f"\n5. 测试获取IP {test_ip} 的详细监控数据...")
        try:
            url = f"{BASE_URL}/node-monitor/ip-metrics/{test_ip}"
            params = {
                "start_time": start_time,
                "end_time": end_time
            }
            response = requests.get(url, params=params, headers=headers)
            print(f"   状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ 成功获取IP详细数据")
                print(f"   记录数量: {len(data)}")
                
                if data:
                    first_record = data[0]
                    print(f"   第一条记录时间戳: {first_record['ts']}")
                    print(f"   CPU用户态: {first_record['cpu_usr']}%")
                    print(f"   CPU系统态: {first_record['cpu_sys']}%")
                    print(f"   内存总量: {first_record['mem_total']} bytes")
                    print(f"   内存空闲: {first_record['mem_free']} bytes")
                    print(f"   网络接收速率: {first_record['net_rx_kbps']} kbps")
                    print(f"   网络发送速率: {first_record['net_tx_kbps']} kbps")
                    
                    # 检查网络速率是否为负数
                    if first_record['net_rx_kbps'] is not None and first_record['net_rx_kbps'] < 0:
                        print(f"   ⚠️  发现负数网络接收速率: {first_record['net_rx_kbps']}")
                    else:
                        print(f"   ✅ 网络接收速率正常: {first_record['net_rx_kbps']}")
                        
                    if first_record['net_tx_kbps'] is not None and first_record['net_tx_kbps'] < 0:
                        print(f"   ⚠️  发现负数网络发送速率: {first_record['net_tx_kbps']}")
                    else:
                        print(f"   ✅ 网络发送速率正常: {first_record['net_tx_kbps']}")
            else:
                print(f"   ❌ 请求失败: {response.text}")
        except Exception as e:
            print(f"   ❌ 错误: {e}")
    
    # 6. 测试获取监控汇总信息
    print("\n6. 测试获取监控汇总信息...")
    try:
        url = f"{BASE_URL}/node-monitor/summary"
        params = {
            "start_time": start_time,
            "end_time": end_time
        }
        response = requests.get(url, params=params, headers=headers)
        print(f"   状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ 成功获取监控汇总信息")
            print(f"   活跃IP数量: {data['active_ip_count']}")
            print(f"   总记录数: {data['total_records']}")
        else:
            print(f"   ❌ 请求失败: {response.text}")
    except Exception as e:
        print(f"   ❌ 错误: {e}")
    
    # 7. 验证网络负数处理
    print("\n7. 验证网络负数处理...")
    try:
        # 查找有负数网络数据的IP
        url = f"{BASE_URL}/node-monitor/active-ips"
        params = {
            "start_time": start_time - 7*24*60*60,  # 扩大时间范围
            "end_time": end_time
        }
        response = requests.get(url, params=params, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            negative_network_found = False
            
            for ip_data in data['active_ips']:
                if ip_data['network_rate'] is not None and ip_data['network_rate'] < 0:
                    print(f"   ❌ 发现负数网络速率: IP {ip_data['ip']}, 速率: {ip_data['network_rate']}")
                    negative_network_found = True
                elif ip_data['network_rate'] == 0:
                    print(f"   ✅ 网络速率为0（可能是负数被清理）: IP {ip_data['ip']}")
            
            if not negative_network_found:
                print("   ✅ 没有发现负数网络速率，修复成功！")
        else:
            print(f"   ⚠️  无法验证网络负数处理: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ 验证网络负数处理失败: {e}")
    
    print("\n🎉 API测试完成!")

def print_api_info():
    """打印API信息"""
    print("=" * 60)
    print("节点监控API信息")
    print("=" * 60)
    print(f"API文档地址: {BASE_URL}/docs")
    print(f"健康检查: {BASE_URL}/health")
    print()
    print("主要端点:")
    print("1. GET /node-monitor/active-ips")
    print("   - 获取时间段内活跃的IP及其最新五维数据")
    print("   - 参数: start_time, end_time (时间戳)")
    print()
    print("2. GET /node-monitor/ip-metrics/{ip}")
    print("   - 获取特定IP在时间段内的所有监控记录")
    print("   - 参数: ip (路径参数), start_time, end_time (查询参数)")
    print()
    print("3. GET /node-monitor/summary")
    print("   - 获取监控数据的汇总信息")
    print("   - 参数: start_time, end_time (查询参数)")
    print()
    print("五维数据说明:")
    print("- CPU使用率: cpu_usr + cpu_sys + cpu_iow")
    print("- 内存使用率: (1 - mem_free / mem_total) * 100")
    print("- 磁盘使用率: disk_used_percent")
    print("- Swap使用率: swap_used / swap_total * 100")
    print("- 网络速率: net_rx_kbps + net_tx_kbps (负数已处理为0)")
    print()
    print("网络负数处理说明:")
    print("- 原因: 网络计数器重置或时间戳问题导致计算出现负数")
    print("- 处理: 将负数网络速率视为0，避免显示异常数据")
    print("=" * 60)

if __name__ == "__main__":
    print_api_info()
    print()
    test_api_endpoints()