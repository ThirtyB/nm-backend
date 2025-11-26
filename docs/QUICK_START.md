# 快速启动指南

## 🚀 快速开始

### 1. 环境准备
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置数据库
确保 `.env` 文件配置正确：
```env
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
DATABASE_URL=postgresql://username:password@localhost:5432/dbname
```

### 3. 初始化数据库
```bash
# 初始化用户表和创建管理员
python init_db.py

# 初始化节点监控表
python init_node_monitor_tables.py
```

### 4. 启动服务
```bash
# 方式1：使用启动脚本
python start_server.py

# 方式2：直接使用uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. 测试API
```bash
# 运行测试脚本
python test_node_monitor_api.py
```

## 📚 API访问

- **API文档**: http://localhost:8000/docs
- **ReDoc文档**: http://localhost:8000/redoc
- **健康检查**: http://localhost:8000/health

## 🔑 默认账户

- **用户名**: admin
- **密码**: admin123

## 📊 主要功能

### 1. 获取活跃IP列表
```bash
GET /node-monitor/active-ips?start_time=1702914834&end_time=1703001234
```

### 2. 获取特定IP监控数据
```bash
GET /node-monitor/ip-metrics/192.168.1.100?start_time=1702914834&end_time=1703001234
```

### 3. 获取监控汇总
```bash
GET /node-monitor/summary?start_time=1702914834&end_time=1703001234
```

## ⚠️ 注意事项

1. 所有API都需要Bearer Token认证
2. 时间参数使用Unix时间戳
3. 确保数据库连接正常
4. 检查防火墙设置

## 🛠️ 故障排除

### 服务无法启动
- 检查端口是否被占用
- 检查数据库连接配置
- 查看错误日志

### API返回401错误
- 检查是否已登录获取token
- 检查请求头是否包含正确的Authorization

### 数据库连接失败
- 检查数据库服务是否运行
- 检查连接字符串是否正确
- 检查网络连接

## 📞 支持

如有问题，请检查：
1. README.md 详细文档
2. API文档 /docs
3. 测试脚本 test_node_monitor_api.py