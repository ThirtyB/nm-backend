# CPU趋势图API使用说明

## 新增的API接口

### 1. CPU平均用量Top N趋势图

**接口地址**: `GET /node-monitor/cpu-trends/average`

**功能**: 获取CPU平均用量最高的Top N个IP的趋势图数据

**查询参数**:
- `start_time` (int, 必填): 开始时间戳（Unix时间戳）
- `end_time` (int, 必填): 结束时间戳（Unix时间戳）
- `top_n` (int, 可选): 返回Top N个IP，默认5，范围1-50

**响应示例**:
```json
{
  "top_ips": [
    {
      "ip": "10.1.11.132",
      "trend_data": [
        {
          "timestamp": 1763522000,
          "cpu_usage": 0.5
        },
        {
          "timestamp": 1763522060,
          "cpu_usage": 0.8
        }
      ],
      "average_cpu": 0.65,
      "max_cpu": 1.2
    }
  ],
  "query_time": "2025-11-20T11:13:42.123456",
  "time_range": {
    "start_time": 1763522000,
    "end_time": 1763608422
  }
}
```

### 2. CPU最高用量Top N趋势图

**接口地址**: `GET /node-monitor/cpu-trends/maximum`

**功能**: 获取CPU最高用量最高的Top N个IP的趋势图数据

**查询参数**:
- `start_time` (int, 必填): 开始时间戳（Unix时间戳）
- `end_time` (int, 必填): 结束时间戳（Unix时间戳）
- `top_n` (int, 可选): 返回Top N个IP，默认5，范围1-50

**响应示例**: 同上

## 使用示例

### JavaScript/Axios示例

```javascript
// 获取CPU平均用量Top 5趋势
const getAverageCpuTrends = async () => {
  const endTime = Math.floor(Date.now() / 1000);
  const startTime = endTime - 24 * 60 * 60; // 24小时前
  
  const response = await axios.get('/node-monitor/cpu-trends/average', {
    params: {
      start_time: startTime,
      end_time: endTime,
      top_n: 5
    },
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  return response.data;
};

// 获取CPU最高用量Top 5趋势
const getMaximumCpuTrends = async () => {
  const endTime = Math.floor(Date.now() / 1000);
  const startTime = endTime - 24 * 60 * 60; // 24小时前
  
  const response = await axios.get('/node-monitor/cpu-trends/maximum', {
    params: {
      start_time: startTime,
      end_time: endTime,
      top_n: 5
    },
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  return response.data;
};
```

### cURL示例

```bash
# 获取CPU平均用量Top 5趋势
curl -X GET "http://localhost:8000/node-monitor/cpu-trends/average?start_time=1763522000&end_time=1763608422&top_n=5" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 获取CPU最高用量Top 5趋势
curl -X GET "http://localhost:8000/node-monitor/cpu-trends/maximum?start_time=1763522000&end_time=1763608422&top_n=5" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 说明

1. **CPU使用率计算**: CPU使用率 = cpu_usr + cpu_sys + cpu_iow
2. **数据过滤**: 只包含CPU三个指标都完整的数据
3. **趋势数据**: 按时间戳升序排列
4. **认证要求**: 需要在请求头中提供有效的JWT token
5. **时间范围**: 建议查询范围不超过7天以保证性能

## Dashboard集成建议

1. 使用ECharts、Chart.js或其他图表库渲染趋势图
2. X轴为时间，Y轴为CPU使用率百分比
3. 不同IP使用不同颜色区分
4. 可以添加工具提示显示具体数值
5. 支持时间范围选择器让用户自定义查询时间段