import json
import redis
from typing import Any, Optional, Union
from datetime import timedelta
from app.config import settings
from app.access_logger import log_redis_access, get_client_ip
import logging
import time

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
        
        start_time = time.time()
        status = "success"
        error_message = None
        
        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except (json.JSONDecodeError, Exception) as e:
            status = "failed"
            error_message = str(e)
            logger.error(f"Redis获取缓存失败 {key}: {e}")
            # 如果反序列化失败，删除损坏的缓存
            self.delete(key)
            return None
        finally:
            # 记录访问日志
            try:
                from app.database import get_db
                db = next(get_db())
                execution_time = int((time.time() - start_time) * 1000)
                log_redis_access(
                    db=db,
                    operation="GET",
                    redis_key=key,
                    execution_time_ms=execution_time,
                    status=status,
                    error_message=error_message
                )
            except Exception as log_error:
                logger.error(f"记录Redis访问日志失败: {log_error}")
    
    def set(self, key: str, value: Any, expire_seconds: Optional[int] = None) -> bool:
        """设置缓存值"""
        if not self.is_available():
            return False
        
        start_time = time.time()
        status = "success"
        error_message = None
        additional_info = {"expire_seconds": expire_seconds} if expire_seconds else None
        
        try:
            # 预处理数据以处理循环引用
            processed_value = self._preprocess_for_serialization(value)
            
            # 使用自定义的序列化方法来处理特殊类型
            serialized_value = json.dumps(processed_value, default=self._json_serializer)
            if expire_seconds:
                result = self.redis_client.setex(key, expire_seconds, serialized_value)
            else:
                result = self.redis_client.set(key, serialized_value)
            return result
        except Exception as e:
            status = "failed"
            error_message = str(e)
            logger.error(f"Redis设置缓存失败 {key}: {e}")
            return False
        finally:
            # 记录访问日志
            try:
                from app.database import get_db
                db = next(get_db())
                execution_time = int((time.time() - start_time) * 1000)
                log_redis_access(
                    db=db,
                    operation="SET",
                    redis_key=key,
                    execution_time_ms=execution_time,
                    status=status,
                    error_message=error_message,
                    additional_info=additional_info
                )
            except Exception as log_error:
                logger.error(f"记录Redis访问日志失败: {log_error}")
    
    def _preprocess_for_serialization(self, obj, visited=None):
        """预处理对象以处理循环引用"""
        if visited is None:
            visited = set()
        
        obj_id = id(obj)
        
        # 检查是否已经访问过
        if obj_id in visited:
            return {"__circular_reference__": True, "__type__": type(obj).__name__}
        
        # 基本类型直接返回
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        
        # 添加到已访问集合
        visited.add(obj_id)
        
        try:
            if isinstance(obj, dict):
                result = {}
                for k, v in obj.items():
                    result[k] = self._preprocess_for_serialization(v, visited.copy())
                return result
            elif isinstance(obj, (list, tuple)):
                result = [self._preprocess_for_serialization(item, visited.copy()) for item in obj]
                return result
            elif hasattr(obj, 'model_dump') and callable(getattr(obj, 'model_dump')):
                return self._preprocess_for_serialization(obj.model_dump(), visited.copy())
            elif hasattr(obj, 'dict') and callable(getattr(obj, 'dict')):
                return self._preprocess_for_serialization(obj.dict(), visited.copy())
            elif hasattr(obj, '__dict__'):
                return self._preprocess_for_serialization(obj.__dict__, visited.copy())
            else:
                return str(obj)
        except Exception:
            return {"__serialization_error__": True, "__type__": type(obj).__name__, "__str__": str(obj)}
    
    def _json_serializer(self, obj):
        """自定义JSON序列化器，处理特殊类型"""
        # 使用线程本地的序列化栈来避免线程安全问题
        if not hasattr(self, '_serialization_stack'):
            self._serialization_stack = set()
        
        # 检查循环引用
        obj_id = id(obj)
        if obj_id in self._serialization_stack:
            return {"__circular_reference__": True, "__type__": type(obj).__name__}
        
        self._serialization_stack.add(obj_id)
        
        try:
            # 检查是否是Pydantic模型
            if hasattr(obj, 'model_dump') and callable(getattr(obj, 'model_dump')):
                return obj.model_dump()
            elif hasattr(obj, 'dict') and callable(getattr(obj, 'dict')):
                return obj.dict()
            elif hasattr(obj, '__dict__') and not isinstance(obj, (dict, list, tuple, str, int, float, bool)):
                return self._safe_dict_conversion(obj)
            else:
                # 对于基本类型和字典等，直接返回
                return obj
        finally:
            self._serialization_stack.discard(obj_id)
    
    def _safe_dict_conversion(self, obj):
        """安全地将对象转换为字典，避免循环引用"""
        try:
            result = {}
            obj_dict = obj.__dict__
            for key, value in obj_dict.items():
                # 跳过私有属性和可能引起循环引用的属性
                if key.startswith('_'):
                    continue
                # 使用相同的序列化器处理值
                result[key] = self._json_serializer(value)
            return result
        except Exception:
            # 如果转换失败，返回字符串表示
            return {"__serialization_error__": True, "__type__": type(obj).__name__, "__str__": str(obj)}
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self.is_available():
            return False
        
        start_time = time.time()
        status = "success"
        error_message = None
        
        try:
            result = bool(self.redis_client.delete(key))
            return result
        except Exception as e:
            status = "failed"
            error_message = str(e)
            logger.error(f"Redis删除缓存失败 {key}: {e}")
            return False
        finally:
            # 记录访问日志
            try:
                from app.database import get_db
                db = next(get_db())
                execution_time = int((time.time() - start_time) * 1000)
                log_redis_access(
                    db=db,
                    operation="DELETE",
                    redis_key=key,
                    execution_time_ms=execution_time,
                    status=status,
                    error_message=error_message
                )
            except Exception as log_error:
                logger.error(f"记录Redis访问日志失败: {log_error}")
    
    def delete_pattern(self, pattern: str) -> int:
        """删除匹配模式的所有缓存"""
        if not self.is_available():
            return 0
        
        start_time = time.time()
        status = "success"
        error_message = None
        deleted_count = 0
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted_count = self.redis_client.delete(*keys)
            return deleted_count
        except Exception as e:
            status = "failed"
            error_message = str(e)
            logger.error(f"Redis批量删除缓存失败 {pattern}: {e}")
            return 0
        finally:
            # 记录访问日志
            try:
                from app.database import get_db
                db = next(get_db())
                execution_time = int((time.time() - start_time) * 1000)
                log_redis_access(
                    db=db,
                    operation="DELETE_PATTERN",
                    redis_key=pattern,
                    execution_time_ms=execution_time,
                    status=status,
                    error_message=error_message,
                    additional_info={"deleted_count": deleted_count}
                )
            except Exception as log_error:
                logger.error(f"记录Redis访问日志失败: {log_error}")

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