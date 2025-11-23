from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging
from app.database import get_db
from app.models import ServiceHeartbeat, NodeMonitorMetrics, ServiceAccessLog, AccessLog
from app.auth import get_current_user, get_admin_user, User
from app.cache import cache, CacheTTL, cache_key
from app.decorators import cached

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/heartbeat", tags=["系统探活"])

class HeartbeatRequest(BaseModel):
    ip_address: str
    service_name: str

class ServiceInfo(BaseModel):
    service_name: str
    ip_address: str
    is_online: bool
    last_report_time: datetime

class DatabaseConnectionInfo(BaseModel):
    is_connected: bool
    connection_time: Optional[datetime] = None
    error_message: Optional[str] = None

class ServiceStatusResponse(BaseModel):
    data_collection: List[ServiceInfo] = []
    kafka_process: List[ServiceInfo] = []
    redis: List[ServiceInfo] = []
    frontend: List[ServiceInfo] = []
    backend: List[ServiceInfo] = []
    database: DatabaseConnectionInfo = DatabaseConnectionInfo(is_connected=False)

class TrafficInfo(BaseModel):
    source_ip: str
    target_ip: str
    data_count: int

class TrafficResponse(BaseModel):
    kafka_to_database: List[TrafficInfo] = []
    database_to_backend: List[TrafficInfo] = []
    redis_to_backend: List[TrafficInfo] = []
    backend_to_frontend: List[TrafficInfo] = []

class SystemStatusResponse(BaseModel):
    service_status: ServiceStatusResponse
    traffic_status: TrafficResponse

class TimeRangeRequest(BaseModel):
    start_time: int  # 时间戳格式
    end_time: int    # 时间戳格式

@router.post("/report", summary="服务探活报告")
async def report_heartbeat(
    request: HeartbeatRequest,
    db: Session = Depends(get_db)
):
    """
    服务探活报告接口
    
    其他服务通过此接口报告存活状态
    
    - **ip_address**: 服务所在IP地址
    - **service_name**: 服务名称
    """
    # 记录收到的请求信息
    logger.info(f"收到心跳报告请求 - IP地址: {request.ip_address}, 服务名称: {request.service_name}")
    
    try:
        # 创建探活记录
        heartbeat = ServiceHeartbeat(
            ip_address=request.ip_address,
            service_name=request.service_name,
            report_time=datetime.utcnow()
        )
        
        db.add(heartbeat)
        db.commit()
        db.refresh(heartbeat)
        
        response_data = {
            "status": "success",
            "message": "探活报告已记录",
            "data": {
                "id": heartbeat.id,
                "ip_address": heartbeat.ip_address,
                "service_name": heartbeat.service_name,
                "report_time": heartbeat.report_time.isoformat()
            }
        }
        
        # 记录成功响应信息
        logger.info(f"心跳报告记录成功 - ID: {heartbeat.id}, IP地址: {heartbeat.ip_address}, "
                   f"服务名称: {heartbeat.service_name}, 报告时间: {heartbeat.report_time}")
        
        return response_data
        
    except Exception as e:
        db.rollback()
        # 记录错误信息
        logger.error(f"记录探活失败 - IP地址: {request.ip_address}, 服务名称: {request.service_name}, "
                    f"错误信息: {str(e)}")
        raise HTTPException(status_code=500, detail=f"记录探活失败: {str(e)}")

def heartbeat_cache_key(start_time: int, end_time: int) -> str:
    """生成心跳状态缓存键"""
    return cache_key("heartbeat", "status", start_time, end_time)

def test_database_connection(db: Session) -> DatabaseConnectionInfo:
    """测试数据库连通性"""
    try:
        # 执行简单查询测试连通性
        from sqlalchemy import text
        result = db.execute(text("SELECT 1 as test")).fetchone()
        if result and result[0] == 1:
            return DatabaseConnectionInfo(
                is_connected=True,
                connection_time=datetime.utcnow()
            )
        else:
            return DatabaseConnectionInfo(
                is_connected=False,
                error_message="数据库测试查询失败"
            )
    except Exception as e:
        return DatabaseConnectionInfo(
            is_connected=False,
            error_message=str(e)
        )

