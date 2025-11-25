"""
轻量级密钥管理服务 (KeyService)
提供 SM2 和 SM4 密钥的统一管理接口
"""

import os
import yaml
from typing import Optional, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class KeyService:
    """密钥管理服务"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化密钥服务
        
        Args:
            config_file: 密钥配置文件路径，默认为项目根目录下的 secrets.yml
        """
        self._keys: Dict[str, Dict[str, str]] = {}
        self._config_file = config_file or self._get_default_config_path()
        self._load_keys()
    
    def _get_default_config_path(self) -> str:
        """获取默认配置文件路径"""
        # 从当前文件位置推导项目根目录
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent
        return str(project_root / "secure" / "secrets.yml")
    
    def _load_keys(self) -> None:
        """从配置文件和环境变量加载密钥"""
        # 优先从环境变量加载
        self._load_from_env()
        
        # 然后从配置文件加载（如果环境变量中没有的话）
        if os.path.exists(self._config_file):
            self._load_from_file()
        else:
            logger.warning(f"密钥配置文件不存在: {self._config_file}")
    
    def _load_from_env(self) -> None:
        """从环境变量加载密钥"""
        env_mappings = {
            'sm2_token_key_v1_priv': 'SM2_TOKEN_KEY_V1_PRIV',
            'sm2_token_key_v1_pub': 'SM2_TOKEN_KEY_V1_PUB',
            'sm4_data_key_v1': 'SM4_DATA_KEY_V1'
        }
        
        for key_name, env_var in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value:
                self._keys[key_name] = {'value': env_value, 'source': 'environment'}
                logger.info(f"从环境变量加载密钥: {key_name}")
    
    def _load_from_file(self) -> None:
        """从配置文件加载密钥"""
        try:
            with open(self._config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if not config or 'keys' not in config:
                logger.warning("配置文件格式不正确或缺少 keys 节")
                return
            
            for key_name, key_info in config['keys'].items():
                if key_name not in self._keys:  # 环境变量优先
                    self._keys[key_name] = {
                        'value': key_info['value'],
                        'source': 'file'
                    }
                    logger.info(f"从配置文件加载密钥: {key_name}")
        
        except Exception as e:
            logger.error(f"加载密钥配置文件失败: {e}")
    
    def get_sm2_token_private_key(self, version: str = "v1") -> str:
        """
        获取 SM2 token 签名私钥
        
        Args:
            version: 密钥版本号
            
        Returns:
            SM2 私钥字符串
            
        Raises:
            KeyError: 密钥不存在
        """
        key_name = f"sm2_token_key_{version}_priv"
        return self._get_key(key_name)
    
    def get_sm2_token_public_key(self, version: str = "v1") -> str:
        """
        获取 SM2 token 验签公钥
        
        Args:
            version: 密钥版本号
            
        Returns:
            SM2 公钥字符串
            
        Raises:
            KeyError: 密钥不存在
        """
        key_name = f"sm2_token_key_{version}_pub"
        return self._get_key(key_name)
    
    def get_sm4_data_key(self, version: str = "v1") -> str:
        """
        获取 SM4 数据加密密钥
        
        Args:
            version: 密钥版本号
            
        Returns:
            SM4 密钥字符串
            
        Raises:
            KeyError: 密钥不存在
        """
        key_name = f"sm4_data_key_{version}"
        return self._get_key(key_name)
    
    def _get_key(self, key_name: str) -> str:
        """
        获取密钥值
        
        Args:
            key_name: 密钥名称
            
        Returns:
            密钥值
            
        Raises:
            KeyError: 密钥不存在
        """
        if key_name not in self._keys:
            raise KeyError(f"密钥不存在: {key_name}")
        
        return self._keys[key_name]['value']
    
    def list_keys(self) -> Dict[str, Dict[str, Any]]:
        """
        列出所有已加载的密钥信息（不包含实际密钥值）
        
        Returns:
            密钥信息字典
        """
        result = {}
        for key_name, key_info in self._keys.items():
            result[key_name] = {
                'source': key_info['source'],
                'has_value': bool(key_info['value'])
            }
        return result
    
    def reload(self) -> None:
        """重新加载密钥"""
        self._keys.clear()
        self._load_keys()
        logger.info("密钥已重新加载")


# 全局密钥服务实例
_key_service: Optional[KeyService] = None


def get_key_service() -> KeyService:
    """
    获取全局密钥服务实例（单例模式）
    
    Returns:
        KeyService 实例
    """
    global _key_service
    if _key_service is None:
        _key_service = KeyService()
    return _key_service


def init_key_service(config_file: Optional[str] = None) -> KeyService:
    """
    初始化全局密钥服务实例
    
    Args:
        config_file: 密钥配置文件路径
        
    Returns:
        KeyService 实例
    """
    global _key_service
    _key_service = KeyService(config_file)
    return _key_service