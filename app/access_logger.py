import time
import hashlib
import json
from typing import Optional, Any, Dict
from sqlalchemy.orm import Session
from fastapi import Request
import logging

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

# 全局变量存储当前请求的客户端IP
_current_client_ip = None

def set_client_ip(ip: str):
    """设置当前请求的客户端IP"""
    global _current_client_ip
    _current_client_ip = ip

def get_client_ip() -> str:
    """获取当前请求的客户端IP"""
    global _current_client_ip
    return _current_client_ip or "unknown"

def log_redis_access(
    db: Session,
    operation: str,
    redis_key: str,
    execution_time_ms: Optional[int] = None,
    status: str = "success",
    error_message: Optional[str] = None,
    additional_info: Optional[Dict[str, Any]] = None
):
    """记录Redis访问日志"""
    try:
        # 延迟导入以避免循环依赖
        from app.models import RedisAccessLog
        
        log_entry = RedisAccessLog(
            client_ip=get_client_ip(),
            operation=operation,
            redis_key=redis_key,
            execution_time_ms=execution_time_ms,
            status=status,
            error_message=error_message,
            additional_info=additional_info
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        logger.error(f"记录Redis访问日志失败: {e}")
        db.rollback()

def log_database_access(
    db: Session,
    operation: str,
    table_name: str,
    execution_time_ms: Optional[int] = None,
    status: str = "success",
    error_message: Optional[str] = None,
    affected_rows: Optional[int] = None,
    query_hash: Optional[str] = None
):
    """记录数据库访问日志"""
    try:
        # 延迟导入以避免循环依赖
        from app.models import DatabaseAccessLog
        
        log_entry = DatabaseAccessLog(
            client_ip=get_client_ip(),
            operation=operation,
            table_name=table_name,
            execution_time_ms=execution_time_ms,
            status=status,
            error_message=error_message,
            affected_rows=affected_rows,
            query_hash=query_hash
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        logger.error(f"记录数据库访问日志失败: {e}")
        db.rollback()

def generate_query_hash(sql: str) -> str:
    """生成SQL查询的hash值"""
    return hashlib.md5(sql.encode('utf-8')).hexdigest()

class RedisAccessLogger:
    """Redis访问日志装饰器"""
    def __init__(self, operation: str):
        self.operation = operation
    
    def __call__(self, func):
        def wrapper(*args, **kwargs):
            from app.database import get_db
            start_time = time.time()
            redis_key = ""
            status = "success"
            error_message = None
            additional_info = None
            
            try:
                # 尝试从参数中提取redis_key
                if args and hasattr(args[0], 'redis_client'):
                    if len(args) > 1:
                        redis_key = str(args[1])
                    elif 'key' in kwargs:
                        redis_key = str(kwargs['key'])
                
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status = "failed"
                error_message = str(e)
                raise
            finally:
                execution_time = int((time.time() - start_time) * 1000)
                
                # 异步记录日志，避免影响性能
                try:
                    db = next(get_db())
                    log_redis_access(
                        db=db,
                        operation=self.operation,
                        redis_key=redis_key or "unknown",
                        execution_time_ms=execution_time,
                        status=status,
                        error_message=error_message,
                        additional_info=additional_info
                    )
                except Exception as log_error:
                    logger.error(f"Redis访问日志记录失败: {log_error}")
        
        return wrapper