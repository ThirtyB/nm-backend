# 服务心跳检查定时任务

## 功能概述

新增了一个定时任务，每30秒自动检查以下服务的状态并记录到数据库：

1. **后端服务** - 获取当前后端的IP地址
2. **Redis服务** - 获取配置的Redis IP地址并测试连接
3. **数据库服务** - 获取配置的数据库IP地址并测试连接

## 实现细节

### 文件结构
- `app/heartbeat_checker.py` - 心跳检查器核心逻辑
- `app/main.py` - 集成心跳检查任务到应用启动/关闭事件
- `test_heartbeat_checker.py` - 测试脚本

### 数据记录格式
所有记录都写入 `service_heartbeat` 表，符合现有数据库格式：

| 字段 | 值 |
|------|-----|
| `service_name` | "后端"、"redis"、"postgres" |
| `ip_address` | 各服务的实际IP地址 |
| `report_time` | 当前时间戳 |
| `created_at` | 记录创建时间 |

### 检查逻辑
- **后端服务**：始终记录为在线（因为服务本身在运行）
- **Redis服务**：通过 `redis.ping()` 测试连接
- **数据库服务**：通过 `psycopg2.connect()` 测试连接

### 定时任务
- **间隔**：30秒
- **启动方式**：应用启动时自动启动后台任务
- **停止方式**：应用关闭时自动停止

## 使用方法

### 启动服务
```bash
python start_server.py
```

服务启动后会自动开始心跳检查，日志输出：
```
INFO:app.main:心跳检查任务已启动
INFO:app.heartbeat_checker:启动服务心跳检查定时任务...
INFO:app.heartbeat_checker:记录心跳成功 - 服务: 后端, IP: 192.168.16.103
INFO:app.heartbeat_checker:记录心跳成功 - 服务: redis, IP: 10.1.11.128
INFO:app.heartbeat_checker:记录心跳成功 - 服务: postgres, IP: 10.1.11.129
```

### 测试功能
```bash
python test_heartbeat_checker.py
```

### 查看记录
```python
from app.database import SessionLocal
from app.models import ServiceHeartbeat
from datetime import datetime, timedelta

db = SessionLocal()
recent_records = db.query(ServiceHeartbeat).filter(
    ServiceHeartbeat.report_time >= datetime.utcnow() - timedelta(minutes=5),
    ServiceHeartbeat.service_name.in_(['后端', 'redis', 'postgres'])
).all()
db.close()
```

## 配置依赖

### requirements.txt 新增依赖
```
psycopg2  # 用于直接测试数据库连接
```

### 环境变量
使用现有的配置：
- `DATABASE_URL` - 数据库连接URL
- `REDIS_URL` - Redis连接URL

## 注意事项

1. **不创建新端点**：完全符合要求，没有新增任何API端点
2. **数据库格式**：完全符合现有 `service_heartbeat` 表结构
3. **服务命名**：按要求使用"后端"、"redis"、"postgres"
4. **错误处理**：连接失败时会记录警告日志，但不影响定时任务继续运行
5. **资源管理**：每个数据库连接都会正确关闭，避免连接泄漏

## 日志示例

```
INFO:app.heartbeat_checker:记录心跳成功 - 服务: 后端, IP: 192.168.16.103
INFO:app.heartbeat_checker:记录心跳成功 - 服务: redis, IP: 10.1.11.128
INFO:app.heartbeat_checker:记录心跳成功 - 服务: postgres, IP: 10.1.11.129
```

当服务不可用时：
```
WARNING:app.heartbeat_checker:服务不可用 - 服务: redis, IP: 10.1.11.128
ERROR:app.heartbeat_checker:Redis连接测试失败: Connection refused
```