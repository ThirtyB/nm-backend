from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from app.database import get_db
from app.cache import cache
from app.auth import get_current_user, get_admin_user, User

router = APIRouter(
    prefix="/cache-management",
    tags=["缓存管理"],
    responses={404: {"description": "Not found"}},
)

@router.delete("/clear")
async def clear_cache(
    pattern: Optional[str] = None,
    current_user: User = Depends(get_admin_user)
):
    """
    清理缓存（仅管理员）
    
    查询参数：
    - pattern: 可选，缓存键模式，如 "node_monitor:*" 或 "scoring:*"
              如果不提供，则清理所有缓存
    
    返回参数：
    - message: 清理结果消息
    - deleted_count: 删除的缓存键数量
    """
    try:
        if pattern:
            deleted_count = cache.delete_pattern(pattern)
            message = f"已清理匹配模式 '{pattern}' 的缓存"
        else:
            # 清理所有缓存需要连接到Redis并执行FLUSHDB
            if cache.is_available():
                cache.redis_client.flushdb()
                deleted_count = "全部"
                message = "已清理所有缓存"
            else:
                raise HTTPException(status_code=500, detail="Redis不可用")
        
        return {
            "message": message,
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理缓存失败: {str(e)}")

@router.get("/status")
async def get_cache_status(
    current_user: User = Depends(get_admin_user)
):
    """
    获取缓存状态（仅管理员）
    
    返回参数：
    - available: Redis是否可用
    - info: Redis信息（如果可用）
    """
    try:
        is_available = cache.is_available()
        result = {
            "available": is_available
        }
        
        if is_available:
            # 获取Redis基本信息
            info = cache.redis_client.info()
            result["info"] = {
                "redis_version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed"),
                "keyspace_hits": info.get("keyspace_hits"),
                "keyspace_misses": info.get("keyspace_misses")
            }
            
            # 获取缓存键数量统计
            keys_info = {}
            for pattern in ["node_monitor:*", "scoring:*", "alert:*", "heartbeat:*", "user:*"]:
                keys = cache.redis_client.keys(pattern)
                keys_info[pattern] = len(keys)
            
            result["keys_count"] = keys_info
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取缓存状态失败: {str(e)}")

@router.get("/keys")
async def get_cache_keys(
    pattern: str = "*",
    limit: int = 100,
    current_user: User = Depends(get_admin_user)
):
    """
    获取缓存键列表（仅管理员）
    
    查询参数：
    - pattern: 键模式，默认为 "*"
    - limit: 返回键数量限制，默认100
    
    返回参数：
    - keys: 缓存键列表
    - total_count: 总键数量
    """
    try:
        if not cache.is_available():
            raise HTTPException(status_code=500, detail="Redis不可用")
        
        keys = cache.redis_client.keys(pattern)
        total_count = len(keys)
        
        # 限制返回数量
        limited_keys = keys[:limit] if limit > 0 else keys
        
        # 获取每个键的TTL
        keys_with_ttl = []
        for key in limited_keys:
            ttl = cache.redis_client.ttl(key)
            keys_with_ttl.append({
                "key": key,
                "ttl": ttl if ttl >= 0 else "永不过期"
            })
        
        return {
            "keys": keys_with_ttl,
            "total_count": total_count,
            "showing_count": len(keys_with_ttl)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取缓存键失败: {str(e)}")