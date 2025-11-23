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

def log_service_access(
    db: Session,
    service_type: str,  # 'database' 或 'redis'
    service_ip: str
):
    """记录服务访问日志"""
    try:
        # 延迟导入以避免循环依赖
        from app.models import ServiceAccessLog
        from app.heartbeat_checker import ServiceHeartbeatChecker
        
        # 获取真实的客户端IP（访问后端的IP）
        client_ip = get_client_ip()
        
        # 如果客户端IP是127.0.0.1或localhost，获取本机真实IP
        if client_ip in ['127.0.0.1', 'localhost', 'unknown']:
            checker = ServiceHeartbeatChecker()
            client_ip = checker.get_local_ip()
        
        log_entry = ServiceAccessLog(
            client_ip=client_ip,
            service_ip=service_ip,
            service_type=service_type
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        logger.error(f"记录Redis访问日志失败: {e}")
        db.rollback()

def log_database_access(
    db: Session,
    operation: str = None,
    table_name: str = None,
    execution_time_ms: Optional[int] = None,
    status: str = "success",
    error_message: Optional[str] = None,
    affected_rows: Optional[int] = None,
    query_hash: Optional[str] = None
):
    """记录数据库访问日志（简化版）"""
    try:
        from app.config import settings
        from urllib.parse import urlparse
        
        # 提取数据库IP
        parsed = urlparse(settings.database_url)
        database_ip = parsed.hostname
        
        # 记录简化的服务访问日志
        log_service_access(db, 'database', database_ip)
        
    except Exception as e:
        logger.error(f"记录数据库访问日志失败: {e}")

def log_redis_access(
    db: Session,
    operation: str = None,
    redis_key: str = None,
    execution_time_ms: Optional[int] = None,
    status: str = "success",
    error_message: Optional[str] = None,
    additional_info: Optional[Dict[str, Any]] = None
):
    """记录Redis访问日志（简化版）"""
    try:
        from app.config import settings
        from urllib.parse import urlparse
        
        # 提取Redis IP
        parsed = urlparse(settings.redis_url)
        redis_ip = parsed.hostname
        
        # 记录简化的服务访问日志
        log_service_access(db, 'redis', redis_ip)
        
    except Exception as e:
        logger.error(f"记录Redis访问日志失败: {e}")

def generate_query_hash(sql: str) -> str:
    """生成SQL查询的hash值"""
    return hashlib.md5(sql.encode('utf-8')).hexdigest()

class RedisAccessLogger:
    """Redis访问日志装饰器（简化版）"""
    def __init__(self, operation: str):
        self.operation = operation
    
    def __call__(self, func):
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                raise
            finally:
                # 异步记录简化的Redis访问日志
                try:
                    from app.database import get_db
                    db = next(get_db())
                    log_redis_access(db=db)
                except Exception as log_error:
                    logger.error(f"Redis访问日志记录失败: {log_error}")
        
        return wrapper