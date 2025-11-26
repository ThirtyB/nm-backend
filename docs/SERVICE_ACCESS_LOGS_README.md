# 简化版服务访问日志系统

## 概述

根据需求，重新设计了服务访问日志系统，简化为只记录核心信息：
- **访问后端的客户端IP**
- **被访问服务的真实IP**（数据库或Redis）
- **访问时间**

## 主要改进

### 1. 简化数据结构
**旧表结构**（复杂）：
- `database_access_log` - 包含操作类型、表名、执行时间等详细信息
- `redis_access_log` - 包含操作类型、键名、执行时间等详细信息

**新表结构**（简化）：
```sql
CREATE TABLE service_access_logs (
    id SERIAL PRIMARY KEY,
    client_ip VARCHAR(45) NOT NULL,           -- 访问后端的客户端IP
    service_ip VARCHAR(45) NOT NULL,           -- 被访问的服务IP（数据库或Redis）
    service_type VARCHAR(20) NOT NULL,         -- 服务类型：'database' 或 'redis'
    access_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);
```

### 2. 确保真实IP地址
- **客户端IP**：如果检测到127.0.0.1或localhost，自动获取本机真实IP
- **服务IP**：从配置文件中解析真实的服务IP地址
- **避免127.0.0.1**：所有IP地址都确保是真实有效的网络地址

### 3. 简化日志记录
- **数据库访问**：只记录客户端IP和数据库IP
- **Redis访问**：只记录客户端IP和RedisIP
- **去除冗余信息**：不再记录具体操作、执行时间、错误信息等

## 文件变更

### 新增文件
1. `service_access_logs.sql` - 新表结构定义
2. `migrate_service_access_logs.py` - 表创建迁移脚本
3. `test_service_access_logs.py` - 功能测试脚本
4. `SERVICE_ACCESS_LOGS_README.md` - 本说明文档

### 修改文件
1. `app/models.py` - 添加ServiceAccessLog模型，移除旧的日志模型
2. `app/access_logger.py` - 简化日志记录函数
3. `app/database.py` - 简化数据库访问日志监听器
4. `app/cache.py` - 简化Redis访问日志记录
5. `app/routers/heartbeat.py` - 更新流量统计查询

## 使用方法

### 1. 创建新表
```bash
python migrate_service_access_logs.py
```

### 2. 测试功能
```bash
python test_service_access_logs.py
```

### 3. 启动服务
```bash
python start_server.py
```

## 数据格式示例

### 记录示例
```json
{
  "client_ip": "192.168.16.103",
  "service_ip": "10.1.11.129",
  "service_type": "database",
  "access_time": "2025-11-23 13:45:30.123456"
}
```

### 流量统计示例
```json
{
  "database_to_backend": [
    {
      "source_ip": "10.1.11.129",
      "target_ip": "192.168.16.103",
      "data_count": 25
    }
  ],
  "redis_to_backend": [
    {
      "source_ip": "10.1.11.128",
      "target_ip": "192.168.16.103",
      "data_count": 18
    }
  ]
}
```

## IP地址处理逻辑

### 客户端IP获取
1. 优先使用HTTP请求中的真实客户端IP
2. 如果是127.0.0.1/localhost，自动获取本机真实IP
3. 确保记录的是真实网络地址

### 服务IP提取
1. **数据库IP**：从`DATABASE_URL`解析hostname
2. **Redis IP**：从`REDIS_URL`解析hostname
3. 确保是配置中的真实服务地址

## 配置示例

```env
DATABASE_URL=postgresql://user1:123456@10.1.11.129:5432/db1
REDIS_URL=redis://10.1.11.128:6379/0
```

提取结果：
- 数据库IP：`10.1.11.129`
- Redis IP：`10.1.11.128`

## 性能优化

1. **简化字段**：减少存储空间和查询复杂度
2. **保留索引**：保持查询性能
3. **异步记录**：不影响主要业务逻辑
4. **避免循环日志**：跳过日志表自身的访问记录

## 兼容性说明

- **无新端点**：完全符合要求，没有新增API端点
- **向后兼容**：现有的heartbeat查询接口继续工作
- **数据迁移**：旧表可以保留或手动清理

## 注意事项

1. 执行迁移脚本前请备份数据库
2. 新旧日志表可能同时存在一段时间
3. 建议在测试环境验证后再部署到生产环境
4. 确保配置文件中的IP地址是真实有效的