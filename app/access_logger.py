import time
import hashlib
import json
import socket
from typing import Optional, Any, Dict
from sqlalchemy.orm import Session
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
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
    service_ip: str,
    backend_ip: str = None  # 后端IP，如果为None则使用本机IP
):
    """记录服务访问日志"""
    try:
        # 延迟导入以避免循环依赖
        from app.models import ServiceAccessLog
        
        # 如果没有提供后端IP，使用本机IP
        if backend_ip is None:
            backend_ip = get_real_ip(get_local_ip())
        
        log_entry = ServiceAccessLog(
            client_ip=backend_ip,  # 这里记录的是后端IP，不是前端IP
            service_ip=service_ip,
            service_type=service_type
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        logger.error(f"记录服务访问日志失败: {e}")
        db.rollback()

def log_database_access(
    db: Session,
    operation: str = None,
    table_name: str = None,
    execution_time_ms: Optional[int] = None,
    status: str = "success",
    error_message: Optional[str] = None,
    affected_rows: Optional[int] = None,
    query_hash: Optional[str] = None,
    backend_ip: str = None  # 后端IP参数
):
    """记录数据库访问日志（简化版）"""
    try:
        from app.config import settings
        from urllib.parse import urlparse
        
        # 提取数据库IP
        parsed = urlparse(settings.database_url)
        database_ip = parsed.hostname
        
        # 记录服务访问日志，传递后端IP
        log_service_access(db, 'database', database_ip, backend_ip)
        
    except Exception as e:
        logger.error(f"记录数据库访问日志失败: {e}")

def log_redis_access(
    db: Session,
    operation: str = None,
    redis_key: str = None,
    execution_time_ms: Optional[int] = None,
    status: str = "success",
    error_message: Optional[str] = None,
    additional_info: Optional[Dict[str, Any]] = None,
    backend_ip: str = None  # 后端IP参数
):
    """记录Redis访问日志（简化版）"""
    try:
        from app.config import settings
        from urllib.parse import urlparse
        
        # 提取Redis IP
        parsed = urlparse(settings.redis_url)
        redis_ip = parsed.hostname
        
        # 记录服务访问日志，传递后端IP
        log_service_access(db, 'redis', redis_ip, backend_ip)
        
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

def get_real_ip(ip: str) -> str:
    """获取真实的IP地址，如果是127.0.0.1或localhost，则替换为实际IP"""
    if ip in ['127.0.0.1', 'localhost', '::1']:
        return get_local_ip()
    return ip

def get_local_ip() -> str:
    """获取本机IP地址"""
    try:
        # 创建一个UDP socket连接到外部地址来获取本机IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"

def log_request(
    db: Session,
    frontend_ip: str,
    backend_ip: str,
    request_method: str,
    request_path: str,
    query_params: Optional[str] = None,
    request_time: time = None,
    response_status: Optional[int] = None,
    response_time_ms: Optional[int] = None,
    user_agent: Optional[str] = None
):
    """记录请求日志到数据库"""
    try:
        from app.models import RequestLog
        
        log_entry = RequestLog(
            frontend_ip=frontend_ip,
            backend_ip=backend_ip,
            request_method=request_method,
            request_path=request_path,
            query_params=query_params,
            request_time=request_time,
            response_status=response_status,
            response_time_ms=response_time_ms,
            user_agent=user_agent
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        logger.error(f"记录请求日志失败: {e}")
        db.rollback()

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""
    
    def __init__(self, app):
        super().__init__(app)
        self.local_ip = get_real_ip(get_local_ip())
    
    async def dispatch(self, request: Request, call_next):
        # 跳过/heartbeat/report路径的记录
        if request.url.path == "/heartbeat/report":
            response = await call_next(request)
            return response
        
        # 记录请求开始时间
        start_time = time.time()
        
        # 获取前端IP地址
        frontend_ip = request.client.host
        if "x-forwarded-for" in request.headers:
            frontend_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
        elif "x-real-ip" in request.headers:
            frontend_ip = request.headers["x-real-ip"]
        
        # 如果是本地地址，替换为实际IP
        frontend_ip = get_real_ip(frontend_ip)
        
        # 获取查询参数
        query_params = None
        if request.query_params:
            query_params = json.dumps(dict(request.query_params))
        
        # 获取用户代理
        user_agent = request.headers.get("user-agent")
        
        try:
            # 调用下一个中间件或路由处理器
            response = await call_next(request)
            
            # 计算响应时间
            end_time = time.time()
            response_time_ms = int((end_time - start_time) * 1000)
            
            # 异步记录请求日志
            try:
                from app.database import get_db
                db = next(get_db())
                log_request(
                    db=db,
                    frontend_ip=frontend_ip,
                    backend_ip=self.local_ip,
                    request_method=request.method,
                    request_path=request.url.path,
                    query_params=query_params,
                    request_time=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time)),
                    response_status=response.status_code,
                    response_time_ms=response_time_ms,
                    user_agent=user_agent
                )
                db.close()
            except Exception as log_error:
                logger.error(f"请求日志记录失败: {log_error}")
            
            return response
            
        except Exception as e:
            # 记录错误请求
            try:
                from app.database import get_db
                db = next(get_db())
                log_request(
                    db=db,
                    frontend_ip=frontend_ip,
                    backend_ip=self.local_ip,
                    request_method=request.method,
                    request_path=request.url.path,
                    query_params=query_params,
                    request_time=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time)),
                    response_status=500,
                    response_time_ms=int((time.time() - start_time) * 1000),
                    user_agent=user_agent
                )
                db.close()
            except Exception as log_error:
                logger.error(f"错误请求日志记录失败: {log_error}")
            
            raise e