def system_status_cache_key(start_time: int, end_time: int) -> str:
    """生成系统状态缓存键"""
    return cache_key("system", "status", start_time, end_time)

@router.post("/status", summary="查询系统状态")
async def get_system_status(
    request: TimeRangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    查询指定时间段内系统状态，包括服务状态和流量统计
    
    - **start_time**: 开始时间戳（Unix时间戳，秒）
    - **end_time**: 结束时间戳（Unix时间戳，秒）
    
    服务类型判断规则：
    - 数据采集开头：2分钟内汇报为在线
    - kafka开头：2分钟内汇报为在线  
    - redis开头：1分钟内汇报为在线
    - 前端/后端开头：1分钟内汇报为在线
    - 数据库：主动测试连通性
    
    流量统计规则：
    - kafka到数据库：kafka处理的数据写入数据库
    - 数据库到后端：后端服务访问数据库的流量
    - redis到后端：后端服务访问redis的流量
    - 后端到前端：前端访问后端API的流量
    
    权限说明：
    - 普通用户：IP地址显示为"隐私保护"
    - 管理员：可见真实IP地址
    
    返回字段说明：
    - service_status: 服务状态信息
    - traffic_status: 流量统计信息
    """
    try:
        # 将时间戳转换为datetime
        start_datetime = datetime.fromtimestamp(request.start_time)
        end_datetime = datetime.fromtimestamp(request.end_time)
        
        print(f"时间范围: {start_datetime} 到 {end_datetime}")  # 调试信息
        
        # 获取服务状态
        service_status = get_service_status_internal(
            start_datetime, end_datetime, db, current_user
        )
        
        # 获取流量统计
        traffic_status = get_traffic_status(
            start_datetime, end_datetime, db, current_user
        )
        
        return SystemStatusResponse(
            service_status=service_status,
            traffic_status=traffic_status
        )
        
    except Exception as e:
        print(f"系统状态查询错误: {str(e)}")  # 调试信息
        raise HTTPException(status_code=500, detail=f"查询系统状态失败: {str(e)}")

def get_service_status_internal(
    start_datetime: datetime,
    end_datetime: datetime,
    db: Session,
    current_user: User
) -> ServiceStatusResponse:
    """获取服务状态内部逻辑"""
    
    # 获取时间段内每个服务的最新汇报记录
    latest_heartbeats = db.query(
        ServiceHeartbeat.ip_address,
        ServiceHeartbeat.service_name,
        func.max(ServiceHeartbeat.report_time).label('latest_report_time')
    ).filter(
        ServiceHeartbeat.report_time >= start_datetime,
        ServiceHeartbeat.report_time <= end_datetime
    ).group_by(
        ServiceHeartbeat.ip_address,
        ServiceHeartbeat.service_name
    ).all()
    
    # 初始化分类结果
    categorized_results = ServiceStatusResponse()
    current_time = datetime.utcnow()
    
    # 判断用户权限
    is_admin = current_user.user_type == "admin"
    
    for heartbeat in latest_heartbeats:
        service_name = heartbeat.service_name
        last_report = heartbeat.latest_report_time
        
        # 判断服务类型和超时时间
        timeout_seconds = None
        category_field = None
        
        if service_name.startswith("数据采集"):
            category_field = "data_collection"
            timeout_seconds = 120  # 2分钟
        elif service_name.startswith("kafka"):
            category_field = "kafka_process"
            timeout_seconds = 120  # 2分钟
        elif service_name.startswith("redis"):
            category_field = "redis"
            timeout_seconds = 60  # 1分钟
        elif service_name.startswith("前端"):
            category_field = "frontend"
            timeout_seconds = 60  # 1分钟
        elif service_name.startswith("后端"):
            category_field = "backend"
            timeout_seconds = 60  # 1分钟
        else:
            # 忽略其他服务
            continue
        
        # 判断是否在线
        time_diff = current_time - last_report
        is_online = time_diff.total_seconds() <= timeout_seconds
        
        # 根据权限决定IP地址显示
        ip_address = heartbeat.ip_address if is_admin else "隐私保护"
        
        # 创建服务信息
        service_info = ServiceInfo(
            service_name=service_name,
            ip_address=ip_address,
            is_online=is_online,
            last_report_time=last_report
        )
        
        # 添加到对应分类
        if category_field == "data_collection":
            categorized_results.data_collection.append(service_info)
        elif category_field == "kafka_process":
            categorized_results.kafka_process.append(service_info)
        elif category_field == "redis":
            categorized_results.redis.append(service_info)
        elif category_field == "frontend":
            categorized_results.frontend.append(service_info)
        elif category_field == "backend":
            categorized_results.backend.append(service_info)
    
    # 测试数据库连通性
    try:
        categorized_results.database = test_database_connection(db)
    except Exception as e:
        categorized_results.database = DatabaseConnectionInfo(
            is_connected=False,
            error_message=f"数据库测试异常: {str(e)}"
        )
    
    return categorized_results

def get_traffic_status(
    start_datetime: datetime,
    end_datetime: datetime,
    db: Session,
    current_user: User
) -> TrafficResponse:
    """获取流量统计"""
    
    is_admin = current_user.user_type == "admin"
    
    # 1. kafka到数据库的流量
    kafka_to_database = []
    if is_admin:
        # 统计所有数据采集发来的数据总量
        total_metrics = db.query(
            func.count(NodeMonitorMetrics.id).label('total_count')
        ).filter(
            NodeMonitorMetrics.inserted_at >= start_datetime,
            NodeMonitorMetrics.inserted_at <= end_datetime
        ).first()
        
        if total_metrics and total_metrics.total_count > 0:
            kafka_to_database.append(TrafficInfo(
                source_ip="kafka_server",
                target_ip="database_server",
                data_count=total_metrics.total_count
            ))
    
    # 2. 数据库到后端的流量
    database_to_backend = []
    if is_admin:
        db_access = db.query(
            ServiceAccessLog.service_ip,
            ServiceAccessLog.client_ip,
            func.count(ServiceAccessLog.id).label('access_count')
        ).filter(
            ServiceAccessLog.service_type == 'database',
            ServiceAccessLog.access_time >= start_datetime,
            ServiceAccessLog.access_time <= end_datetime
        ).group_by(ServiceAccessLog.service_ip, ServiceAccessLog.client_ip).all()
        
        for access in db_access:
            database_to_backend.append(TrafficInfo(
                source_ip=access.service_ip,
                target_ip=access.client_ip,
                data_count=access.access_count
            ))
    
    # 3. redis到后端的流量
    redis_to_backend = []
    if is_admin:
        redis_access = db.query(
            ServiceAccessLog.service_ip,
            ServiceAccessLog.client_ip,
            func.count(ServiceAccessLog.id).label('access_count')
        ).filter(
            ServiceAccessLog.service_type == 'redis',
            ServiceAccessLog.access_time >= start_datetime,
            ServiceAccessLog.access_time <= end_datetime
        ).group_by(ServiceAccessLog.service_ip, ServiceAccessLog.client_ip).all()
        
        for access in redis_access:
            redis_to_backend.append(TrafficInfo(
                source_ip=access.service_ip,
                target_ip=access.client_ip,
                data_count=access.access_count
            ))
    
    # 4. 后端到前端的流量
    backend_to_frontend = []
    if is_admin:
        # 检查access_logs表是否存在
        try:
            access_logs = db.query(
                AccessLog.remote_addr,
                AccessLog.server_addr,
                func.count(AccessLog.id).label('access_count')
            ).filter(
                AccessLog.logtime >= start_datetime,
                AccessLog.logtime <= end_datetime
            ).group_by(AccessLog.remote_addr, AccessLog.server_addr).all()
            
            for access in access_logs:
                backend_to_frontend.append(TrafficInfo(
                    source_ip=access.server_addr or "backend_server",
                    target_ip=access.remote_addr or "frontend_client",
                    data_count=access.access_count
                ))
        except Exception as e:
            # 如果表不存在或查询失败，返回空列表
            print(f"查询access_logs表失败: {e}")
            pass
    
    return TrafficResponse(
        kafka_to_database=kafka_to_database,
        database_to_backend=database_to_backend,
        redis_to_backend=redis_to_backend,
        backend_to_frontend=backend_to_frontend
    )