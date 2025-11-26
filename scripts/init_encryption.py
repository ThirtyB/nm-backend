#!/usr/bin/env python3
"""
加密服务初始化脚本
用于初始化字段加密服务并验证配置
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.security.field_encryption import get_field_encryption_service
from app.security.key_service import get_key_service
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def init_encryption_services():
    """初始化加密服务"""
    logger.info("=== 初始化加密服务 ===")
    
    try:
        # 测试密钥服务
        logger.info("测试密钥服务...")
        key_service = get_key_service()
        
        # 列出可用密钥
        keys = key_service.list_keys()
        logger.info(f"可用密钥: {list(keys.keys())}")
        
        # 获取 SM4 密钥
        try:
            sm4_key = key_service.get_sm4_data_key("v1")
            logger.info(f"✓ 成功获取 SM4 密钥，长度: {len(sm4_key)} 字符")
        except Exception as e:
            logger.error(f"✗ 获取 SM4 密钥失败: {e}")
            logger.error("请确保 secure/secrets.yml 文件存在且包含有效的 SM4 密钥")
            return False
        
        # 测试字段加密服务
        logger.info("测试字段加密服务...")
        encryption_service = get_field_encryption_service()
        
        # 测试加密/解密
        test_phone = "13812345678"
        logger.info(f"测试加密手机号: {test_phone}")
        
        encrypted = encryption_service.encrypt_phone(test_phone)
        if encrypted is None:
            logger.error("✗ 加密失败")
            return False
        
        ciphertext, iv, tag = encrypted
        logger.info(f"✓ 加密成功: 密文长度={len(ciphertext)}, IV长度={len(iv)}, 标签长度={len(tag)}")
        
        decrypted = encryption_service.decrypt_phone(encrypted)
        if decrypted != test_phone:
            logger.error(f"✗ 解密失败: 期望={test_phone}, 实际={decrypted}")
            return False
        
        logger.info(f"✓ 解密成功: {decrypted}")
        
        logger.info("✓ 加密服务初始化成功")
        return True
        
    except Exception as e:
        logger.error(f"✗ 加密服务初始化失败: {e}")
        return False


def check_dependencies():
    """检查依赖"""
    logger.info("=== 检查依赖 ===")
    
    required_modules = [
        'gmssl',
        'sqlalchemy',
        'pydantic',
        'fastapi'
    ]
    
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
            logger.info(f"✓ {module}")
        except ImportError:
            logger.error(f"✗ {module} 未安装")
            missing_modules.append(module)
    
    if missing_modules:
        logger.error(f"缺少依赖: {', '.join(missing_modules)}")
        logger.error("请运行: pip install -r requirements.txt")
        return False
    
    logger.info("✓ 所有依赖检查通过")
    return True


def check_config_files():
    """检查配置文件"""
    logger.info("=== 检查配置文件 ===")
    
    config_files = [
        "secure/secrets.yml",
        "app/config.py",
        "app/database.py"
    ]
    
    missing_files = []
    
    for file_path in config_files:
        full_path = project_root / file_path
        if full_path.exists():
            logger.info(f"✓ {file_path}")
        else:
            logger.error(f"✗ {file_path} 不存在")
            missing_files.append(file_path)
    
    if missing_files:
        logger.error(f"缺少配置文件: {', '.join(missing_files)}")
        return False
    
    logger.info("✓ 所有配置文件检查通过")
    return True


def main():
    """主函数"""
    logger.info("开始初始化手机号加密功能")
    
    checks = [
        ("依赖检查", check_dependencies),
        ("配置文件检查", check_config_files),
        ("加密服务初始化", init_encryption_services)
    ]
    
    passed = 0
    total = len(checks)
    
    for check_name, check_func in checks:
        logger.info(f"\n--- {check_name} ---")
        try:
            if check_func():
                passed += 1
                logger.info(f"✓ {check_name} 通过")
            else:
                logger.error(f"✗ {check_name} 失败")
        except Exception as e:
            logger.error(f"✗ {check_name} 异常: {e}")
    
    logger.info(f"\n=== 初始化结果 ===")
    logger.info(f"通过: {passed}/{total}")
    logger.info(f"成功率: {passed/total*100:.1f}%")
    
    if passed == total:
        logger.info("🎉 初始化成功！手机号加密功能已准备就绪")
        logger.info("\n下一步:")
        logger.info("1. 更新数据库: psql -d your_database -f schema.sql")
        logger.info("2. 迁移现有数据: python migrate_phone_encryption.py --all")
        logger.info("3. 运行测试: python test_phone_encryption.py")
        return True
    else:
        logger.error("❌ 初始化失败，请检查上述错误")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)