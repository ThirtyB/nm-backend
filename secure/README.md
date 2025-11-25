# 安全文件夹 (Secure Directory)

## 概述

此文件夹包含所有与安全相关的配置文件和密钥文件。

## 文件说明

### 配置文件
- `secrets.yml` - 密钥配置文件（包含真实的密钥信息）
- `secrets.example.yml` - 密钥配置文件模板（不包含真实密钥）

### 安全注意事项

🔒 **重要提醒**：
- 此文件夹中的 `secrets.yml` 包含真实的密钥信息
- 绝对不要将真实的密钥文件提交到版本控制系统
- 文件夹已配置在 `.gitignore` 中，`secrets.yml` 不会被提交
- 请确保此文件夹的访问权限设置正确

## 使用方法

### 1. 生成密钥配置文件
```bash
# 在项目根目录运行（所有操作都在 secure/ 目录中进行）
python secure/key_generator.py

# 指定输出文件名（相对于 secure 目录，默认为 secrets.yml）
python secure/key_generator.py --output secrets.yml

# 指定版本和强制覆盖
python secure/key_generator.py --version v2 --force

# 查看帮助
python secure/key_generator.py --help
```

### 🔒 安全特性
- **目录隔离**：所有密钥操作都在 `secure/` 目录中进行
- **路径验证**：脚本自动验证运行目录，确保安全性
- **文件权限**：生成的密钥文件权限自动设为 600
- **版本控制安全**：密钥文件已配置在 `.gitignore` 中

### 2. 使用环境变量（推荐用于生产环境）
```bash
export SM2_TOKEN_KEY_V1_PRIV="your_private_key_here"
export SM2_TOKEN_KEY_V1_PUB="your_public_key_here"
export SM4_DATA_KEY_V1="your_sm4_key_here"
```

### 3. 文件权限设置
```bash
# 设置 secure 目录权限（仅所有者可访问）
chmod 700 secure/

# 设置密钥文件权限（仅所有者可读写）
chmod 600 secure/secrets.yml
```

## 密钥轮换

当需要轮换密钥时：

1. 备份当前密钥文件
2. 生成新版本密钥
3. 更新配置文件
4. 重启应用服务

## 故障排除

如果密钥加载失败，请检查：
1. `secure/secrets.yml` 文件是否存在
2. 文件权限是否正确（600）
3. 文件格式是否正确（YAML 语法）
4. 环境变量是否设置正确（如果使用环境变量）

## 联系支持

如有安全相关问题，请联系系统管理员。