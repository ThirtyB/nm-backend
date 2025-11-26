#!/usr/bin/env python3
"""
评分系统时间范围测试脚本
演示如何使用时间参数查询不同时间段的评分
"""

import requests
import json
import time
from datetime import datetime, timedelta

# 配置
BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "admin123"

class ScoringTimeRangeTest:
    def __init__(self):
        self.base_url = BASE_URL
        self.token = None
        
    def login(self):
        """登录获取token"""
        print("正在登录...")
        login_data = {
            "username": USERNAME,
            "password": PASSWORD
        }
        
        try:
            response = requests.post(f"{self.base_url}/auth/login", json=login_data)
            if response.status_code == 200:
                self.token = response.json()["access_token"]
                print("✓ 登录成功")
                return True
            else:
                print(f"✗ 登录失败: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"✗ 登录异常: {e}")
            return False
    
    def get_headers(self):
        """获取认证头"""
        return {"Authorization": f"Bearer {self.token}"}
    
    def format_timestamp(self, timestamp):
        """格式化时间戳为可读字符串"""
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
    
    def test_time_range_scoring(self, start_time, end_time, description):
        """测试指定时间范围的评分"""
        print(f"\n{'='*60}")
        print(f"测试时间范围: {description}")
        print(f"时间: {self.format_timestamp(start_time)} - {self.format_timestamp(end_time)}")
        print(f"{'='*60}")
        
        try:
            headers = self.get_headers()
            params = {
                "start_time": start_time,
                "end_time": end_time
            }
            
            # 获取评分汇总
            response = requests.get(f"{self.base_url}/scoring/summary", 
                                  headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ 获取评分汇总成功")
                print(f"  机器总数: {data['total_machines']}")
                print(f"  平均总分: {data['average_score']}")
                
                if data['total_machines'] > 0:
                    print(f"  各维度平均分:")
                    for dim, avg_score in data['dimension_averages'].items():
                        print(f"    {dim}: {avg_score}")
                    
                    print(f"  分数分布:")
                    for range_name, count in data['score_distribution'].items():
                        if count > 0:
                            print(f"    {range_name}: {count}台")
                    
                    print(f"  告警统计:")
                    print(f"    总告警数: {data['alert_distribution']['total_alerts']}")
                    if data['alert_distribution']['total_alerts'] > 0:
                        print(f"    按级别: {data['alert_distribution']['by_level']}")
                        print(f"    按维度: {data['alert_distribution']['by_dimension']}")
                else:
                    print("  ⚠️ 该时间段内无监控数据")
                
                return True
            else:
                print(f"✗ 获取评分汇总失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"✗ 测试时间范围异常: {e}")
            return False
    
    def test_specific_machine_time_range(self, ip, start_time, end_time, description):
        """测试特定机器在指定时间范围的评分"""
        print(f"\n{'-'*40}")
        print(f"测试机器 {ip} - {description}")
        print(f"时间: {self.format_timestamp(start_time)} - {self.format_timestamp(end_time)}")
        print(f"{'-'*40}")
        
        try:
            headers = self.get_headers()
            params = {
                "start_time": start_time,
                "end_time": end_time,
                "include_details": "true"
            }
            
            response = requests.get(f"{self.base_url}/scoring/machines/{ip}", 
                                  headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ 获取机器评分成功")
                print(f"  IP: {data['ip']}")
                print(f"  总分: {data['total_score']}")
                print(f"  评估时间: {data['evaluation_time']}")
                
                print(f"  各维度评分:")
                for dim_name, dim_score in data['dimensions'].items():
                    print(f"    {dim_name}: {dim_score['score']} (告警数: {dim_score['alert_count']})")
                    if dim_score['deductions']:
                        print(f"      扣分详情:")
                        for deduction in dim_score['deductions']:
                            print(f"        - {deduction['rule_name']}: {deduction['alert_level']} (-{deduction['deduction']}分)")
                
                return True
            else:
                print(f"✗ 获取机器评分失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"✗ 测试机器时间范围异常: {e}")
            return False
    
    def run_time_range_tests(self):
        """运行时间范围测试"""
        print("=" * 80)
        print("评分系统时间范围测试")
        print("=" * 80)
        
        if not self.login():
            return False
        
        # 当前时间
        now = int(time.time())
        
        # 定义不同的时间范围
        time_ranges = [
            {
                "start": now - 1 * 60 * 60,    # 最近1小时
                "end": now,
                "description": "最近1小时"
            },
            {
                "start": now - 6 * 60 * 60,    # 最近6小时
                "end": now,
                "description": "最近6小时"
            },
            {
                "start": now - 24 * 60 * 60,   # 最近24小时
                "end": now,
                "description": "最近24小时"
            },
            {
                "start": now - 7 * 24 * 60 * 60, # 最近7天
                "end": now,
                "description": "最近7天"
            }
        ]
        
        # 测试每个时间范围的评分汇总
        print("\n🔍 测试不同时间范围的评分汇总")
        for time_range in time_ranges:
            self.test_time_range_scoring(
                time_range["start"], 
                time_range["end"], 
                time_range["description"]
            )
        
        # 获取一个机器IP进行详细测试
        try:
            headers = self.get_headers()
            params = {
                "start_time": now - 24 * 60 * 60,
                "end_time": now
            }
            response = requests.get(f"{self.base_url}/scoring/machines", 
                                  headers=headers, params=params)
            
            if response.status_code == 200 and response.json()['scores']:
                test_ip = response.json()['scores'][0]['ip']
                
                print(f"\n🎯 测试特定机器 {test_ip} 在不同时间范围的评分")
                
                # 测试该机器在不同时间范围的评分
                for time_range in time_ranges:
                    self.test_specific_machine_time_range(
                        test_ip,
                        time_range["start"],
                        time_range["end"],
                        time_range["description"]
                    )
            else:
                print("\n⚠️ 无法获取机器IP进行详细测试")
                
        except Exception as e:
            print(f"\n✗ 获取机器IP失败: {e}")
        
        # 测试时间范围边界情况
        print(f"\n🧪 测试时间范围边界情况")
        
        # 测试空时间范围
        print("\n测试空时间范围（应该返回空结果）:")
        empty_start = now - 100
        empty_end = now - 90  # 10秒的时间范围
        self.test_time_range_scoring(empty_start, empty_end, "空时间范围测试")
        
        # 测试未来时间范围
        print("\n测试未来时间范围（应该返回空结果）:")
        future_start = now + 3600
        future_end = now + 7200
        self.test_time_range_scoring(future_start, future_end, "未来时间范围测试")
        
        print("\n" + "=" * 80)
        print("时间范围测试完成！")
        print("=" * 80)
        
        return True

def main():
    """主函数"""
    tester = ScoringTimeRangeTest()
    tester.run_time_range_tests()

if __name__ == "__main__":
    main()