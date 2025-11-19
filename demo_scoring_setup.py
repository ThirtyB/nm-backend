#!/usr/bin/env python3
"""
评分系统演示设置脚本
创建示例告警规则来演示评分系统功能
"""

import requests
import json

# 配置
BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "admin123"

class ScoringDemoSetup:
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
    
    def create_alert_rule(self, rule_data):
        """创建告警规则"""
        try:
            headers = self.get_headers()
            response = requests.post(f"{self.base_url}/alert-management/rules", 
                                   json=rule_data, headers=headers)
            
            if response.status_code == 200:
                rule = response.json()
                print(f"✓ 创建规则成功: {rule['rule_name']} (ID: {rule['id']})")
                return rule
            else:
                print(f"✗ 创建规则失败: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"✗ 创建规则异常: {e}")
            return None
    
    def clear_existing_rules(self):
        """清除现有规则"""
        print("\n清除现有告警规则...")
        try:
            headers = self.get_headers()
            response = requests.get(f"{self.base_url}/alert-management/rules", headers=headers)
            
            if response.status_code == 200:
                rules = response.json()
                for rule in rules:
                    delete_response = requests.delete(
                        f"{self.base_url}/alert-management/rules/{rule['id']}", 
                        headers=headers
                    )
                    if delete_response.status_code == 200:
                        print(f"  ✓ 删除规则: {rule['rule_name']}")
                    else:
                        print(f"  ✗ 删除规则失败: {rule['rule_name']}")
                
                print(f"✓ 清除完成，共删除 {len(rules)} 个规则")
                return True
            else:
                print(f"✗ 获取规则列表失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ 清除规则异常: {e}")
            return False
    
    def setup_demo_rules(self):
        """设置演示规则"""
        print("\n设置演示告警规则...")
        
        demo_rules = [
            # CPU相关规则
            {
                "rule_name": "CPU使用率过高-警告",
                "rule_type": "global",
                "condition_field": "cpu_usage_rate",
                "condition_operator": ">",
                "condition_value": 80.0,
                "alert_level": "warning",
                "alert_message": "CPU使用率 {current_value}% 超过警告阈值 {threshold_value}%",
                "is_active": True
            },
            {
                "rule_name": "CPU使用率过高-严重",
                "rule_type": "global",
                "condition_field": "cpu_usage_rate",
                "condition_operator": ">",
                "condition_value": 95.0,
                "alert_level": "critical",
                "alert_message": "CPU使用率 {current_value}% 达到严重级别 {threshold_value}%",
                "is_active": True
            },
            
            # 内存相关规则
            {
                "rule_name": "内存使用率过高-警告",
                "rule_type": "global",
                "condition_field": "memory_usage_rate",
                "condition_operator": ">",
                "condition_value": 85.0,
                "alert_level": "warning",
                "alert_message": "内存使用率 {current_value}% 超过警告阈值 {threshold_value}%",
                "is_active": True
            },
            {
                "rule_name": "内存使用率过高-错误",
                "rule_type": "global",
                "condition_field": "memory_usage_rate",
                "condition_operator": ">",
                "condition_value": 95.0,
                "alert_level": "error",
                "alert_message": "内存使用率 {current_value}% 达到错误级别 {threshold_value}%",
                "is_active": True
            },
            
            # 磁盘相关规则
            {
                "rule_name": "磁盘使用率过高-信息",
                "rule_type": "global",
                "condition_field": "disk_used_percent",
                "condition_operator": ">",
                "condition_value": 70.0,
                "alert_level": "info",
                "alert_message": "磁盘使用率 {current_value}% 超过信息阈值 {threshold_value}%",
                "is_active": True
            },
            {
                "rule_name": "磁盘使用率过高-警告",
                "rule_type": "global",
                "condition_field": "disk_used_percent",
                "condition_operator": ">",
                "condition_value": 85.0,
                "alert_level": "warning",
                "alert_message": "磁盘使用率 {current_value}% 超过警告阈值 {threshold_value}%",
                "is_active": True
            },
            {
                "rule_name": "磁盘使用率过高-严重",
                "rule_type": "global",
                "condition_field": "disk_used_percent",
                "condition_operator": ">",
                "condition_value": 95.0,
                "alert_level": "critical",
                "alert_message": "磁盘使用率 {current_value}% 达到严重级别 {threshold_value}%",
                "is_active": True
            },
            
            # 网络相关规则
            {
                "rule_name": "网络速率过高-信息",
                "rule_type": "global",
                "condition_field": "network_rate",
                "condition_operator": ">",
                "condition_value": 10000.0,  # 10MB/s
                "alert_level": "info",
                "alert_message": "网络速率 {current_value} KB/s 超过信息阈值 {threshold_value} KB/s",
                "is_active": True
            },
            
            # Swap相关规则
            {
                "rule_name": "Swap使用率过高-警告",
                "rule_type": "global",
                "condition_field": "swap_usage_rate",
                "condition_operator": ">",
                "condition_value": 50.0,
                "alert_level": "warning",
                "alert_message": "Swap使用率 {current_value}% 超过警告阈值 {threshold_value}%",
                "is_active": True
            },
            {
                "rule_name": "Swap使用率过高-错误",
                "rule_type": "global",
                "condition_field": "swap_usage_rate",
                "condition_operator": ">",
                "condition_value": 80.0,
                "alert_level": "error",
                "alert_message": "Swap使用率 {current_value}% 达到错误级别 {threshold_value}%",
                "is_active": True
            }
        ]
        
        created_rules = []
        for rule_data in demo_rules:
            rule = self.create_alert_rule(rule_data)
            if rule:
                created_rules.append(rule)
        
        print(f"\n✓ 演示规则设置完成，共创建 {len(created_rules)} 个规则")
        return created_rules
    
    def show_rules_summary(self):
        """显示规则汇总"""
        print("\n当前告警规则汇总:")
        try:
            headers = self.get_headers()
            response = requests.get(f"{self.base_url}/alert-management/rules", headers=headers)
            
            if response.status_code == 200:
                rules = response.json()
                
                # 按维度分组
                dimensions = {
                    "CPU": [],
                    "内存": [],
                    "磁盘": [],
                    "网络": [],
                    "Swap": []
                }
                
                for rule in rules:
                    field = rule['condition_field']
                    if 'cpu' in field:
                        dimensions["CPU"].append(rule)
                    elif 'mem' in field or 'memory' in field:
                        dimensions["内存"].append(rule)
                    elif 'disk' in field:
                        dimensions["磁盘"].append(rule)
                    elif 'net' in field or 'network' in field:
                        dimensions["网络"].append(rule)
                    elif 'swap' in field:
                        dimensions["Swap"].append(rule)
                
                for dim, dim_rules in dimensions.items():
                    if dim_rules:
                        print(f"\n{dim}维度规则:")
                        for rule in dim_rules:
                            print(f"  - {rule['rule_name']} ({rule['alert_level']}): {rule['condition_field']} {rule['condition_operator']} {rule['condition_value']}")
                
                return True
            else:
                print(f"✗ 获取规则失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ 显示规则汇总异常: {e}")
            return False
    
    def run_demo(self):
        """运行演示设置"""
        print("=" * 60)
        print("评分系统演示设置")
        print("=" * 60)
        
        if not self.login():
            return False
        
        # 清除现有规则
        if not self.clear_existing_rules():
            return False
        
        # 设置演示规则
        rules = self.setup_demo_rules()
        if not rules:
            return False
        
        # 显示规则汇总
        self.show_rules_summary()
        
        print("\n" + "=" * 60)
        print("演示设置完成！")
        print("现在可以运行以下命令测试评分系统:")
        print("1. python test_scoring_system.py")
        print("2. 访问 http://localhost:8000/docs 查看API文档")
        print("3. 调用 /scoring/machines 接口获取机器评分")
        print("=" * 60)
        
        return True

def main():
    """主函数"""
    setup = ScoringDemoSetup()
    setup.run_demo()

if __name__ == "__main__":
    main()