#!/usr/bin/env python3
"""
密钥服务测试脚本
测试 KeyService 的各项功能
"""

import os
import sys
import tempfile
import yaml
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.security.key_service import KeyService, get_key_service, init_key_service


def test_key_service():
    """测试密钥服务功能"""
    print("=" * 60)
    print("密钥服务功能测试")
    print("=" * 60)
    
    # 测试 1: 创建临时配置文件
    print("\n1. 测试配置文件加载...")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        test_config = {
            'keys': {
                'sm2_token_key_v1_priv': {
                    'value': 'test_sm2_priv_key',
                    'type': 'sm2_private'
                },
                'sm2_token_key_v1_pub': {
                    'value': 'test_sm2_pub_key',
                    'type': 'sm2_public'
                },
                'sm4_data_key_v1': {
                    'value': 'test_sm4_key_32_chars',
                    'type': 'sm4'
                }
            }
        }
        yaml.dump(test_config, f)
        temp_config_path = f.name
    
    try:
        # 测试 2: 初始化密钥服务
        print("2. 初始化密钥服务...")
        key_service = KeyService(temp_config_path)
        
        # 测试 3: 获取各种密钥
        print("3. 测试密钥获取...")
        sm2_priv = key_service.get_sm2_token_private_key()
        sm2_pub = key_service.get_sm2_token_public_key()
        sm4_key = key_service.get_sm4_data_key()
        
        print(f"   SM2 私钥: {sm2_priv}")
        print(f"   SM2 公钥: {sm2_pub}")
        print(f"   SM4 密钥: {sm4_key}")
        
        # 验证密钥值
        assert sm2_priv == 'test_sm2_priv_key', "SM2 私钥不匹配"
        assert sm2_pub == 'test_sm2_pub_key', "SM2 公钥不匹配"
        assert sm4_key == 'test_sm4_key_32_chars', "SM4 密钥不匹配"
        print("   ✓ 密钥值验证通过")
        
        # 测试 4: 列出密钥信息
        print("4. 测试密钥列表...")
        keys_info = key_service.list_keys()
        for key_name, info in keys_info.items():
            print(f"   {key_name}: source={info['source']}, has_value={info['has_value']}")
        
        # 测试 5: 版本参数测试
        print("5. 测试版本参数...")
        try:
            key_service.get_sm2_token_private_key("v2")
            print("   ✗ 应该抛出密钥不存在异常")
        except KeyError:
            print("   ✓ 版本不存在时正确抛出异常")
        
        # 测试 6: 全局单例测试
        print("6. 测试全局单例...")
        service1 = get_key_service()
        service2 = get_key_service()
        assert service1 is service2, "全局单例失败"
        print("   ✓ 全局单例测试通过")
        
        print("\n" + "=" * 60)
        print("所有测试通过! ✓")
        print("=" * 60)
        
    finally:
        # 清理临时文件
        os.unlink(temp_config_path)


def test_environment_variable_priority():
    """测试环境变量优先级"""
    print("\n" + "=" * 60)
    print("环境变量优先级测试")
    print("=" * 60)
    
    # 设置环境变量
    test_env_vars = {
        'SM2_TOKEN_KEY_V1_PRIV': 'env_sm2_priv_key',
        'SM2_TOKEN_KEY_V1_PUB': 'env_sm2_pub_key',
        'SM4_DATA_KEY_V1': 'env_sm4_key'
    }
    
    # 保存原始环境变量
    original_env = {}
    for key, value in test_env_vars.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    try:
        # 创建临时配置文件（密钥值不同）
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            test_config = {
                'keys': {
                    'sm2_token_key_v1_priv': {
                        'value': 'file_sm2_priv_key',
                        'type': 'sm2_private'
                    },
                    'sm2_token_key_v1_pub': {
                        'value': 'file_sm2_pub_key',
                        'type': 'sm2_public'
                    },
                    'sm4_data_key_v1': {
                        'value': 'file_sm4_key',
                        'type': 'sm4'
                    }
                }
            }
            yaml.dump(test_config, f)
            temp_config_path = f.name
        
        try:
            key_service = KeyService(temp_config_path)
            
            # 验证环境变量优先
            sm2_priv = key_service.get_sm2_token_private_key()
            sm2_pub = key_service.get_sm2_token_public_key()
            sm4_key = key_service.get_sm4_data_key()
            
            print(f"SM2 私钥: {sm2_priv}")
            print(f"SM2 公钥: {sm2_pub}")
            print(f"SM4 密钥: {sm4_key}")
            
            assert sm2_priv == 'env_sm2_priv_key', "环境变量优先级失败"
            assert sm2_pub == 'env_sm2_pub_key', "环境变量优先级失败"
            assert sm4_key == 'env_sm4_key', "环境变量优先级失败"
            
            print("✓ 环境变量优先级测试通过")
            
        finally:
            os.unlink(temp_config_path)
    
    finally:
        # 恢复原始环境变量
        for key, original_value in original_env.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value


def main():
    """主函数"""
    try:
        test_key_service()
        test_environment_variable_priority()
        
        print("\n" + "=" * 60)
        print("所有测试完成! 密钥服务工作正常。")
        print("=" * 60)
        
        print("\n使用说明:")
        print("1. 运行 'python secure/key_generator.py' 生成密钥")
        print("2. 密钥文件将自动生成到 'secure/secrets.yml'")
        print("3. 或者设置环境变量来提供密钥")
        print("4. 在代码中使用 'get_key_service()' 获取密钥服务实例")
        
    except Exception as e:
        print(f"\n测试失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()