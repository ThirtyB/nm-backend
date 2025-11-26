# 手机号字段级 SM4-CBC + HMAC 加密实现

## 概述

本系统实现了用户表手机号字段的 SM4-CBC + HMAC-SHA256 字段级加密，确保敏感数据在数据库中的安全存储。

## 技术实现

### 1. 数据库 Schema

在 `schema.sql` 中，用户表增加了以下加密字段：

```sql
-- SM4-CBC + HMAC 加密字段
phone_encrypted BYTEA,  -- 加密后的手机号密文
phone_iv BYTEA,         -- CBC 初始化向量 (16字节)
phone_tag BYTEA,        -- HMAC-SHA256 认证标签 (32字节)
phone_alg VARCHAR(20) DEFAULT 'SM4-CBC-HMAC',  -- 加密算法标识
```

原 `phone` 字段保留用于向后兼容，但建议设置为 NULL。

### 2. 字段加密服务

`app/security/field_encryption.py` 提供了集中式的字段加密服务：

- **FieldEncryptionService**: 核心加密服务类
- **SM4-CBC + HMAC 加密**: 使用国密 SM4 算法的 CBC 模式 + HMAC-SHA256 认证
- **密钥管理**: 集成现有的 KeyService 获取 SM4 密钥
- **数据完整性**: HMAC-SHA256 提供认证和完整性保护

#### 主要方法：

```python
# 加密手机号
encrypt_phone(phone: Optional[str]) -> Optional[Tuple[bytes, bytes, bytes]]

# 解密手机号
decrypt_phone(encrypted_data: Optional[Tuple[bytes, bytes, bytes]]) -> Optional[str]

# 十六进制格式加密（便于数据库存储）
encrypt_phone_to_hex(phone: Optional[str]) -> Optional[Tuple[str, str, str]]

# 从十六进制格式解密
decrypt_phone_from_hex(encrypted_hex: Optional[Tuple[str, str, str]]) -> Optional[str]
```

### 3. 数据模型改造

`app/models.py` 中的 User 模型增加了加密支持：

```python
class User(Base):
    # 加密字段
    phone_encrypted = Column(LargeBinary)  # 密文
    phone_iv = Column(LargeBinary)         # IV
    phone_tag = Column(LargeBinary)        # 认证标签
    phone_alg = Column(String(20), default='SM4-GCM')
    
    # 解密属性
    @property
    def phone_decrypted(self) -> Optional[str]:
        """获取解密后的手机号"""
    
    # 加密设置方法
    def set_phone_encrypted(self, phone: Optional[str]) -> None:
        """设置加密的手机号"""
```

### 4. API 层改造

所有用户相关的 API 都已更新以支持加密字段：

- **用户创建**: 创建用户时自动加密手机号
- **用户更新**: 更新手机号时自动加密
- **用户查询**: 返回时自动解密手机号
- **个人资料**: 用户自己管理手机号时自动加密

#### 受影响的文件：
- `app/routers/users.py`: 管理员用户管理
- `app/routers/user_profile.py`: 用户个人资料管理
- `app/schemas.py`: 响应模型自动处理解密

### 5. 数据迁移

`migrate_phone_encryption.py` 提供了现有数据的迁移功能：

```bash
# 执行迁移
python migrate_phone_encryption.py --migrate

# 验证迁移结果
python migrate_phone_encryption.py --verify

# 执行迁移和验证
python migrate_phone_encryption.py --all
```

## 安全特性

### 1. 加密强度
- **加密算法**: SM4-CBC（国密标准）
- **认证算法**: HMAC-SHA256
- **密钥长度**: 128 位（SM4）
- **IV 长度**: 128 位（16 字节）
- **HMAC 标签**: 256 位（32 字节）

### 2. 密钥管理
- 使用现有的 KeyService 统一管理密钥
- 密钥存储在 `secure/secrets.yml` 文件中
- 支持环境变量覆盖配置文件

### 3. 数据完整性
- GCM 模式提供认证和完整性保护
- 每次加密使用随机 IV
- 认证标签防止数据篡改

### 4. 向后兼容
- 保留原 `phone` 字段
- 现有数据可逐步迁移
- API 接口保持不变

## 使用指南

### 1. 初始化

确保已配置 SM4 密钥：

```bash
# 生成密钥（如果还没有）
cd secure
python key_generator.py --output secrets.yml
```

### 2. 数据库更新

执行新的 schema：

```sql
-- 在数据库中执行
psql -d your_database -f schema.sql
```

### 3. 数据迁移

迁移现有数据：

```bash
python migrate_phone_encryption.py --all
```

### 4. 测试验证

运行测试脚本：

```bash
python test_phone_encryption.py
```

## 注意事项

### 1. 性能考虑
- 加密/解密操作会增加 CPU 开销
- 无法对加密字段建立索引进行查询
- 建议在应用层缓存常用数据

### 2. 查询限制
- 无法直接查询加密字段的内容
- 手机号唯一性检查需要特殊处理
- 模糊查询不可用

### 3. 备份恢复
- 备份时需要同时备份密钥文件
- 密钥丢失将无法恢复数据
- 建议定期备份密钥文件

### 4. 监控日志
- 加密/解密失败会记录错误日志
- 建议监控加密服务的运行状态
- 定期检查数据完整性

## 扩展性

### 1. 支持其他字段
当前的加密服务可以轻松扩展到其他敏感字段：

```python
# 示例：加密邮箱字段
email_encrypted = encryption_service.encrypt_field(email)
```

### 2. 支持其他算法
可以扩展支持其他加密算法：

```python
# 示例：支持 AES-GCM
class AESFieldEncryptionService(FieldEncryptionService):
    def encrypt_field(self, data: str) -> bytes:
        # AES-GCM 加密实现
        pass
```

### 3. 密钥轮换
可以支持密钥版本管理和轮换：

```python
# 示例：使用不同版本的密钥
old_key = key_service.get_sm4_data_key("v1")
new_key = key_service.get_sm4_data_key("v2")
```

## 故障排除

### 1. 常见问题

**问题**: 加密失败
- 检查密钥文件是否存在
- 验证密钥格式是否正确
- 确认 gmssl 库已安装

**问题**: 解密失败
- 检查数据完整性（IV、标签是否存在）
- 验证密钥版本是否匹配
- 确认数据未被篡改

**问题**: 性能问题
- 考虑批量操作时减少加密次数
- 使用连接池优化数据库连接
- 监控 CPU 使用率

### 2. 调试方法

启用调试日志：

```python
import logging
logging.getLogger('app.security.field_encryption').setLevel(logging.DEBUG)
```

## 总结

本实现提供了完整的字段级加密解决方案，具有以下优势：

1. **安全性高**: 使用国密 SM4-GCM 算法
2. **集成度好**: 与现有系统无缝集成
3. **易用性强**: API 接口保持不变
4. **扩展性好**: 支持其他字段和算法
5. **维护方便**: 提供完整的测试和迁移工具

通过这个实现，系统的数据安全性得到了显著提升，同时保持了良好的开发体验。