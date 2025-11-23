import asyncio
import socket
import time
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import ServiceHeartbeat
from app.config import settings
import redis
import psycopg2
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class ServiceHeartbeatChecker:
    def __init__(self):
        self.running = False
        
    def get_local_ip(self) -> str:
        """获取本机IP地址"""
        try:
            # 创建一个socket连接到公共DNS服务器来获取本机IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
            return local_ip
        except Exception as e:
            logger.error(f"获取本机IP失败: {e}")
            return "127.0.0.1"
    
    def extract_ip_from_url(self, url: str) -> str:
        """从URL中提取IP地址"""
        try:
            parsed = urlparse(url)
            if parsed.hostname:
                return parsed.hostname
            return "localhost"
        except Exception as e:
            logger.error(f"从URL {url} 提取IP失败: {e}")
            return "localhost"
    
    def test_redis_connection(self, redis_url: str) -> bool:
        """测试Redis连接"""
        try:
            r = redis.from_url(redis_url, socket_timeout=5)
            r.ping()
            return True
        except Exception as e:
            logger.error(f"Redis连接测试失败: {e}")
            return False
    
    def test_database_connection(self, database_url: str) -> bool:
        """测试数据库连接"""
        try:
            # 使用psycopg2直接连接测试
            conn = psycopg2.connect(database_url)
            conn.close()
            return True
        except Exception as e:
            logger.error(f"数据库连接测试失败: {e}")
            return False
    
    def record_heartbeat(self, service_name: str, ip_address: str, is_alive: bool):
        """记录心跳到数据库"""
        try:
            db = SessionLocal()
            try:
                # 只有服务存活时才记录
                if is_alive:
                    heartbeat = ServiceHeartbeat(
                        ip_address=ip_address,
                        service_name=service_name,
                        report_time=datetime.utcnow()
                    )
                    db.add(heartbeat)
                    db.commit()
                    logger.info(f"记录心跳成功 - 服务: {service_name}, IP: {ip_address}")
                else:
                    logger.warning(f"服务不可用 - 服务: {service_name}, IP: {ip_address}")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"记录心跳失败 - 服务: {service_name}, 错误: {e}")
    
    async def check_all_services(self):
        """检查所有服务的状态"""
        try:
            # 1. 检查后端服务
            backend_ip = self.get_local_ip()
            self.record_heartbeat("后端", backend_ip, True)  # 后端服务本身是运行的
            
            # 2. 检查Redis服务
            redis_ip = self.extract_ip_from_url(settings.redis_url)
            redis_alive = self.test_redis_connection(settings.redis_url)
            self.record_heartbeat("redis", redis_ip, redis_alive)
            
            # 3. 检查数据库服务
            database_ip = self.extract_ip_from_url(settings.database_url)
            database_alive = self.test_database_connection(settings.database_url)
            self.record_heartbeat("postgres", database_ip, database_alive)
            
        except Exception as e:
            logger.error(f"检查服务状态失败: {e}")
    
    async def start_heartbeat_check(self):
        """启动心跳检查定时任务"""
        self.running = True
        logger.info("启动服务心跳检查定时任务...")
        
        while self.running:
            try:
                await self.check_all_services()
                await asyncio.sleep(30)  # 每30秒检查一次
            except Exception as e:
                logger.error(f"心跳检查任务出错: {e}")
                await asyncio.sleep(30)  # 出错后也等待30秒再重试
    
    def stop(self):
        """停止心跳检查"""
        self.running = False
        logger.info("停止服务心跳检查定时任务")

# 全局心跳检查器实例
heartbeat_checker = ServiceHeartbeatChecker()