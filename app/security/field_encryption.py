"""
字段级加密服务
提供 SM4-CBC 字段加密和解密功能，使用 HMAC-SHA256 进行认证
"""

import os
import secrets
import hmac
import hashlib
import logging
from typing import Optional, Tuple
from gmssl import sm4, func

from app.security.key_service import get_key_service

logger = logging.getLogger(__name__)


class FieldEncryptionService:
    """字段加密服务"""
    
    def __init__(self):
        """初始化字段加密服务"""
        self.key_service = get_key_service()
        self._sm4_key = None
        self._hmac_key = None
    
    def _get_sm4_key(self) -> bytes:
        """获取 SM4 密钥"""
        if self._sm4_key is None:
            try:
                # 从密钥服务获取 SM4 密钥
                sm4_key_hex = self.key_service.get_sm4_data_key("v1")
                self._sm4_key = bytes.fromhex(sm4_key_hex)
                logger.info("成功加载 SM4 加密密钥")
            except Exception as e:
                logger.error(f"获取 SM4 密钥失败: {e}")
                raise RuntimeError("无法获取加密密钥")
        return self._sm4_key
    
    def _get_hmac_key(self) -> bytes:
        """获取 HMAC 密钥（从 SM4 密钥派生）"""
        if self._hmac_key is None:
            sm4_key = self._get_sm4_key()
            # 使用 SM4 密钥通过 HKDF 派生 HMAC 密钥
            self._hmac_key = hashlib.sha256(b'hmac-key' + sm4_key).digest()
        return self._hmac_key
    
    def _pkcs7_pad(self, data: bytes, block_size: int = 16) -> bytes:
        """PKCS7 填充"""
        padding_len = block_size - (len(data) % block_size)
        padding = bytes([padding_len] * padding_len)
        return data + padding
    
    def _pkcs7_unpad(self, data: bytes) -> bytes:
        """移除 PKCS7 填充"""
        if not data:
            return data
        padding_len = data[-1]
        return data[:-padding_len]
    
    def _xor_bytes(self, a: bytes, b: bytes) -> bytes:
        """字节异或操作"""
        return bytes(x ^ y for x, y in zip(a, b))
    
    def encrypt_phone(self, phone: Optional[str]) -> Optional[Tuple[bytes, bytes, bytes]]:
        """
        加密手机号（使用手动实现的 SM4-CBC + HMAC-SHA256）
        
        Args:
            phone: 手机号字符串，可以为空
            
        Returns:
            如果手机号为空，返回 None
            否则返回 (密文, IV, HMAC) 的元组
        """
        if phone is None or phone.strip() == "":
            return None
        
        try:
            # 获取 SM4 密钥
            sm4_key = self._get_sm4_key()
            
            # 生成 CBC 模式的 IV (16字节)
            iv = secrets.token_bytes(16)
            
            # 准备数据
            phone_bytes = phone.encode('utf-8')
            padded_data = self._pkcs7_pad(phone_bytes)
            
            # 手动实现 CBC 加密
            sm4_ecb = sm4.CryptSM4(sm4_key, sm4.SM4_ENCRYPT)
            ciphertext = b''
            prev_block = iv
            
            # 分块加密
            for i in range(0, len(padded_data), 16):
                block = padded_data[i:i+16]
                xor_block = self._xor_bytes(block, prev_block)
                encrypted_block = sm4_ecb.crypt_ecb(xor_block)
                ciphertext += encrypted_block
                prev_block = encrypted_block
            
            # 使用 HMAC-SHA256 计算认证标签
            hmac_key = self._get_hmac_key()
            hmac_tag = hmac.new(hmac_key, iv + ciphertext, hashlib.sha256).digest()
            
            logger.debug(f"成功加密手机号，密文长度: {len(ciphertext)}")
            return ciphertext, iv, hmac_tag
            
        except Exception as e:
            logger.error(f"手机号加密失败: {e}")
            raise RuntimeError(f"加密失败: {str(e)}")
    
    def decrypt_phone(self, encrypted_data: Optional[Tuple[bytes, bytes, bytes]]) -> Optional[str]:
        """
        解密手机号
        
        Args:
            encrypted_data: (密文, IV, HMAC) 元组，可以为 None
            
        Returns:
            如果输入为 None，返回 None
            否则返回解密后的手机号字符串
        """
        if encrypted_data is None:
            return None
        
        try:
            ciphertext, iv, hmac_tag = encrypted_data
            
            # 获取密钥
            sm4_key = self._get_sm4_key()
            hmac_key = self._get_hmac_key()
            
            # 验证 HMAC
            expected_hmac = hmac.new(hmac_key, iv + ciphertext, hashlib.sha256).digest()
            if not hmac.compare_digest(hmac_tag, expected_hmac):
                raise ValueError("HMAC 认证失败：数据可能被篡改")
            
            # 手动实现 CBC 解密
            sm4_ecb = sm4.CryptSM4(sm4_key, sm4.SM4_DECRYPT)
            decrypted_data = b''
            prev_block = iv
            
            # 分块解密
            for i in range(0, len(ciphertext), 16):
                block = ciphertext[i:i+16]
                decrypted_block = sm4_ecb.crypt_ecb(block)
                xor_block = self._xor_bytes(decrypted_block, prev_block)
                decrypted_data += xor_block
                prev_block = block
            
            # 移除填充
            unpadded_data = self._pkcs7_unpad(decrypted_data)
            
            # 转换为字符串
            phone = unpadded_data.decode('utf-8')
            
            logger.debug(f"成功解密手机号")
            return phone
            
        except Exception as e:
            logger.error(f"手机号解密失败: {e}")
            raise RuntimeError(f"解密失败: {str(e)}")
    
    def encrypt_phone_to_hex(self, phone: Optional[str]) -> Optional[Tuple[str, str, str]]:
        """
        加密手机号并返回十六进制字符串
        
        Args:
            phone: 手机号字符串，可以为空
            
        Returns:
            如果手机号为空，返回 None
            否则返回 (密文_hex, IV_hex, HMAC_hex) 的元组
        """
        encrypted = self.encrypt_phone(phone)
        if encrypted is None:
            return None
        
        ciphertext, iv, hmac_tag = encrypted
        return (
            ciphertext.hex(),
            iv.hex(),
            hmac_tag.hex()
        )
    
    def decrypt_phone_from_hex(self, encrypted_hex: Optional[Tuple[str, str, str]]) -> Optional[str]:
        """
        从十六进制字符串解密手机号
        
        Args:
            encrypted_hex: (密文_hex, IV_hex, HMAC_hex) 元组，可以为 None
            
        Returns:
            如果输入为 None，返回 None
            否则返回解密后的手机号字符串
        """
        if encrypted_hex is None:
            return None
        
        try:
            ciphertext_hex, iv_hex, hmac_hex = encrypted_hex
            
            # 转换为字节
            ciphertext = bytes.fromhex(ciphertext_hex)
            iv = bytes.fromhex(iv_hex)
            hmac_tag = bytes.fromhex(hmac_hex)
            
            return self.decrypt_phone((ciphertext, iv, hmac_tag))
            
        except Exception as e:
            logger.error(f"十六进制数据解密失败: {e}")
            raise RuntimeError(f"解密失败: {str(e)}")


# 全局字段加密服务实例
_field_encryption_service: Optional[FieldEncryptionService] = None


def get_field_encryption_service() -> FieldEncryptionService:
    """
    获取全局字段加密服务实例（单例模式）
    
    Returns:
        FieldEncryptionService 实例
    """
    global _field_encryption_service
    if _field_encryption_service is None:
        _field_encryption_service = FieldEncryptionService()
    return _field_encryption_service


def init_field_encryption_service() -> FieldEncryptionService:
    """
    初始化全局字段加密服务实例
    
    Returns:
        FieldEncryptionService 实例
    """
    global _field_encryption_service
    _field_encryption_service = FieldEncryptionService()
    return _field_encryption_service