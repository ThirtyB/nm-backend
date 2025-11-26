# 五维使用率Top接口文档

## 接口概述

新增接口用于获取一段时间内五维使用率（CPU、内存、磁盘、网络、Swap）的top数据，基于最新数据排序，支持分类管理。

## 接口信息

- **URL**: `/node-monitor/usage-top`
- **方法**: POST
- **权限**: 需要认证用户
- **标签**: 节点监控

## 输入参数

```json
{
  "start_time": 1700000000,
  "end_time": 1700003600,
  "top_count": 10,
  "dimensions": ["CPU", "内存", "磁盘", "网络", "Swap"]
}
```

### 参数说明

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| start_time | int | 是 | 开始时间戳（Unix时间戳） |
| end_time | int | 是 | 结束时间戳（Unix时间戳） |
| top_count | int | 否 | 返回top数量，默认10 |
| dimensions | array | 否 | 指定维度列表，默认全部维度 |

### 维度可选值

- `"CPU"` - CPU使用率
- `"内存"` - 内存使用率  
- `"磁盘"` - 磁盘使用率
- `"网络"` - 网络速率
- `"Swap"` - Swap使用率

## 输出格式

```json
{
  "time_range": {
    "start_time": 1700000000,
    "end_time": 1700003600
  },
  "dimensions": {
    "CPU": {
      "name": "CPU",
      "unit": "%",
      "top_items": [
        {
          "ip": "192.168.1.100",
          "usage_rate": 85.5,
          "latest_timestamp": 1700003500
        },
        {
          "ip": "192.168.1.101", 
          "usage_rate": 78.2,
          "latest_timestamp": 1700003400
        }
      ]
    },
    "内存": {
      "name": "内存",
      "unit": "%",
      "top_items": [...]
    },
    "磁盘": {
      "name": "磁盘", 
      "unit": "%",
      "top_items": [...]
    },
    "网络": {
      "name": "网络",
      "unit": "kbps", 
      "top_items": [...]
    },
    "Swap": {
      "name": "Swap",
      "unit": "%",
      "top_items": [...]
    }
  },
  "query_time": "2024-01-01T12:00:00"
}
```

### 输出字段说明

| 字段名 | 类型 | 说明 |
|--------|------|------|
| time_range | object | 查询时间范围 |
| dimensions | object | 各维度top数据 |
| query_time | datetime | 查询时间 |

#### 维度数据结构

| 字段名 | 类型 | 说明 |
|--------|------|------|
| name | string | 维度名称 |
| unit | string | 单位 |
| top_items | array | top项目列表 |

#### top项目结构

| 字段名 | 类型 | 说明 |
|--------|------|------|
| ip | string | IP地址 |
| usage_rate | float | 最新使用率 |
| latest_timestamp | int | 最新数据时间戳 |
| time_series | array | 使用率时间序列 |

#### 时间序列结构

| 字段名 | 类型 | 说明 |
|--------|------|------|
| timestamp | int | 时间戳 |
| usage_rate | float | 该时间点的使用率 |

## 使用率计算规则

### CPU使用率
```
CPU使用率 = cpu_usr + cpu_sys + cpu_iow
单位：%
```

### 内存使用率
```
内存使用率 = (1 - mem_free / mem_total) * 100
单位：%
```

### 磁盘使用率
```
磁盘使用率 = disk_used_percent
单位：%
```

### 网络使用率
```
网络使用率 = net_rx_kbps + net_tx_kbps
单位：kbps
```

### Swap使用率
```
Swap使用率 = swap_used / swap_total * 100
单位：%
```

## 使用示例

### 1. 查询所有维度top10

```bash
curl -X POST "http://localhost:8000/node-monitor/usage-top" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "start_time": 1700000000,
    "end_time": 1700003600,
    "top_count": 10
  }'
```

### 2. 查询指定维度top5

```bash
curl -X POST "http://localhost:8000/node-monitor/usage-top" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "start_time": 1700000000,
    "end_time": 1700003600,
    "top_count": 5,
    "dimensions": ["CPU", "内存"]
  }'
```

### 3. Python调用示例

```python
import requests

headers = {
    "Authorization": "Bearer YOUR_TOKEN",
    "Content-Type": "application/json"
}

data = {
    "start_time": 1700000000,
    "end_time": 1700003600,
    "top_count": 10,
    "dimensions": ["CPU", "内存", "磁盘"]
}

response = requests.post(
    "http://localhost:8000/node-monitor/usage-top",
    headers=headers,
    json=data
)

result = response.json()
print(result)
```

## 特性说明

1. **基于最新数据**: 每个IP只使用指定时间段内的最新监控数据
2. **降序排序**: 按使用率从高到低排序
3. **分类管理**: 按维度分别返回top数据
4. **灵活查询**: 支持指定时间范围、top数量、维度列表
5. **数据清理**: 自动处理网络数据中的负数，负数视为0
6. **权限控制**: 需要用户认证，普通用户和管理员均可访问

## 错误处理

| 错误码 | 说明 |
|--------|------|
| 401 | 未认证或token无效 |
| 500 | 服务器内部错误 |

## 测试

项目提供了测试脚本 `test_usage_top.py`，可以用来测试接口功能：

```bash
python test_usage_top.py
```

测试脚本会验证：
- 所有维度top10查询
- 指定维度top5查询  
- 单个维度top3查询
- 输入输出格式