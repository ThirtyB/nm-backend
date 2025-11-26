# 用户注册手机号修复说明

## 问题描述

用户自行注册接口中手机号字段没有生效，注册时提交的手机号没有被保存到数据库中。

## 问题原因

1. `UserCreate` schema 中缺少 `phone` 字段定义
2. 注册接口中没有处理手机号的保存逻辑
3. 没有使用手机号加密存储方法

## 修复内容

### 1. 修改 Schema 定义

**文件**: `app/schemas.py`

```python
class UserCreate(BaseModel):
    username: str
    password: str
    phone: Optional[str] = None  # 添加手机号字段
```

### 2. 修改注册接口逻辑

**文件**: `app/routers/auth.py`

#### 新用户注册
```python
# 创建新用户
hashed_password = get_password_hash(user_data.password)
new_user = User(
    username=user_data.username,
    hashed_password=hashed_password,
    user_type="user",  # 强制为普通用户
    is_active=True
)
# 设置加密的手机号
new_user.set_phone_encrypted(user_data.phone)
```

#### 重新激活用户
```python
# 用户存在但已停用，重新激活并更新密码，强制设置为普通用户
existing_user.hashed_password = get_password_hash(user_data.password)
existing_user.is_active = True
existing_user.user_type = "user"  # 强制为普通用户
if user_data.phone is not None:
    existing_user.set_phone_encrypted(user_data.phone)  # 更新加密的手机号
```

### 3. 添加测试文件

**文件**: `test/test_user_registration.py`

创建了完整的测试用例，包括：
- 带手机号的注册测试
- 不带手机号的注册测试  
- 空手机号注册测试
- 重复注册测试

## 手机号加密机制

系统使用 SM4-CBC + HMAC-SHA256 加密算法保护手机号：

- `phone_encrypted`: 加密后的密文
- `phone_iv`: CBC 初始化向量
- `phone_tag`: HMAC 认证标签
- `phone_alg`: 加密算法标识

通过 `User.set_phone_encrypted()` 方法自动处理加密存储，通过 `User.phone_decrypted` 属性自动解密读取。

## 测试方法

1. 启动服务器：
```bash
python start_server.py
```

2. 运行测试：
```bash
python test/test_user_registration.py
```

3. 手动测试 API：
```bash
curl -X POST "http://localhost:8000/auth/register" \
     -H "Content-Type: application/json" \
     -d '{
       "username": "testuser",
       "password": "test123456",
       "phone": "13800138000"
     }'
```

## 验证结果

注册成功后，返回的用户信息中 `phone` 字段应该显示解密后的手机号，数据库中存储的是加密后的密文。

## 注意事项

- 手机号字段为可选，可以为空
- 空字符串会被视为 None，不会存储加密数据
- 加密/解密失败不会影响其他功能的正常运行
- 向后兼容，原有的明文 `phone` 字段保留但不再使用