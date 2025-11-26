#!/usr/bin/env python3
"""
手机号加密功能测试脚本
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.security.field_encryption import get_field_encryption_service
from app.models import User
from app.database import get_db
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_field_encryption_service():
    """测试字段加密服务"""
    logger.info("=== 测试字段加密服务 ===")
    
    try:
        # 获取加密服务
        encryption_service = get_field_encryption_service()
        logger.info("✓ 成功获取字段加密服务")
        
        # 测试用例
        test_cases = [
            "13812345678",
            "15900001111",
            "18622223333",
            "",  # 空字符串
            None  # None值
        ]
        
        for phone in test_cases:
            logger.info(f"测试手机号: {phone}")
            
            # 加密
            try:
                encrypted = encryption_service.encrypt_phone(phone)
                if phone is None or phone.strip() == "":
                    assert encrypted is None, f"空手机号应该返回 None，但得到: {encrypted}"
                    logger.info(f"  ✓ 空手机号加密测试通过")
                else:
                    assert encrypted is not None, f"非空手机号不应该返回 None"
                    ciphertext, iv, tag = encrypted
                    logger.info(f"  ✓ 加密成功: 密文长度={len(ciphertext)}, IV长度={len(iv)}, 标签长度={len(tag)}")
                    
                    # 解密
                    decrypted = encryption_service.decrypt_phone(encrypted)
                    assert decrypted == phone, f"解密结果不匹配: 期望={phone}, 实际={decrypted}"
                    logger.info(f"  ✓ 解密成功: {decrypted}")
                    
                    # 测试十六进制格式
                    encrypted_hex = encryption_service.encrypt_phone_to_hex(phone)
                    decrypted_hex = encryption_service.decrypt_phone_from_hex(encrypted_hex)
                    assert decrypted_hex == phone, f"十六进制解密结果不匹配: 期望={phone}, 实际={decrypted_hex}"
                    logger.info(f"  ✓ 十六进制格式测试通过")
                    
            except Exception as e:
                logger.error(f"  ✗ 测试失败: {e}")
                return False
        
        logger.info("✓ 字段加密服务测试全部通过")
        return True
        
    except Exception as e:
        logger.error(f"✗ 字段加密服务测试失败: {e}")
        return False


def test_user_model_encryption():
    """测试用户模型的加密功能"""
    logger.info("=== 测试用户模型加密功能 ===")
    
    try:
        # 创建测试用户实例（不保存到数据库）
        user = User(
            username="test_user",
            hashed_password="test_password",
            user_type="user",
            is_active=True
        )
        
        # 测试手机号加密
        test_phones = [
            "13812345678",
            "15900001111",
            "",  # 空字符串
            None  # None值
        ]
        
        for phone in test_phones:
            logger.info(f"测试手机号: {phone}")
            
            # 设置加密手机号
            user.set_phone_encrypted(phone)
            
            if phone is None or phone.strip() == "":
                assert user.phone_encrypted is None, f"空手机号加密字段应该为 None"
                assert user.phone_iv is None, f"空手机号 IV 字段应该为 None"
                assert user.phone_tag is None, f"空手机号标签字段应该为 None"
                logger.info(f"  ✓ 空手机号处理正确")
            else:
                assert user.phone_encrypted is not None, f"非空手机号加密字段不应该为 None"
                assert user.phone_iv is not None, f"非空手机号 IV 字段不应该为 None"
                assert user.phone_tag is not None, f"非空手机号标签字段不应该为 None"
                logger.info(f"  ✓ 加密字段设置成功")
                
                # 测试解密
                decrypted = user.phone_decrypted
                assert decrypted == phone, f"解密结果不匹配: 期望={phone}, 实际={decrypted}"
                logger.info(f"  ✓ 解密成功: {decrypted}")
        
        logger.info("✓ 用户模型加密功能测试全部通过")
        return True
        
    except Exception as e:
        logger.error(f"✗ 用户模型加密功能测试失败: {e}")
        return False


def test_database_operations():
    """测试数据库操作"""
    logger.info("=== 测试数据库操作 ===")
    
    try:
        # 获取数据库会话
        db = next(get_db())
        
        # 查询现有用户
        users = db.query(User).limit(3).all()
        logger.info(f"找到 {len(users)} 个用户进行测试")
        
        for user in users:
            logger.info(f"测试用户: {user.username}")
            
            # 获取当前手机号（可能是加密的）
            current_phone = user.phone_decrypted
            logger.info(f"  当前手机号: {current_phone}")
            
            # 测试设置新的加密手机号
            test_phone = "13888888888"
            user.set_phone_encrypted(test_phone)
            db.commit()
            
            # 验证加密后的手机号
            decrypted = user.phone_decrypted
            assert decrypted == test_phone, f"数据库加密测试失败: 期望={test_phone}, 实际={decrypted}"
            logger.info(f"  ✓ 数据库加密测试成功: {decrypted}")
            
            # 恢复原来的手机号
            user.set_phone_encrypted(current_phone)
            db.commit()
        
        db.close()
        logger.info("✓ 数据库操作测试全部通过")
        return True
        
    except Exception as e:
        logger.error(f"✗ 数据库操作测试失败: {e}")
        return False


def main():
    """主函数"""
    logger.info("开始手机号加密功能测试")
    
    tests = [
        ("字段加密服务", test_field_encryption_service),
        ("用户模型加密功能", test_user_model_encryption),
        ("数据库操作", test_database_operations)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n--- {test_name} ---")
        try:
            if test_func():
                passed += 1
                logger.info(f"✓ {test_name} 测试通过")
            else:
                logger.error(f"✗ {test_name} 测试失败")
        except Exception as e:
            logger.error(f"✗ {test_name} 测试异常: {e}")
    
    logger.info(f"\n=== 测试结果 ===")
    logger.info(f"通过: {passed}/{total}")
    logger.info(f"成功率: {passed/total*100:.1f}%")
    
    if passed == total:
        logger.info("🎉 所有测试通过！")
        return True
    else:
        logger.error("❌ 部分测试失败")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)