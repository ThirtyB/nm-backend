import json
import redis
from typing import Any, Optional, Union
from datetime import timedelta
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class RedisCache:
    def __init__(self):
        try:
            self.redis_client = redis.from_url(settings.redis_url, decode_responses=True)
            # 测试连接
            self.redis_client.ping()
            logger.info("Redis连接成功")
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            self.redis_client = None
    
    def is_available(self) -> bool:
        """检查Redis是否可用"""
        if not self.redis_client:
            return False
        try:
            self.redis_client.ping()
            return True
        except:
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if not self.is_available():
            return None
        
        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Redis获取缓存失败 {key}: {e}")
            # 如果反序列化失败，删除损坏的缓存
            self.delete(key)
            return None
    
    def set(self, key: str, value: Any, expire_seconds: Optional[int] = None) -> bool:
        """设置缓存值"""
        if not self.is_available():
            return False
        
        try:
            # 使用自定义的序列化方法来处理特殊类型
            serialized_value = json.dumps(value, default=self._json_serializer)
            if expire_seconds:
                return self.redis_client.setex(key, expire_seconds, serialized_value)
            else:
                return self.redis_client.set(key, serialized_value)
        except Exception as e:
            logger.error(f"Redis设置缓存失败 {key}: {e}")
            return False
    
    def _json_serializer(self, obj):
        """自定义JSON序列化器，处理特殊类型"""
        if hasattr(obj, 'model_dump'):  # Pydantic模型
            return obj.model_dump()
        elif hasattr(obj, 'dict'):  # 旧版Pydantic
            return obj.dict()
        elif hasattr(obj, '__dict__'):  # 普通对象
            return obj.__dict__
        else:
            return str(obj)
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self.is_available():
            return False
        
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.error(f"Redis删除缓存失败 {key}: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """删除匹配模式的所有缓存"""
        if not self.is_available():
            return 0
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis批量删除缓存失败 {pattern}: {e}")
            return 0

# 缓存时间常量（秒）
class CacheTTL:
    TWO_HOURS = 7200      # 2小时 - 用户信息、配置信息
    FIVE_MINUTES = 300     # 5分钟 - TOP使用率
    TEN_MINUTES = 600      # 10分钟 - 历史监控
    ONE_MINUTE = 60        # 1分钟 - 其他功能

# 全局缓存实例
cache = RedisCache()

def clear_all_cache():
    """清理所有缓存（用于处理数据结构变更）"""
    if cache.is_available():
        try:
            # 删除所有缓存键
            keys = cache.redis_client.keys("*")
            if keys:
                cache.redis_client.delete(*keys)
                logger.info(f"清理了 {len(keys)} 个缓存键")
            return True
        except Exception as e:
            logger.error(f"清理缓存失败: {e}")
            return False
    return False

def cache_key(*parts) -> str:
    """生成缓存键"""
    return ":".join(str(part) for part in parts)