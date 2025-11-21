import functools
import hashlib
from typing import Any, Callable, Optional
from app.cache import cache, CacheTTL, cache_key

def cached(ttl_seconds: int, key_prefix: str = "", key_func: Optional[Callable] = None):
    """
    缓存装饰器
    
    Args:
        ttl_seconds: 缓存过期时间（秒）
        key_prefix: 缓存键前缀
        key_func: 自定义缓存键生成函数，接收函数参数，返回字符串
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                # 提取key_func需要的参数，排除依赖注入的参数
                import inspect
                sig = inspect.signature(key_func)
                key_func_params = {}
                
                # 从kwargs中提取key_func需要的参数
                for param_name in sig.parameters:
                    if param_name in kwargs:
                        key_func_params[param_name] = kwargs[param_name]
                
                cache_key_str = key_func(**key_func_params)
            else:
                # 默认使用函数名和参数哈希作为键
                # 排除依赖注入的参数
                filtered_kwargs = {k: v for k, v in kwargs.items() 
                                 if k not in ['db', 'current_user', 'token']}
                params_str = str(args) + str(sorted(filtered_kwargs.items()))
                params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
                cache_key_str = cache_key(key_prefix, func.__name__, params_hash)
            
            # 尝试从缓存获取
            cached_result = cache.get(cache_key_str)
            if cached_result is not None:
                return cached_result
            
            # 执行原函数
            result = await func(*args, **kwargs)
            
            # 存入缓存
            cache.set(cache_key_str, result, ttl_seconds)
            
            return result
        
        return wrapper
    return decorator

def invalidate_cache_pattern(pattern: str):
    """缓存失效装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            # 执行后删除匹配的缓存
            cache.delete_pattern(pattern)
            return result
        return wrapper
    return decorator