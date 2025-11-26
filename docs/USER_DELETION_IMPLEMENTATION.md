# 用户删除功能实现说明

## 业务逻辑变更

### 原有逻辑
- 用户不会被删除，只能设置为不活跃（`is_active = False`）
- 不活跃用户可以重新激活使用

### 新逻辑
- 用户可以被设置为禁用（`is_active = False`）
- 用户可以被直接删除（从数据库中完全移除）
- 禁用用户不允许注册和登录

## 实现的功能

### 1. 用户删除接口

**接口**: `DELETE /users/{user_id}`
- **权限**: 仅管理员
- **功能**: 从数据库中完全删除用户记录
- **限制**: 不能删除自己

```python
@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """删除用户"""
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    if db_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )
    
    # 删除用户
    db.delete(db_user)
    db.commit()
    
    return {"message": "User deleted successfully"}
```

### 2. 禁用用户限制

#### 注册限制
- **用户名限制**: 如果用户名被禁用用户占用，不允许注册
- **手机号限制**: 如果手机号被禁用用户占用，不允许注册

**错误信息**:
- 用户名被占用: `"Username is disabled and cannot be registered"`
- 手机号被占用: `"Phone number is disabled and cannot be registered"`

#### 登录限制
- **用户名登录**: 禁用用户无法使用用户名登录
- **手机号登录**: 禁用用户无法使用手机号登录

**错误信息**: `"Account is disabled"`

## 修改的接口

### 1. 用户注册 (`POST /auth/register`)

**修改内容**:
- 移除了重新激活禁用用户的逻辑
- 添加了用户名和手机号的禁用检查

```python
# 检查用户名是否已存在
existing_user = db.query(User).filter(User.username == user_data.username).first()
if existing_user:
    if existing_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    else:
        # 用户名被禁用用户占用，不允许注册
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is disabled and cannot be registered"
        )

# 检查手机号唯一性和是否被禁用用户使用
if user_data.phone is not None and user_data.phone.strip() != "":
    phone_user = find_user_by_phone(db, user_data.phone)
    if phone_user:
        if phone_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )
        else:
            # 手机号被禁用用户占用，不允许注册
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number is disabled and cannot be registered"
            )
```

### 2. 用户登录 (`POST /auth/login`)

**修改内容**:
- 区分用户不存在和账户禁用的错误信息
- 支持用户名和手机号的禁用检查

```python
if not user:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

if not user.is_active:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Account is disabled",
        headers={"WWW-Authenticate": "Bearer"},
    )
```

### 3. 管理员创建用户 (`POST /users/`)

**修改内容**:
- 移除了重新激活禁用用户的逻辑
- 添加了用户名和手机号的禁用检查

### 4. 用户管理接口

**现有接口保持不变**:
- `POST /users/{user_id}/deactivate`: 禁用用户
- `POST /users/{user_id}/activate`: 激活用户
- `GET /users/`: 获取用户列表（支持包含禁用用户）

## API使用示例

### 删除用户
```bash
curl -X DELETE "http://localhost:8000/users/123" \
     -H "Authorization: Bearer <admin_token>"
```

**成功响应**:
```json
{
  "message": "User deleted successfully"
}
```

**错误响应**:
```json
{
  "detail": "Cannot delete yourself"
}
```

### 禁用用户登录测试
```bash
# 使用禁用用户登录
curl -X POST "http://localhost:8000/auth/login" \
     -H "Content-Type: application/json" \
     -d '{
       "username": "disabled_user",
       "password": "password123"
     }'
```

**错误响应**:
```json
{
  "detail": "Account is disabled"
}
```

### 使用禁用用户名注册
```bash
curl -X POST "http://localhost:8000/auth/register" \
     -H "Content-Type: application/json" \
     -d '{
       "username": "disabled_user",
       "password": "newpassword123",
       "phone": "13800138000"
     }'
```

**错误响应**:
```json
{
  "detail": "Username is disabled and cannot be registered"
}
```

## 测试用例

**文件**: `test/test_user_deletion.py`

### 测试场景

1. **用户删除功能测试**
   - 创建用户
   - 验证用户存在
   - 删除用户
   - 验证用户已删除

2. **禁用用户限制测试**
   - 创建并禁用用户
   - 测试用户名登录（失败）
   - 测试手机号登录（失败）
   - 测试使用禁用用户名注册（失败）
   - 测试使用禁用手机号注册（失败）
   - 重新激活用户
   - 测试重新激活后登录（成功）

3. **防止自删除测试**
   - 获取当前用户ID
   - 尝试删除自己（失败）

## 安全考虑

### 1. 错误信息区分
- **用户不存在**: `"Incorrect username or password"`
- **账户禁用**: `"Account is disabled"`
- **用户名/手机号被禁用占用**: 明确的错误信息

### 2. 权限控制
- 只有管理员可以删除用户
- 用户不能删除自己
- 禁用用户无法进行任何操作

### 3. 数据完整性
- 删除操作是物理删除，数据无法恢复
- 建议在删除前进行确认或备份

## 兼容性说明

### 向后兼容
- 现有的禁用/激活接口保持不变
- 用户列表查询接口保持不变
- 现有用户的登录和注册行为保持不变

### 数据库兼容
- 不需要修改数据库结构
- 使用现有的 `is_active` 字段
- 删除操作使用标准的 SQLAlchemy 删除方法

## 监控和日志

### 建议监控指标
- 用户删除次数
- 禁用用户登录尝试次数
- 禁用用户名/手机号注册尝试次数

### 建议日志记录
- 用户删除操作（操作者、被删除用户、时间）
- 禁用用户登录尝试（用户名、IP、时间）
- 禁用资源注册尝试（用户名/手机号、IP、时间）

## 注意事项

1. **数据恢复**: 物理删除无法恢复，建议谨慎操作
2. **关联数据**: 删除用户前需要考虑关联数据的处理
3. **权限管理**: 确保只有授权的管理员可以删除用户
4. **用户体验**: 提供清晰的错误信息帮助用户理解问题

## 后续优化建议

1. **软删除**: 考虑实现软删除功能，标记删除时间而非物理删除
2. **批量操作**: 支持批量禁用/删除用户
3. **删除确认**: 添加删除确认机制，防止误操作
4. **审计日志**: 记录所有用户状态变更的详细日志