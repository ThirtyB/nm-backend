# 新功能总结：五维使用率Top接口

## 功能概述

为后端添加了新的接口 `/node-monitor/usage-top`，用于返回一段时间内五维使用率（CPU、内存、磁盘、网络、Swap）的top数据，基于最新数据排序，支持分类管理。

## 新增文件

1. **测试文件**: `test_usage_top.py` - 接口功能测试脚本
2. **API文档**: `USAGE_TOP_API.md` - 详细的接口使用文档
3. **功能总结**: `NEW_FEATURE_SUMMARY.md` - 本文件

## 修改文件

1. **app/routers/node_monitor.py**: 添加新的接口路由和处理逻辑
2. **app/schemas.py**: 添加请求和响应的数据模型

## 接口详情

### 路径和方法
- **URL**: `/node-monitor/usage-top`
- **方法**: POST
- **权限**: 需要认证用户

### 输入格式
```json
{
  "start_time": 1700000000,    // Unix时间戳，必填
  "end_time": 1700003600,      // Unix时间戳，必填
  "top_count": 10,             // 返回top数量，可选，默认10
  "dimensions": ["CPU", "内存", "磁盘", "网络", "Swap"]  // 指定维度，可选，默认全部
}
```

### 输出格式
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
        }
      ]
    },
    "内存": {...},
    "磁盘": {...},
    "网络": {...},
    "Swap": {...}
  },
  "query_time": "2024-01-01T12:00:00"
}
```

## 使用率计算规则

| 维度 | 计算公式 | 单位 |
|------|----------|------|
| CPU | cpu_usr + cpu_sys + cpu_iow | % |
| 内存 | (mem_total - mem_free - mem_buff - mem_cache) / mem_total * 100 | % |
| 磁盘 | disk_used_percent | % |
| 网络 | net_rx_kbps + net_tx_kbps | kbps |
| Swap | swap_used / swap_total * 100 | % |

## 核心特性

1. **基于最新数据**: 每个IP只使用指定时间段内的最新监控数据
2. **降序排序**: 按使用率从高到低排序
3. **分类管理**: 按维度分别返回top数据
4. **灵活查询**: 支持指定时间范围、top数量、维度列表
5. **数据清理**: 自动处理网络数据中的负数
6. **权限控制**: 需要用户认证

## 使用示例

### 查询CPU和内存使用率top5
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

### Python调用
```python
import requests

headers = {"Authorization": "Bearer YOUR_TOKEN", "Content-Type": "application/json"}
data = {
    "start_time": int(time.time()) - 3600,  # 最近1小时
    "end_time": int(time.time()),
    "top_count": 10
}

response = requests.post(
    "http://localhost:8000/node-monitor/usage-top",
    headers=headers,
    json=data
)

result = response.json()
```

## 测试方法

运行测试脚本验证功能：
```bash
python test_usage_top.py
```

测试内容包括：
- 所有维度top10查询
- 指定维度top5查询
- 单个维度top3查询
- 输入输出格式验证

## 技术实现

1. **SQL查询**: 使用窗口函数获取每个IP的最新记录
2. **数据计算**: 复用现有的使用率计算函数
3. **排序处理**: 在内存中按使用率降序排序
4. **数据模型**: 使用Pydantic定义请求和响应模型
5. **错误处理**: 统一的异常处理和错误响应

## 部署说明

新接口已集成到现有的FastAPI应用中，无需额外配置。确保：

1. 数据库中有node_monitor_metrics表的数据
2. 用户认证系统正常工作
3. 服务正常启动（端口8000）

接口文档可通过以下地址访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc