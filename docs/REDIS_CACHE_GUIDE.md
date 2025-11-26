# Redis缓存实现指南

## 概述

本项目已集成Redis缓存功能，用于提升后端API性能。根据不同功能的特点，设置了不同的缓存过期时间。

## 缓存策略

### 缓存时间配置

| 功能类别 | 缓存时间 | 说明 |
|---------|---------|------|
| 用户信息、配置信息 | 2小时 | 用户权限、告警规则等变化不频繁的数据 |
| TOP使用率 | 5分钟 | 用于实时展示的使用率排行数据 |
| 历史监控数据 | 10分钟 | 特定IP的历史监控指标数据 |
| 其他功能 | 1分钟 | 活跃IP、评分、告警、心跳等需要较高实时性的数据 |

### 缓存键命名规则

```
# 节点监控相关
node_monitor:active_ips:{start_time}:{end_time}
node_monitor:ip_metrics:{ip}:{start_time}:{end_time}
node_monitor:usage_top:{start_time}:{end_time}:{top_count}:{dimensions}
node_monitor:summary:{start_time}:{end_time}

# 评分系统相关
scoring:machines:{start_time}:{end_time}:{ips}:{include_details}
scoring:machine:{ip}:{start_time}:{end_time}:{include_details}
scoring:summary:{start_time}:{end_time}:{ips}

# 告警管理相关
alert:rules:{rule_type}:{is_active}
alert:alerts:{start_time}:{end_time}:{ips}:{levels}:{types}
alert:alerts:{ip}:{start_time}:{end_time}

# 心跳系统相关
heartbeat:status:{start_time}:{end_time}

# 用户认证相关
user:info:{username}
```

## 环境配置

### 1. 安装依赖

```bash
pip install redis
```

### 2. 配置Redis连接

在 `.env` 文件中添加Redis配置：

```env
# Redis配置
REDIS_URL=redis://localhost:6379/0
```

支持多种连接格式：

```env
# 本地Redis（无密码）
REDIS_URL=redis://localhost:6379/0

# 带密码的Redis
REDIS_URL=redis://password@localhost:6379/0

# 远程Redis
REDIS_URL=redis://username:password@remote-host:6379/0
```

### 3. 启动Redis服务

确保Redis服务已启动：

```bash
# Windows
redis-server

# Linux/macOS
sudo systemctl start redis
# 或
redis-server
```

## 缓存管理API

### 1. 获取缓存状态

```http
GET /cache-management/status
Authorization: Bearer <admin_token>
```

返回Redis状态信息，包括版本、内存使用、键数量等。

### 2. 查看缓存键

```http
GET /cache-management/keys?pattern=node_monitor:*&limit=50
Authorization: Bearer <admin_token>
```

查看匹配模式的缓存键及其TTL。

### 3. 清理缓存

```http
DELETE /cache-management/clear?pattern=node_monitor:*
Authorization: Bearer <admin_token>
```

清理匹配模式的缓存，不提供pattern则清理所有缓存。

## 缓存实现原理

### 1. 缓存装饰器

使用 `@cached` 装饰器自动处理缓存逻辑：

```python
@cached(ttl_seconds=CacheTTL.ONE_MINUTE, key_func=my_cache_key)
async def my_function(param1, param2):
    # 函数逻辑
    return result
```

### 2. 缓存失效

使用 `@invalidate_cache_pattern` 装饰器在数据更新时自动清理相关缓存：

```python
@invalidate_cache_pattern("alert:rules:*")
async def update_rule(rule_id, rule_data):
    # 更新规则逻辑
    return updated_rule
```

### 3. 缓存键生成

支持自定义缓存键生成函数：

```python
def my_cache_key(param1, param2):
    return cache_key("module", "function", param1, param2)
```

## 测试Redis功能

运行测试脚本验证Redis功能：

```bash
python test_redis_cache.py
```

测试内容包括：
- Redis连接测试
- 基本缓存操作
- TTL功能测试
- 模式删除测试

## 性能优化建议

### 1. 缓存预热

系统启动时可以预热常用数据：

```python
# 预热告警规则
await get_alert_rules(rule_type="global", is_active=True)
```

### 2. 缓存监控

定期监控缓存命中率：

```python
# 通过 /cache-management/status 查看缓存统计
keyspace_hits: 1000
keyspace_misses: 100
# 命中率 = 1000 / (1000 + 100) = 90.9%
```

### 3. 内存管理

监控Redis内存使用，必要时清理过期缓存：

```python
# 清理特定模式的缓存
cache.delete_pattern("node_monitor:*")
```

## 故障处理

### Redis连接失败

如果Redis连接失败，系统会自动降级为无缓存模式，所有请求直接查询数据库，不会影响业务功能。

### 缓存不一致

如果发现缓存数据不一致，可以通过管理API清理相关缓存：

```bash
# 清理所有缓存
curl -X DELETE "http://localhost:8000/cache-management/clear" \
     -H "Authorization: Bearer <admin_token>"

# 清理特定模块缓存
curl -X DELETE "http://localhost:8000/cache-management/clear?pattern=node_monitor:*" \
     -H "Authorization: Bearer <admin_token>"
```

## 注意事项

1. **缓存一致性**：数据更新时会自动清理相关缓存，确保一致性
2. **内存限制**：根据服务器内存情况合理设置Redis最大内存
3. **持久化**：生产环境建议启用Redis持久化（RDB或AOF）
4. **安全性**：生产环境应为Redis设置密码，并限制访问IP
5. **监控告警**：建议对Redis的内存使用、连接数等指标设置监控告警

## 常见问题

### Q: Redis连接超时怎么办？
A: 检查Redis服务是否启动，网络是否通畅，防火墙设置是否正确。

### Q: 缓存占用内存过多？
A: 可以通过管理API清理不需要的缓存，或调整Redis的maxmemory配置。

### Q: 如何查看缓存内容？
A: 使用 `/cache-management/keys` API查看缓存键，或使用Redis CLI命令 `redis-cli --scan --pattern "*"`。

### Q: 缓存不生效？
A: 检查Redis连接是否正常，确认函数是否正确使用了 `@cached` 装饰器。