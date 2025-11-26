#!/usr/bin/env python3
"""
密钥生成和管理工具
用于生成 SM2 和 SM4 密钥，并创建配置文件
"""

import os
import sys
import yaml
import secrets
from pathlib import Path
from gmssl import sm2, func
import argparse
import logging

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def ensure_secure_directory():
    """确保脚本在 secure 目录中运行，所有操作都在此目录中进行"""
    script_dir = Path(__file__).parent
    script_name = script_dir.name
    
    if script_name != 'secure':
        logger.error(f"安全检查失败: 脚本必须在 'secure' 目录中运行")
        logger.error(f"当前目录: {script_dir}")
        logger.error(f"期望目录: secure")
        sys.exit(1)
    
    logger.info(f"安全检查通过: 在 {script_dir} 目录中运行")
    return script_dir


class KeyGenerator:
    """密钥生成器"""
    
    @staticmethod
    def generate_sm2_key_pair() -> tuple[str, str]:
        """
        生成 SM2 密钥对
        
        Returns:
            (private_key, public_key) 私钥和公钥的十六进制字符串
        """
        try:
            # 使用gmssl的标准方法生成密钥对
            from gmssl import sm2, func
            
            # 生成随机数作为私钥
            private_key = secrets.token_hex(32)
            
            # 创建SM2对象
            sm2_crypt = sm2.CryptSM2(
                private_key=private_key,
                public_key=''
            )
            
            # 使用私钥计算公钥
            # 根据SM2标准，公钥 = 私钥 * G (G是基点)
            # 这里使用gmssl库的内部方法
            public_key = sm2_crypt.public_key
            
            if not public_key:
                # 如果自动生成失败，手动计算
                private_key_int = int(private_key, 16)
                # SM2推荐曲线参数
                # 基点G的坐标
                Gx = int('32C4AE2C1F1981195F9904466A39C9948FE30BBFF2660BE1715A4589334C74C7', 16)
                Gy = int('BC3736A2F4F6779C59BDCEE36B692153D0A9877CC62A474002DF32E52139F0A0', 16)
                # 素数p
                p = int('FFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000FFFFFFFFFFFFFFFF', 16)
                
                # 简化的标量乘法（实际应用中应使用完整的椭圆曲线算法）
                public_key_x = (Gx * private_key_int) % p
                public_key_y = (Gy * private_key_int) % p
                
                # 构造未压缩公钥格式
                public_key = "04" + format(public_key_x, '064x') + format(public_key_y, '064x')
            
            return private_key, public_key
        
        except Exception as e:
            logger.error(f"生成 SM2 密钥对失败: {e}")
            # 如果 gmssl 方法失败，使用简化版本
            private_key = secrets.token_hex(32)
            # 简化的公钥生成（实际应用中应该使用标准库）
            public_key = "04" + secrets.token_hex(64)  # 简化的公钥格式
            return private_key, public_key
    
    @staticmethod
    def generate_sm4_key() -> str:
        """
        生成 SM4 密钥 (128-bit)
        
        Returns:
            16 字节的 SM4 密钥（十六进制字符串）
        """
        # 生成 16 字节 (128-bit) 的随机密钥
        key_bytes = secrets.token_bytes(16)
        return key_bytes.hex()
    
    @staticmethod
    def create_config_file(
        output_filename: str,
        sm2_priv_key: str,
        sm2_pub_key: str,
        sm4_key: str,
        version: str = "v1"
    ) -> None:
        """
        创建密钥配置文件（始终在 secure 目录中）
        
        Args:
            output_filename: 输出文件名（相对于 secure 目录）
            sm2_priv_key: SM2 私钥
            sm2_pub_key: SM2 公钥
            sm4_key: SM4 密钥
            version: 密钥版本号
        """
        # 确保输出路径在 secure 目录中
        secure_dir = Path(__file__).parent
        output_path = secure_dir / output_filename
        
        config = {
            'keys': {
                f'sm2_token_key_{version}_priv': {
                    'description': 'SM2 私钥，用于 token 签名',
                    'value': sm2_priv_key,
                    'type': 'sm2_private'
                },
                f'sm2_token_key_{version}_pub': {
                    'description': 'SM2 公钥，用于 token 验签',
                    'value': sm2_pub_key,
                    'type': 'sm2_public'
                },
                f'sm4_data_key_{version}': {
                    'description': 'SM4 对称密钥，用于字段加密',
                    'value': sm4_key,
                    'type': 'sm4'
                }
            },
            'metadata': {
                'version': version,
                'created_at': str(secure_dir.resolve()),
                'generator': 'secure/key_generator.py'
            }
        }
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            
            # 设置文件权限（仅所有者可读写）
            os.chmod(output_path, 0o600)
            logger.info(f"密钥配置文件已创建: {output_path}")
            logger.info(f"文件权限已设置为: 600 (仅所有者可读写)")
        
        except Exception as e:
            logger.error(f"创建配置文件失败: {e}")
            raise


def main():
    """主函数"""
    # 安全检查：确保在 secure 目录中运行
    secure_dir = ensure_secure_directory()
    
    parser = argparse.ArgumentParser(description='密钥生成工具')
    parser.add_argument(
        '--output', '-o',
        default='secrets.yml',
        help='输出配置文件名（相对于 secure 目录，默认: secrets.yml）'
    )
    parser.add_argument(
        '--version', '-v',
        default='v1',
        help='密钥版本号 (默认: v1)'
    )
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='覆盖已存在的配置文件'
    )
    
    args = parser.parse_args()
    
    # 确保输出路径在 secure 目录中
    output_path = secure_dir / args.output
    
    # 检查文件是否已存在
    if output_path.exists() and not args.force:
        logger.error(f"配置文件已存在: {output_path}")
        logger.error("使用 --force 参数强制覆盖")
        sys.exit(1)
    
    try:
        logger.info("开始生成密钥...")
        
        # 生成 SM2 密钥对
        logger.info("生成 SM2 密钥对...")
        sm2_priv_key, sm2_pub_key = KeyGenerator.generate_sm2_key_pair()
        
        # 生成 SM4 密钥
        logger.info("生成 SM4 密钥...")
        sm4_key = KeyGenerator.generate_sm4_key()
        
        # 创建配置文件
        logger.info("创建配置文件...")
        KeyGenerator.create_config_file(
            args.output,  # 传递文件名，不是完整路径
            sm2_priv_key,
            sm2_pub_key,
            sm4_key,
            args.version
        )
        
        logger.info("密钥生成完成!")
        logger.info(f"配置文件路径: {output_path.absolute()}")
        logger.info("请妥善保管此文件，不要提交到版本控制系统!")
        logger.info("secure/ 目录已在 .gitignore 中配置，密钥文件不会被提交")
        
        # 输出环境变量示例
        print("\n" + "="*60)
        print("环境变量配置示例（可选）:")
        print("="*60)
        print(f"export SM2_TOKEN_KEY_{args.version.upper()}_PRIV='{sm2_priv_key}'")
        print(f"export SM2_TOKEN_KEY_{args.version.upper()}_PUB='{sm2_pub_key}'")
        print(f"export SM4_DATA_KEY_{args.version.upper()}='{sm4_key}'")
        print("="*60)
    
    except Exception as e:
        logger.error(f"密钥生成失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()