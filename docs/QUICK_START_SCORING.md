# 评分系统快速启动指南

## 概述

本指南帮助您快速启动和使用新的机器评分系统。评分系统基于告警信息计算五个维度（CPU、内存、磁盘、网络、Swap）的分数，并提供总分。

## 快速启动步骤

### 1. 启动服务

```bash
# 确保已安装依赖
pip install -r requirements.txt

# 启动FastAPI服务
uvicorn app.main:app --reload
```

服务将在 `http://localhost:8000` 启动

### 2. 设置演示告警规则

```bash
# 运行演示设置脚本
python demo_scoring_setup.py
```

这个脚本会：
- 使用管理员账户登录
- 清除现有告警规则
- 创建示例告警规则（覆盖CPU、内存、磁盘、网络、Swap五个维度）
- 显示规则汇总

### 3. 测试评分系统

```bash
# 运行评分系统测试
python test_scoring_system.py
```

测试包括：
- 获取所有机器评分
- 获取特定机器详细评分
- 评分汇总统计
- 简化评分模式

### 4. 查看API文档

访问 `http://localhost:8000/docs` 查看完整的API文档

## 主要API接口

### 获取所有机器评分
```bash
# 获取最近24小时的机器评分
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "http://localhost:8000/scoring/machines?start_time=$(($(date +%s)-86400))&end_time=$(date +%s)"
```

### 获取特定机器评分
```bash
# 获取特定机器最近24小时的评分
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "http://localhost:8000/scoring/machines/192.168.1.100?start_time=$(($(date +%s)-86400))&end_time=$(date +%s)"
```

### 获取评分汇总统计
```bash
# 获取最近24小时的评分汇总统计
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "http://localhost:8000/scoring/summary?start_time=$(($(date +%s)-86400))&end_time=$(date +%s)"
```

## 评分规则说明

### 扣分标准
- `info`级别：扣5分
- `warning`级别：扣10分
- `error`级别：扣20分
- `critical`级别：扣40分

### 维度划分
- **CPU**：cpu_usr, cpu_sys, cpu_iow, cpu_usage_rate, system_in, system_cs
- **内存**：mem_total, mem_free, mem_buff, mem_cache, memory_usage_rate
- **磁盘**：disk_total, disk_used, disk_used_percent, disk_iops, disk_r, disk_w
- **网络**：net_rx_kbps, net_tx_kbps, net_rx_kbytes, net_tx_kbytes, network_rate
- **Swap**：swap_total, swap_used, swap_in, swap_out, swap_usage_rate

### 计算方式
- 每个维度初始100分
- 根据告警数量和级别扣分
- 总分 = 五个维度分数的平均值
- 最低0分，不出现负分

## 自定义告警规则

您可以通过告警管理API自定义评分规则：

```bash
# 创建自定义规则
curl -X POST \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "rule_name": "自定义CPU规则",
       "rule_type": "global",
       "condition_field": "cpu_usage_rate",
       "condition_operator": ">",
       "condition_value": 90.0,
       "alert_level": "error",
       "alert_message": "CPU使用率过高：{current_value}%",
       "is_active": true
     }' \
     "http://localhost:8000/alert-management/rules"
```

## 示例响应

### 机器评分响应
```json
{
  "scores": [
    {
      "ip": "192.168.1.100",
      "total_score": 85.5,
      "dimensions": {
        "CPU": {
          "name": "CPU",
          "score": 90.0,
          "alert_count": 1,
          "deductions": [
            {
              "rule_name": "CPU使用率过高-警告",
              "alert_level": "warning",
              "alert_message": "CPU使用率 85.2% 超过警告阈值 80.0%",
              "current_value": 85.2,
              "threshold_value": 80.0,
              "deduction": 10
            }
          ]
        },
        "内存": {"name": "内存", "score": 100.0, "alert_count": 0, "deductions": []},
        "磁盘": {"name": "磁盘", "score": 80.0, "alert_count": 2, "deductions": [...]},
        "网络": {"name": "网络", "score": 100.0, "alert_count": 0, "deductions": []},
        "Swap": {"name": "Swap", "score": 57.0, "alert_count": 1, "deductions": [...]}
      },
      "evaluation_time": "2024-01-01T12:00:00"
    }
  ],
  "total_count": 1,
  "query_time": "2024-01-01T12:00:00"
}
```

## 故障排除

### 1. 无法获取评分
- 确保服务正在运行
- 检查认证token是否有效
- 确认数据库中有监控数据

### 2. 评分都是100分
- 检查告警规则是否已创建并激活
- 确认监控数据是否符合告警条件
- 使用 `/alert-management/alerts` 接口检查是否有告警

### 3. 评分计算异常
- 检查告警规则配置是否正确
- 确认监控字段名称是否匹配
- 查看服务日志获取详细错误信息

## 扩展功能

### 个例规则
可以为特定机器设置不同的评分标准：

```bash
# 为特定IP设置个例规则
curl -X POST \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "rule_name": "特定机器CPU规则",
       "rule_type": "specific",
       "target_ip": "192.168.1.100",
       "condition_field": "cpu_usage_rate",
       "condition_operator": ">",
       "condition_value": 95.0,
       "alert_level": "warning",
       "is_active": true
     }' \
     "http://localhost:8000/alert-management/rules"
```

### 时间范围规则
可以设置规则只在特定时间段生效：

```bash
# 添加时间范围的规则
{
  "rule_name": "工作时间CPU规则",
  "rule_type": "global",
  "condition_field": "cpu_usage_rate",
  "condition_operator": ">",
  "condition_value": 70.0,
  "alert_level": "warning",
  "time_range_start": 1703980800,  // 工作日开始时间
  "time_range_end": 1704016800,    // 工作日结束时间
  "is_active": true
}
```

## 联系支持

如果遇到问题，请：
1. 查看服务日志
2. 检查API响应错误信息
3. 运行测试脚本验证功能
4. 查看完整文档 `README.md`