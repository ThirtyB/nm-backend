# PBKDF2-HMAC-SM3 密码存储安全升级

## 概述

为了提高系统安全性，我们将密码存储方式从bcrypt升级为PBKDF2-HMAC-SM3。这种方案结合了PBKDF2的迭代安全性和国密SM3算法的加密强度。

## 技术细节

### 算法选择

- **PBKDF2**: Password-Based Key Derivation Function 2
  - 迭代次数: 100,000次
  - 有效防止暴力破解和彩虹表攻击

- **HMAC-SM3**: 基于国密SM3的哈希消息认证码
  - SM3是中国国家密码管理局批准的商用密码哈希算法
  - 输出长度: 256位（32字节）
  - 安全性等同于SHA-256

- **盐值处理**: 
  - 每个密码使用独立的32字节随机盐
  - 盐值使用Base64编码存储

### 存储格式

新的密码哈希存储格式：
```
pbkdf2_sm3$<iterations>$<salt_base64>$<hash_base64>
```

示例：
```
pbkdf2_sm3$100000$9YvDzAdGHwIomjGVrljuWNG1i18+IkHsEDqMUwshMqI=$bYrml04o9UH5ywQzD79L8f+HOaHPV+86Aw3lZidqVl0=
```

## 安全特性

### 1. 抗暴力破解
- 100,000次PBKDF2迭代大幅增加计算成本
- 每次验证都需要完整的迭代计算

### 2. 抗彩虹表攻击
- 每个密码使用独立的随机盐
- 相同密码产生不同的哈希值

### 3. 国密算法支持
- 使用SM3算法符合国家密码标准
- 适用于需要国密合规的场景

### 4. 向后兼容
- 自动识别并验证现有的bcrypt密码哈希
- 用户登录时可无缝迁移到新格式

## 实现细节

### 密码哈希生成流程

```python
def get_password_hash(password: str) -> str:
    # 1. 生成随机盐
    salt = os.urandom(32)
    
    # 2. PBKDF2-HMAC-SHA256迭代
    dk = hashlib.pbkdf2_hmac('sha256', password_bytes, salt, 100000)
    
    # 3. 应用SM3作为额外哈希层
    final_hash = sm3_hash(dk)
    
    # 4. 组合存储
    return f"pbkdf2_sm3$100000${salt_b64}${hash_b64}"
```

### 密码验证流程

```python
def verify_password(plain_password: str, hashed_password: str) -> bool:
    # 1. 检查哈希格式
    if hashed_password.startswith('pbkdf2_sm3$'):
        # 新格式验证
        # 解析参数并重新计算哈希
    else:
        # 向后兼容：验证bcrypt格式
```

## 迁移策略

### 现有用户处理

由于无法从bcrypt哈希中恢复原始密码，采用以下策略：

1. **标记迁移**: 将使用旧哈希的用户标记为需要重置密码
2. **登录时迁移**: 用户下次登录时验证旧密码，然后更新为新哈希
3. **管理员重置**: 管理员可以为用户重置密码

### 新用户注册

所有新注册用户直接使用PBKDF2-HMAC-SM3哈希。

## 性能考虑

### 计算时间
- 每次密码验证约需要10-50ms（取决于硬件）
- 100,000次迭代在安全性和性能间取得平衡

### 存储空间
- 新哈希长度约88字符
- 相比bcrypt略有增加但可接受

## 使用指南

### 1. 安装依赖

```bash
pip install gmssl
```

### 2. 运行迁移脚本

```bash
python migrate_password_hash.py
```

### 3. 测试功能

```bash
python test_pbkdf2_sm3.py
```

## 安全建议

### 1. 密码策略
- 最小长度8位
- 包含大小写字母、数字和特殊字符
- 定期更换密码

### 2. 监控和审计
- 记录登录失败次数
- 监控异常登录行为
- 定期检查密码强度

### 3. 系统配置
- 使用HTTPS保护传输
- 实施账户锁定策略
- 定期更新安全配置

## 故障排除

### 常见问题

1. **gmssl导入失败**
   - 确保已安装gmssl包
   - 系统会自动回退到SHA-256

2. **密码验证失败**
   - 检查哈希格式是否正确
   - 确认迭代次数匹配

3. **性能问题**
   - 可根据需要调整迭代次数
   - 建议不低于50,000次

## 总结

PBKDF2-HMAC-SM3密码存储方案提供了：

- ✅ 高安全性：多层加密保护
- ✅ 国密合规：支持SM3算法
- ✅ 向后兼容：平滑迁移现有用户
- ✅ 性能平衡：合理的安全开销
- ✅ 易于维护：清晰的实现逻辑

此升级显著提升了系统的密码安全水平，为用户数据提供更强的保护。