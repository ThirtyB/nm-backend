# 请求日志功能说明

## 功能概述

新增的请求日志功能会记录所有API请求的信息（除了`/heartbeat/report`路径），包括前端IP、后端IP、请求时间、响应时间等详细信息。

## 数据库表结构

执行`request_logs.sql`文件来创建相应的数据库表：

```bash
psql -d your_database -f request_logs.sql
```

### 表字段说明

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | SERIAL | 主键 |
| frontend_ip | VARCHAR(45) | 前端IP地址（支持IPv6） |
| backend_ip | VARCHAR(45) | 后端服务器IP地址 |
| request_method | VARCHAR(10) | HTTP方法（GET、POST等） |
| request_path | VARCHAR(500) | 请求路径 |
| query_params | TEXT | 查询参数（JSON格式） |
| request_time | TIMESTAMP | 请求时间 |
| response_status | INTEGER | HTTP响应状态码 |
| response_time_ms | INTEGER | 响应时间（毫秒） |
| user_agent | TEXT | 客户端用户代理字符串 |
| created_at | TIMESTAMP | 记录创建时间 |

## 功能特性

1. **自动记录**: 所有API请求都会被自动记录
2. **排除特定路径**: `/heartbeat/report`路径不会被记录
3. **IP地址获取**: 支持代理服务器环境下的真实IP获取
4. **性能监控**: 记录请求响应时间
5. **详细信息**: 记录请求方法、路径、参数等完整信息

## 使用方法

### 1. 执行SQL文件

首先执行SQL文件创建表结构：

```bash
psql -d your_database -f request_logs.sql
```

### 2. 重启应用

重启FastAPI应用以启用新的中间件。

### 3. 测试功能

运行测试脚本验证功能：

```bash
python test_request_logging.py
```

### 4. 查看日志

查询数据库中的请求日志：

```sql
-- 查看最近的请求记录
SELECT * FROM request_logs ORDER BY request_time DESC LIMIT 10;

-- 查看特定IP的请求
SELECT * FROM request_logs WHERE frontend_ip = '192.168.1.100' ORDER BY request_time DESC;

-- 查看响应时间超过1秒的请求
SELECT * FROM request_logs WHERE response_time_ms > 1000 ORDER BY request_time DESC;

-- 统计各路径的请求次数
SELECT request_path, COUNT(*) as count 
FROM request_logs 
GROUP BY request_path 
ORDER BY count DESC;
```

## 配置说明

### 中间件配置

请求日志中间件在`app/main.py`中配置：

```python
from app.access_logger import RequestLoggingMiddleware

# 添加请求日志中间件
app.add_middleware(RequestLoggingMiddleware)
```

### 排除路径

默认排除`/heartbeat/report`路径，如需修改排除的路径，可以在`RequestLoggingMiddleware`的`dispatch`方法中修改：

```python
# 跳过特定路径的记录
if request.url.path == "/heartbeat/report":
    response = await call_next(request)
    return response
```

## 性能影响

- 中间件异步记录日志，对请求性能影响很小
- 数据库操作在后台执行，不会阻塞请求响应
- 建议定期清理历史日志数据以保持性能

## 故障排除

### 1. 日志记录失败

如果日志记录失败，检查：
- 数据库连接是否正常
- 表结构是否正确创建
- 应用日志中的错误信息

### 2. IP地址获取不准确

如果IP地址获取不准确，检查：
- 是否使用了代理服务器
- `X-Forwarded-For`和`X-Real-IP`头信息是否正确
- 网络配置是否正确

**注意**：系统会自动将以下本地地址替换为实际IP地址：
- `127.0.0.1`
- `localhost` 
- `::1` (IPv6本地地址)

这是为了确保记录的IP地址是真实的网络地址，而不是本地回环地址。

## 服务访问日志说明

### 数据库和Redis访问日志

系统会记录后端服务对数据库和Redis的访问，记录的是：
- **client_ip**: 后端服务器的IP地址（不是前端客户端IP）
- **service_ip**: 数据库或Redis服务器的IP地址
- **service_type**: 服务类型（'database' 或 'redis'）

### 日志记录逻辑

1. **数据库访问**: 每次SQL操作都会记录后端IP到数据库IP的访问
2. **Redis访问**: 每次Redis操作都会记录后端IP到Redis IP的访问
3. **自动IP转换**: 本地地址会自动转换为实际网络IP

### 验证方法

```sql
-- 查看服务访问日志
SELECT client_ip, service_ip, service_type, access_time
FROM service_access_logs 
ORDER BY access_time DESC LIMIT 10;
```

### 3. 性能问题

如果出现性能问题：
- 检查数据库索引是否创建
- 考虑定期清理历史数据
- 监控数据库连接池状态

## 与心跳状态接口的集成

`/heartbeat/status`接口已经更新，现在会从`request_logs`表中查询后端到前端的连接数据：

### 返回数据格式

```json
{
  "backend_to_frontend": [
    {
      "source_ip": "192.168.1.100",  // 后端IP
      "target_ip": "192.168.1.50",    // 前端IP
      "data_count": 150               // 请求次数
    }
  ]
}
```

### 查询逻辑

- 按时间范围查询`request_logs`表
- 按`backend_ip`和`frontend_ip`分组统计请求次数
- 返回每个后端IP到前端IP的连接数据量

## 扩展功能

可以考虑添加的功能：
1. 日志数据可视化界面
2. 异常请求告警
3. 请求统计分析
4. 日志数据导出功能
5. 实时请求监控面板