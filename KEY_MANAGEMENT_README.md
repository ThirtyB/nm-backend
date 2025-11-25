# 密钥管理模块 (KeyService)

## 概述

轻量级密钥管理模块，提供统一的密钥管理接口，支持 SM2 和 SM4 密钥的集中管理。

## 功能特性

- ✅ 统一密钥管理接口
- ✅ 支持配置文件和环境变量两种密钥来源
- ✅ 环境变量优先级高于配置文件
- ✅ 密钥版本管理（支持 v1, v2, v3 等）
- ✅ 单例模式的全局密钥服务
- ✅ 密钥生成工具
- ✅ 完整的测试覆盖

## 支持的密钥类型

### SM2 密钥对
- `sm2_token_key_v1_priv`: SM2 私钥，用于 token 签名
- `sm2_token_key_v1_pub`: SM2 公钥，用于 token 验签

### SM4 密钥
- `sm4_data_key_v1`: SM4 对称密钥，用于字段加密 (128-bit)

## 快速开始

### 1. 生成密钥

```bash
# 生成密钥并创建配置文件（所有操作都在 secure/ 目录中进行）
python secure/key_generator.py

# 指定输出文件名（相对于 secure 目录）和版本
python secure/key_generator.py --output secrets.yml --version v1

# 强制覆盖已存在的配置文件
python secure/key_generator.py --force

# 查看帮助信息
python secure/key_generator.py --help
```

### 🔒 安全特性
- **目录隔离**：所有密钥操作都在 `secure/` 目录中进行
- **路径验证**：脚本自动验证运行目录，确保安全性
- **文件权限**：生成的密钥文件权限自动设为 600

### 2. 配置密钥

#### 方式一：配置文件（推荐）
密钥文件将自动生成到 `secure/secrets.yml`：
```yaml
# secure/secrets.yml
keys:
  sm2_token_key_v1_priv:
    description: "SM2 私钥，用于 token 签名"
    value: "your_private_key_here"
    type: "sm2_private"
  sm2_token_key_v1_pub:
    description: "SM2 公钥，用于 token 验签"
    value: "your_public_key_here"
    type: "sm2_public"
  sm4_data_key_v1:
    description: "SM4 对称密钥，用于字段加密"
    value: "your_sm4_key_here"
    type: "sm4"
```

#### 方式二：环境变量
```bash
export SM2_TOKEN_KEY_V1_PRIV="your_private_key_here"
export SM2_TOKEN_KEY_V1_PUB="your_public_key_here"
export SM4_DATA_KEY_V1="your_sm4_key_here"
```

### 3. 在代码中使用

```python
from app.security.key_service import get_key_service

# 获取全局密钥服务实例
key_service = get_key_service()

# 获取 SM2 密钥
private_key = key_service.get_sm2_token_private_key()
public_key = key_service.get_sm2_token_public_key()

# 获取 SM4 密钥
sm4_key = key_service.get_sm4_data_key()

# 指定版本获取密钥
v1_priv = key_service.get_sm2_token_private_key("v1")
v2_key = key_service.get_sm4_data_key("v2")  # 如果存在的话
```

## API 参考

### KeyService 类

#### 初始化
```python
# 使用默认配置文件路径
key_service = KeyService()

# 指定配置文件路径
key_service = KeyService("/path/to/secrets.yml")
```

#### 主要方法

| 方法 | 描述 | 参数 | 返回值 |
|------|------|------|--------|
| `get_sm2_token_private_key(version="v1")` | 获取 SM2 私钥 | version: 密钥版本 | str |
| `get_sm2_token_public_key(version="v1")` | 获取 SM2 公钥 | version: 密钥版本 | str |
| `get_sm4_data_key(version="v1")` | 获取 SM4 密钥 | version: 密钥版本 | str |
| `list_keys()` | 列出密钥信息 | 无 | Dict |
| `reload()` | 重新加载密钥 | 无 | None |

### 全局函数

| 函数 | 描述 |
|------|------|
| `get_key_service()` | 获取全局单例实例 |
| `init_key_service(config_file=None)` | 初始化全局实例 |

## 密钥版本管理

### 版本命名规则
- 格式：`{algorithm}_{purpose}_key_{version}_{type}`
- 示例：
  - `sm2_token_key_v1_priv` (v1 版本 SM2 token 私钥)
  - `sm2_token_key_v2_pub` (v2 版本 SM2 token 公钥)
  - `sm4_data_key_v1` (v1 版本 SM4 数据密钥)

### 密钥轮换
1. 生成新版本密钥：
   ```bash
   python app/security/key_generator.py --version v2 --output secrets_v2.yml
   ```

2. 更新配置文件，添加新版本密钥

3. 代码中逐步切换到新版本：
   ```python
   # 旧版本
   old_key = key_service.get_sm4_data_key("v1")
   
   # 新版本
   new_key = key_service.get_sm4_data_key("v2")
   ```

## 安全注意事项

### 🔒 文件权限
- 配置文件权限应设置为 `600`（仅所有者可读写）
- 密钥生成工具会自动设置正确的文件权限

### 🚫 版本控制
- `secure/secrets.yml` 已添加到 `.gitignore`
- 绝对不要将真实密钥提交到版本控制系统
- 只提交 `secure/secrets.example.yml` 作为模板
- `secure/` 目录通过 `.gitkeep` 保持被 git 跟踪

### 🌐 环境变量
- 生产环境推荐使用环境变量
- 容器化部署时通过 secrets management 系统注入
- CI/CD 环境使用安全的密钥管理服务

## 测试

### 运行测试
```bash
# 运行密钥服务测试
python test_key_service.py

# 运行使用示例
python app/security/example_usage.py
```

### 测试覆盖
- ✅ 配置文件加载
- ✅ 环境变量优先级
- ✅ 密钥获取和验证
- ✅ 版本管理
- ✅ 全局单例模式
- ✅ 错误处理

## 故障排除

### 常见问题

#### 1. 密钥不存在错误
```
KeyError: 密钥不存在: sm2_token_key_v1_priv
```
**解决方案：**
- 运行密钥生成工具创建密钥
- 检查配置文件路径是否正确
- 确认环境变量是否设置

#### 2. 配置文件读取失败
```
密钥配置文件不存在: /path/to/secure/secrets.yml
```
**解决方案：**
- 运行 `python app/security/key_generator.py` 生成密钥文件
- 确认文件在 `secure/` 目录中
- 或指定正确的配置文件路径
- 检查文件权限

#### 3. 环境变量不生效
**可能原因：**
- 环境变量名称拼写错误
- 环境变量未正确导出
- 程序启动时环境变量未设置

## 集成到现有项目

### 1. 在 FastAPI 应用中初始化
```python
# main.py
from app.security.key_service import init_key_service

# 应用启动时初始化密钥服务
app = FastAPI()

@app.on_event("startup")
async def startup_event():
    init_key_service()
```

### 2. 在路由中使用
```python
# routers/auth.py
from app.security.key_service import get_key_service

@router.post("/sign-token")
async def sign_token(data: TokenData):
    key_service = get_key_service()
    private_key = key_service.get_sm2_token_private_key()
    # 使用私钥签名 token
```

## 下一步计划

- [ ] 支持更多密钥算法（AES、RSA 等）
- [ ] 密钥轮换自动化
- [ ] 密钥使用审计日志
- [ ] 集成外部密钥管理服务（如 HashiCorp Vault）
- [ ] 密钥过期和自动更新机制

## 贡献

欢迎提交 Issue 和 Pull Request 来改进密钥管理模块。