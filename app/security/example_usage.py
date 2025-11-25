"""
密钥服务使用示例
展示如何在项目中集成和使用 KeyService
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.security.key_service import get_key_service, init_key_service


def example_token_signing():
    """示例：使用 SM2 密钥进行 token 签名"""
    key_service = get_key_service()
    
    try:
        # 获取 SM2 私钥用于签名
        private_key = key_service.get_sm2_token_private_key()
        print(f"获取到 SM2 私钥用于签名: {private_key[:8]}...")
        
        # 获取 SM2 公钥用于验签
        public_key = key_service.get_sm2_token_public_key()
        print(f"获取到 SM2 公钥用于验签: {public_key[:8]}...")
        
        # TODO: 在这里实现实际的 token 签名逻辑
        # signed_token = sign_token_with_sm2(token_data, private_key)
        # verified = verify_token_with_sm2(signed_token, public_key)
        
    except KeyError as e:
        print(f"密钥不存在: {e}")
        print("请先运行 'python app/security/key_generator.py' 生成密钥")


def example_data_encryption():
    """示例：使用 SM4 密钥进行数据加密"""
    key_service = get_key_service()
    
    try:
        # 获取 SM4 密钥用于数据加密
        sm4_key = key_service.get_sm4_data_key()
        print(f"获取到 SM4 密钥用于加密: {sm4_key[:8]}...")
        
        # TODO: 在这里实现实际的数据加密逻辑
        # encrypted_data = encrypt_data_with_sm4(sensitive_data, sm4_key)
        # decrypted_data = decrypt_data_with_sm4(encrypted_data, sm4_key)
        
    except KeyError as e:
        print(f"密钥不存在: {e}")
        print("请先运行 'python app/security/key_generator.py' 生成密钥")


def example_version_management():
    """示例：密钥版本管理"""
    key_service = get_key_service()
    
    try:
        # 获取当前版本的密钥
        v1_priv = key_service.get_sm2_token_private_key("v1")
        v1_pub = key_service.get_sm2_token_public_key("v1")
        v1_sm4 = key_service.get_sm4_data_key("v1")
        
        print("当前版本 (v1) 密钥获取成功")
        
        # 尝试获取未来版本的密钥（应该失败）
        try:
            v2_key = key_service.get_sm2_token_private_key("v2")
            print("意外获取到 v2 密钥")
        except KeyError:
            print("v2 密钥不存在（符合预期）")
            
        # 列出所有可用密钥
        keys_info = key_service.list_keys()
        print("\n可用密钥列表:")
        for key_name, info in keys_info.items():
            print(f"  {key_name}: 来源={info['source']}, 有效={info['has_value']}")
            
    except KeyError as e:
        print(f"密钥不存在: {e}")


def main():
    """主函数 - 运行所有示例"""
    print("=" * 60)
    print("密钥服务使用示例")
    print("=" * 60)
    
    print("\n1. Token 签名示例:")
    example_token_signing()
    
    print("\n2. 数据加密示例:")
    example_data_encryption()
    
    print("\n3. 密钥版本管理示例:")
    example_version_management()
    
    print("\n" + "=" * 60)
    print("示例完成!")
    print("=" * 60)


if __name__ == '__main__':
    main()