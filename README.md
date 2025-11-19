# 资源监视器后端

基于FastAPI的用户管理系统，支持用户注册、登录和权限管理，以及节点监控数据查询功能。

## 项目结构

```
app/
├── __init__.py
├── main.py          # FastAPI应用入口
├── config.py        # 配置管理
├── database.py      # 数据库连接
├── models.py        # 数据模型
├── schemas.py       # Pydantic模型
├── auth.py          # 认证相关
└── routers/
    ├── __init__.py
    ├── auth.py      # 认证路由
    ├── users.py     # 用户管理路由
    └── node_monitor.py  # 节点监控路由
```

## 安装和运行

### 1. 创建虚拟环境

```bash
python -m venv venv
venv\Scripts\activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

编辑 `.env` 文件，修改必要的配置：

```env
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
DATABASE_URL=sqlite:///./resource_monitor.db
```

### 4. 初始化数据库并创建管理员

```bash
python init_db.py
```

默认管理员账户：
- 用户名：admin
- 密码：admin123

### 5. 启动服务

```bash
uvicorn app.main:app --reload
```

服务将在 `http://localhost:8000` 启动

## API文档

启动服务后，访问以下地址查看API文档：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API接口

### 认证接口

#### 用户登录
- **POST** `/auth/login`
- 请求体：
```json
{
  "username": "admin",
  "password": "admin123"
}
```
- 响应：
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

### 用户管理接口（需要管理员权限）

#### 创建用户
- **POST** `/users/`
- 请求体：
```json
{
  "username": "newuser",
  "password": "password123",
  "user_type": "user"
}
```

#### 获取用户列表
- **GET** `/users/`

#### 获取单个用户
- **GET** `/users/{user_id}`

#### 更新用户
- **PUT** `/users/{user_id}`
- 请求体：
```json
{
  "username": "updateduser",
  "password": "newpassword123",
  "user_type": "admin"
}
```

#### 删除用户
- **DELETE** `/users/{user_id}`

## 使用说明

1. 使用管理员账户登录获取token
2. 在请求头中添加认证信息：`Authorization: Bearer {token}`
3. 使用管理员权限进行用户管理操作

## 节点监控接口（需要用户认证）

### 获取活跃IP列表
- **GET** `/node-monitor/active-ips`
- 查询参数：
  - `start_time`: 开始时间戳（必需）
  - `end_time`: 结束时间戳（必需）
- 响应：
```json
{
  "active_ips": [
    {
      "ip": "192.168.1.100",
      "latest_ts": 1703001234,
      "cpu_usage_rate": 25.5,
      "disk_usage_rate": 60.2,
      "memory_usage_rate": 45.8,
      "swap_usage_rate": 10.0,
      "network_rate": 1024.5
    }
  ],
  "total_count": 1,
  "time_range": {
    "start_time": 1702914834,
    "end_time": 1703001234
  }
}
```

### 获取特定IP的监控数据
- **GET** `/node-monitor/ip-metrics/{ip}`
- 路径参数：
  - `ip`: IP地址
- 查询参数：
  - `start_time`: 开始时间戳（必需）
  - `end_time`: 结束时间戳（必需）
- 响应：返回该IP在指定时间段内的所有监控记录，按时间升序排列

### 获取监控汇总信息
- **GET** `/node-monitor/summary`
- 查询参数：
  - `start_time`: 开始时间戳（必需）
  - `end_time`: 结束时间戳（必需）
- 响应：
```json
{
  "active_ip_count": 5,
  "total_records": 1250,
  "time_range": {
    "start_time": 1702914834,
    "end_time": 1703001234
  }
}
```

## 五维数据计算说明

### CPU使用率
```
CPU使用率 = cpu_usr + cpu_sys + cpu_iow
```

### 内存使用率
```
内存使用率 = (mem_total - mem_free - mem_buff - mem_cache) / mem_total * 100
```

### 磁盘使用率
```
磁盘使用率 = disk_used_percent
```

### Swap使用率
```
Swap使用率 = swap_used / swap_total * 100
```

### 网络速率
```
网络速率 = net_rx_kbps + net_tx_kbps
```

## 测试脚本

项目包含一个测试脚本 `test_node_monitor_api.py`，用于测试所有节点监控API：

```bash
python test_node_monitor_api.py
```

该脚本会：
1. 测试API健康检查
2. 用户登录获取认证token
3. 测试获取活跃IP列表
4. 测试获取特定IP的详细监控数据
5. 测试获取监控汇总信息

## 数据库表结构

### node_monitor_metrics 表
- `id`: 主键
- `ip`: 节点IP地址
- `ts`: 时间戳
- `cpu_usr`, `cpu_sys`, `cpu_iow`: CPU使用率相关字段
- `mem_total`, `mem_free`, `mem_buff`, `mem_cache`: 内存相关字段
- `swap_total`, `swap_used`: Swap相关字段
- `disk_total`, `disk_used`, `disk_used_percent`: 磁盘相关字段
- `net_rx_kbps`, `net_tx_kbps`: 网络速率字段
- 其他字段...

## 用户类型

- `admin`: 管理员，拥有所有权限
- `user`: 普通用户，可以访问节点监控数据

## 注意事项

1. 所有节点监控API都需要用户认证（Bearer Token）
2. 时间参数使用Unix时间戳
3. 活跃IP查询使用窗口函数确保获取最新数据，避免使用DISTINCT
4. 五维数据在后端计算后返回，前端无需额外计算