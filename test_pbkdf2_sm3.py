#!/usr/bin/env python3
"""
测试PBKDF2-HMAC-SM3密码哈希功能
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.auth import get_password_hash, verify_password

def test_password_hashing():
    """测试密码哈希和验证功能"""
    test_passwords = [
        "simple_password",
        "complex_password_123!@#",
        "中文字符密码",
        "very_long_password_that_exceeds_normal_lengths_and_contains_various_characters_1234567890!@#$%^&*()",
        ""
    ]
    
    print("=== PBKDF2-HMAC-SM3 密码哈希测试 ===\n")
    
    for password in test_passwords:
        print(f"测试密码: '{password}'")
        
        # 生成哈希
        hashed = get_password_hash(password)
        print(f"生成的哈希: {hashed}")
        
        # 验证正确密码
        is_valid = verify_password(password, hashed)
        print(f"验证正确密码: {'✓' if is_valid else '✗'}")
        
        # 验证错误密码
        is_invalid = verify_password("wrong_password", hashed)
        print(f"验证错误密码: {'✗' if not is_invalid else '✗'}")
        
        # 测试相同密码生成不同哈希（由于盐的随机性）
        hashed2 = get_password_hash(password)
        hashes_different = hashed != hashed2
        print(f"相同密码生成不同哈希: {'✓' if hashes_different else '✗'}")
        
        # 验证第二个哈希也能验证正确密码
        is_valid2 = verify_password(password, hashed2)
        print(f"第二个哈希验证正确密码: {'✓' if is_valid2 else '✗'}")
        
        print("-" * 60)

def test_backward_compatibility():
    """测试向后兼容性（bcrypt）"""
    print("\n=== 向后兼容性测试 ===\n")
    
    # 模拟旧的bcrypt哈希
    import bcrypt
    old_password = "test_password"
    salt = bcrypt.gensalt()
    bcrypt_hash = bcrypt.hashpw(old_password.encode('utf-8'), salt).decode('utf-8')
    
    print(f"旧bcrypt哈希: {bcrypt_hash}")
    
    # 使用新的验证函数验证旧哈希
    is_valid = verify_password(old_password, bcrypt_hash)
    print(f"新函数验证旧bcrypt哈希: {'✓' if is_valid else '✗'}")
    
    # 验证错误密码
    is_invalid = verify_password("wrong_password", bcrypt_hash)
    print(f"验证错误密码: {'✗' if not is_invalid else '✗'}")

def test_hash_format():
    """测试哈希格式"""
    print("\n=== 哈希格式测试 ===\n")
    
    password = "test_password"
    hashed = get_password_hash(password)
    
    print(f"哈希格式: {hashed}")
    
    # 检查格式
    parts = hashed.split('$')
    if len(parts) == 4 and parts[0] == 'pbkdf2_sm3':
        print("✓ 哈希格式正确")
        print(f"  算法: {parts[0]}")
        print(f"  迭代次数: {parts[1]}")
        print(f"  盐长度: {len(base64.b64decode(parts[2]))} 字节")
        print(f"  哈希长度: {len(base64.b64decode(parts[3]))} 字节")
    else:
        print("✗ 哈希格式错误")

if __name__ == "__main__":
    import base64
    
    try:
        test_password_hashing()
        test_backward_compatibility()
        test_hash_format()
        print("\n=== 所有测试完成 ===")
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()