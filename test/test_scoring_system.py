#!/usr/bin/env python3
"""
评分系统测试脚本
测试机器评分功能是否正常工作
"""

import requests
import json
import time
from datetime import datetime, timedelta

# 配置
BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "admin123"

class ScoringSystemTester:
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
    
    def test_health_check(self):
        """测试健康检查"""
        print("\n测试健康检查...")
        try:
            response = requests.get(f"{self.base_url}/health")
            if response.status_code == 200:
                print("✓ 健康检查通过")
                return True
            else:
                print(f"✗ 健康检查失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ 健康检查异常: {e}")
            return False
    
    def get_time_range(self):
        """获取默认时间范围（最近24小时）"""
        import time
        end_time = int(time.time())
        start_time = end_time - 24 * 60 * 60  # 24小时前
        return start_time, end_time
    
    def test_get_all_scores(self):
        """测试获取所有机器评分"""
        print("\n测试获取所有机器评分...")
        try:
            headers = self.get_headers()
            start_time, end_time = self.get_time_range()
            
            params = {
                "start_time": start_time,
                "end_time": end_time
            }
            response = requests.get(f"{self.base_url}/scoring/machines", 
                                  headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ 获取评分成功，共 {data['total_count']} 台机器")
                print(f"  时间范围: {start_time} - {end_time}")
                
                # 显示前3台机器的评分
                for i, score in enumerate(data['scores'][:3]):
                    print(f"  机器 {i+1}: IP={score['ip']}, 总分={score['total_score']}")
                    for dim_name, dim_score in score['dimensions'].items():
                        print(f"    {dim_name}: {dim_score['score']} (告警数: {dim_score['alert_count']})")
                
                return True
            else:
                print(f"✗ 获取评分失败: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"✗ 获取评分异常: {e}")
            return False
    
    def test_get_machine_score(self):
        """测试获取特定机器评分"""
        print("\n测试获取特定机器评分...")
        try:
            headers = self.get_headers()
            start_time, end_time = self.get_time_range()
            
            # 先获取所有机器，选择第一个进行测试
            params = {
                "start_time": start_time,
                "end_time": end_time
            }
            response = requests.get(f"{self.base_url}/scoring/machines", 
                                  headers=headers, params=params)
            if response.status_code != 200 or not response.json()['scores']:
                print("✗ 无法获取机器列表")
                return False
            
            first_ip = response.json()['scores'][0]['ip']
            print(f"测试机器: {first_ip}")
            
            # 获取该机器的详细评分
            params = {
                "start_time": start_time,
                "end_time": end_time
            }
            response = requests.get(f"{self.base_url}/scoring/machines/{first_ip}", 
                                  headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ 获取机器评分成功")
                print(f"  IP: {data['ip']}")
                print(f"  总分: {data['total_score']}")
                print(f"  评估时间: {data['evaluation_time']}")
                print(f"  时间范围: {start_time} - {end_time}")
                
                for dim_name, dim_score in data['dimensions'].items():
                    print(f"  {dim_name}: {dim_score['score']} (告警数: {dim_score['alert_count']})")
                    if dim_score['deductions']:
                        print(f"    扣分详情:")
                        for deduction in dim_score['deductions']:
                            print(f"      - {deduction['rule_name']}: {deduction['alert_level']} (-{deduction['deduction']}分)")
                
                return True
            else:
                print(f"✗ 获取机器评分失败: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"✗ 获取机器评分异常: {e}")
            return False
    
    def test_scoring_summary(self):
        """测试评分汇总统计"""
        print("\n测试评分汇总统计...")
        try:
            headers = self.get_headers()
            start_time, end_time = self.get_time_range()
            
            params = {
                "start_time": start_time,
                "end_time": end_time
            }
            response = requests.get(f"{self.base_url}/scoring/summary", 
                                  headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ 获取评分汇总成功")
                print(f"  时间范围: {start_time} - {end_time}")
                print(f"  机器总数: {data['total_machines']}")
                print(f"  平均总分: {data['average_score']}")
                print(f"  各维度平均分:")
                for dim, avg_score in data['dimension_averages'].items():
                    print(f"    {dim}: {avg_score}")
                print(f"  分数分布:")
                for range_name, count in data['score_distribution'].items():
                    print(f"    {range_name}: {count}台")
                print(f"  告警统计:")
                print(f"    总告警数: {data['alert_distribution']['total_alerts']}")
                print(f"    按级别: {data['alert_distribution']['by_level']}")
                print(f"    按维度: {data['alert_distribution']['by_dimension']}")
                
                return True
            else:
                print(f"✗ 获取评分汇总失败: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"✗ 获取评分汇总异常: {e}")
            return False
    
    def test_score_without_details(self):
        """测试不包含详细信息的评分"""
        print("\n测试不包含详细信息的评分...")
        try:
            headers = self.get_headers()
            start_time, end_time = self.get_time_range()
            
            params = {
                "start_time": start_time,
                "end_time": end_time,
                "include_details": "false"
            }
            response = requests.get(f"{self.base_url}/scoring/machines", 
                                  headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ 获取简化评分成功，共 {data['total_count']} 台机器")
                print(f"  时间范围: {start_time} - {end_time}")
                
                # 检查是否没有详细信息
                if data['scores']:
                    first_score = data['scores'][0]
                    for dim_name, dim_score in first_score['dimensions'].items():
                        if dim_score['deductions']:
                            print(f"✗ 仍然包含扣分详情")
                            return False
                    print("✓ 确认不包含扣分详情")
                
                return True
            else:
                print(f"✗ 获取简化评分失败: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"✗ 获取简化评分异常: {e}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("评分系统测试开始")
        print("=" * 60)
        
        tests = [
            ("健康检查", self.test_health_check),
            ("登录", self.login),
            ("获取所有机器评分", self.test_get_all_scores),
            ("获取特定机器评分", self.test_get_machine_score),
            ("评分汇总统计", self.test_scoring_summary),
            ("简化评分测试", self.test_score_without_details),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n{'=' * 20} {test_name} {'=' * 20}")
            if test_func():
                passed += 1
                print(f"✓ {test_name} 测试通过")
            else:
                print(f"✗ {test_name} 测试失败")
        
        print("\n" + "=" * 60)
        print(f"测试完成: {passed}/{total} 通过")
        print("=" * 60)
        
        if passed == total:
            print("🎉 所有测试通过！评分系统工作正常。")
        else:
            print("⚠️  部分测试失败，请检查系统配置。")
        
        return passed == total

def main():
    """主函数"""
    tester = ScoringSystemTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()