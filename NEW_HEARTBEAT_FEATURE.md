# 新版心跳和流量统计系统

## 功能概述

新版心跳和流量统计系统提供了更全面的服务监控和流量分析功能，包括：

1. **服务状态监控**：监控各种服务的在线状态
2. **流量统计**：统计不同服务之间的数据流量
3. **数据库连通性测试**：主动测试数据库连接状态

## 服务类型和超时规则

| 服务类型 | 服务名称前缀 | 超时时间 | 说明 |
|---------|-------------|---------|------|
| 数据采集 | "数据采集" | 2分钟 | 数据采集服务 |
| Kafka进程 | "kafka" | 2分钟 | Kafka消息队列 |
| Redis | "redis" | 1分钟 | Redis缓存服务 |
| 后端 | "后端" | 1分钟 | 后端API服务 |
| 前端 | "前端" | 1分钟 | 前端应用 |
| 数据库 | - | 主动测试 | 通过SQL查询测试连通性 |

## API接口

### 1. 服务心跳报告

**接口**: `POST /heartbeat/report`

**请求体**:
```json
{
    "ip_address": "192.168.1.10",
    "service_name": "数据采集服务1"
}
```

**响应**:
```json
{
    "status": "success",
    "message": "探活报告已记录",
    "data": {
        "id": 1,
        "ip_address": "192.168.1.10",
        "service_name": "数据采集服务1",
        "report_time": "2025-11-21T10:30:00.000Z"
    }
}
```

### 2. 系统状态查询

**接口**: `POST /heartbeat/status`

**请求体**:
```json
{
    "start_time": 1700582400,
    "end_time": 1700586000
}
```

**响应**:
```json
{
    "service_status": {
        "data_collection": [
            {
                "service_name": "数据采集服务1",
                "ip_address": "192.168.1.10",
                "is_online": true,
                "last_report_time": "2025-11-21T10:30:00.000Z"
            }
        ],
        "kafka_process": [...],
        "redis": [...],
        "frontend": [...],
        "backend": [...],
        "database": {
            "is_connected": true,
            "connection_time": "2025-11-21T10:30:00.000Z",
            "error_message": null
        }
    },
    "traffic_status": {
        "data_collection_to_kafka": [
            {
                "source_ip": "192.168.1.10",
                "target_ip": "kafka_server",
                "data_count": 150
            }
        ],
        "kafka_to_database": [...],
        "database_to_backend": [...],
        "redis_to_backend": [...],
        "backend_to_frontend": [...]
    }
}
```

## 流量统计说明

系统会统计以下几种流量：

1. **数据采集到Kafka的流量**
   - 统计 `node_monitor_metrics` 表中不同数据采集IP发送的数据条数
   - 按IP分组统计

2. **Kafka到数据库的流量**
   - 统计 `node_monitor_metrics` 表中所有数据采集发来的数据总量
   - 汇总统计

3. **数据库到后端的流量**
   - 统计 `database_access_log` 表中发往不同后端IP的访问次数
   - 按客户端IP分组统计

4. **Redis到后端的流量**
   - 统计 `redis_access_log` 表中发往不同后端IP的访问次数
   - 按客户端IP分组统计

5. **后端到前端的流量**
   - 统计 `access_logs` 表中后端服务发往不同前端IP的访问次数
   - 按客户端IP和服务器IP分组统计

## 权限说明

- **普通用户**: IP地址显示为"隐私保护"，流量统计信息不可见
- **管理员用户**: 可见真实IP地址和完整流量统计信息

## 数据库表结构

### access_logs 表

```sql
CREATE TABLE access_logs (
    id SERIAL PRIMARY KEY,
    client_ip VARCHAR(45) NOT NULL,
    server_ip VARCHAR(45) NOT NULL,
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    access_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    response_time_ms INTEGER,
    status_code INTEGER,
    user_agent TEXT,
    request_size INTEGER,
    response_size INTEGER
);
```

## 部署步骤

1. **创建 access_logs 表**:
   ```bash
   python migrate_access_logs.py
   ```

2. **重启服务**:
   ```bash
   python start_server.py
   ```

3. **测试功能**:
   ```bash
   python test_new_heartbeat.py
   ```

## 注意事项

1. 确保 `access_logs` 表已创建，否则后端到前端的流量统计将无法正常工作
2. 流量统计功能仅对管理员用户可见
3. 时间戳使用Unix时间戳格式（秒）
4. 服务名称必须以指定前缀开头才能被正确分类
5. 数据库连通性测试通过执行 `SELECT 1` 查询来实现

## 故障排除

### 常见问题

1. **access_logs 表不存在错误**
   - 运行 `python migrate_access_logs.py` 创建表

2. **流量统计为空**
   - 检查相关日志表是否有数据
   - 确认时间范围设置正确
   - 确认当前用户是管理员

3. **服务状态显示不准确**
   - 检查服务是否按时发送心跳
   - 确认超时规则设置正确
   - 检查时间戳格式是否正确