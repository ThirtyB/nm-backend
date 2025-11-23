from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging
import re
from app.database import get_db
from app.models import ServiceHeartbeat, NodeMonitorMetrics, ServiceAccessLog, AccessLog
from app.auth import get_admin_user, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/heartbeat", tags=["系统探活"])

class TimeRangeRequest(BaseModel):
    start_time: int  # 开始时间戳
    end_time: int    # 结束时间戳

class ServiceStatusInfo(BaseModel):
    ip_address: str
    service_name: str
    last_report_time: datetime
    is_online: bool

class ConnectionInfo(BaseModel):
    source_ip: str
    target_ip: str
    data_count: int

class HeartbeatStatusResponse(BaseModel):
    # 第一部分：存活情况
    data_collection: List[ServiceStatusInfo] = []
    kafka: List[ServiceStatusInfo] = []
    redis: List[ServiceStatusInfo] = []
    frontend: List[ServiceStatusInfo] = []
    backend: List[ServiceStatusInfo] = []
    database: List[ServiceStatusInfo] = []
    
    # 第二部分：连接数情况
    data_collection_to_kafka: List[ConnectionInfo] = []
    kafka_to_database: ConnectionInfo
    database_to_backend: List[ConnectionInfo] = []
    redis_to_backend: List[ConnectionInfo] = []
    backend_to_frontend: List[ConnectionInfo] = []

class HeartbeatRequest(BaseModel):
    ip_address: str
    service_name: str

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
        
        logger.info(f"心跳报告记录成功 - ID: {heartbeat.id}, IP地址: {heartbeat.ip_address}, "
                   f"服务名称: {heartbeat.service_name}, 报告时间: {heartbeat.report_time}")
        
        return response_data
        
    except Exception as e:
        db.rollback()
        logger.error(f"记录探活失败 - IP地址: {request.ip_address}, 服务名称: {request.service_name}, "
                    f"错误信息: {str(e)}")
        raise HTTPException(status_code=500, detail=f"记录探活失败: {str(e)}")

@router.post("/status", summary="查询系统状态")
async def get_heartbeat_status(
    request: TimeRangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    查询系统状态（仅管理员可访问）
    
    - **start_time**: 开始时间戳（Unix时间戳，秒）
    - **end_time**: 结束时间戳（Unix时间戳，秒）
    """
    try:
        # 将时间戳转换为datetime
        start_datetime = datetime.fromtimestamp(request.start_time)
        end_datetime = datetime.fromtimestamp(request.end_time)
        current_time = datetime.utcnow()
        
        # 第一部分：存活情况
        service_status = get_service_status(db, start_datetime, end_datetime, current_time)
        
        # 第二部分：连接数情况
        connection_status = get_connection_status(db, start_datetime, end_datetime)
        
        return HeartbeatStatusResponse(
            # 存活情况
            data_collection=service_status["data_collection"],
            kafka=service_status["kafka"],
            redis=service_status["redis"],
            frontend=service_status["frontend"],
            backend=service_status["backend"],
            database=service_status["database"],
            
            # 连接数情况
            data_collection_to_kafka=connection_status["data_collection_to_kafka"],
            kafka_to_database=connection_status["kafka_to_database"],
            database_to_backend=connection_status["database_to_backend"],
            redis_to_backend=connection_status["redis_to_backend"],
            backend_to_frontend=connection_status["backend_to_frontend"]
        )
        
    except Exception as e:
        logger.error(f"查询系统状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询系统状态失败: {str(e)}")

def get_service_status(db: Session, start_datetime: datetime, end_datetime: datetime, current_time: datetime) -> Dict[str, List[ServiceStatusInfo]]:
    """获取服务存活情况"""
    
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
    categorized_results = {
        "data_collection": [],
        "kafka": [],
        "redis": [],
        "frontend": [],
        "backend": [],
        "database": []
    }
    
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
            category_field = "kafka"
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
        elif service_name.startswith("postgres") or service_name.startswith("数据库"):
            category_field = "database"
            timeout_seconds = 60  # 1分钟
        else:
            # 忽略其他服务
            continue
        
        # 判断是否在线
        time_diff = current_time - last_report
        is_online = time_diff.total_seconds() <= timeout_seconds
        
        # 创建服务信息
        service_info = ServiceStatusInfo(
            ip_address=heartbeat.ip_address,
            service_name=service_name,
            last_report_time=last_report,
            is_online=is_online
        )
        
        # 添加到对应分类
        categorized_results[category_field].append(service_info)
    
    return categorized_results

def get_connection_status(db: Session, start_datetime: datetime, end_datetime: datetime) -> Dict[str, Any]:
    """获取连接数情况"""
    
    # 1. 数据采集到kafka的情况
    data_collection_to_kafka = []
    try:
        # 从node_monitor_metrics表获取不同ip的采集服务数据
        collection_metrics = db.query(
            NodeMonitorMetrics.ip,
            func.count(NodeMonitorMetrics.id).label('data_count')
        ).filter(
            NodeMonitorMetrics.inserted_at >= start_datetime,
            NodeMonitorMetrics.inserted_at <= end_datetime
        ).group_by(NodeMonitorMetrics.ip).all()
        
        for metric in collection_metrics:
            data_collection_to_kafka.append(ConnectionInfo(
                source_ip=metric.ip,
                target_ip="kafka_server",
                data_count=metric.data_count
            ))
    except Exception as e:
        logger.warning(f"查询数据采集到kafka连接失败: {e}")
    
    # 2. kafka到数据库，返回总数据条数
    kafka_to_database = ConnectionInfo(
        source_ip="kafka_server",
        target_ip="database_server",
        data_count=0
    )
    try:
        total_metrics = db.query(
            func.count(NodeMonitorMetrics.id).label('total_count')
        ).filter(
            NodeMonitorMetrics.inserted_at >= start_datetime,
            NodeMonitorMetrics.inserted_at <= end_datetime
        ).first()
        
        if total_metrics and total_metrics.total_count > 0:
            kafka_to_database.data_count = total_metrics.total_count
    except Exception as e:
        logger.warning(f"查询kafka到数据库连接失败: {e}")
    
    # 3. 数据库到后端
    database_to_backend = []
    try:
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
            database_to_backend.append(ConnectionInfo(
                source_ip=access.service_ip,
                target_ip=access.client_ip,
                data_count=access.access_count
            ))
    except Exception as e:
        logger.warning(f"查询数据库到后端连接失败: {e}")
    
    # 4. redis到后端
    redis_to_backend = []
    try:
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
            redis_to_backend.append(ConnectionInfo(
                source_ip=access.service_ip,
                target_ip=access.client_ip,
                data_count=access.access_count
            ))
    except Exception as e:
        logger.warning(f"查询redis到后端连接失败: {e}")
    
    # 5. 后端到前端
    backend_to_frontend = []
    try:
        # 从access_logs表获取数据
        access_logs = db.query(
            AccessLog.server_addr,
            AccessLog.upstream_addr,
            func.count(AccessLog.id).label('access_count')
        ).filter(
            AccessLog.logtime >= start_datetime,
            AccessLog.logtime <= end_datetime
        ).group_by(AccessLog.server_addr, AccessLog.upstream_addr).all()
        
        for access in access_logs:
            # 提取IP地址（去除端口）
            frontend_ip = extract_ip_from_address(access.server_addr)
            backend_ip = extract_ip_from_address(access.upstream_addr)
            
            if frontend_ip and backend_ip:
                backend_to_frontend.append(ConnectionInfo(
                    source_ip=backend_ip,
                    target_ip=frontend_ip,
                    data_count=access.access_count
                ))
    except Exception as e:
        logger.warning(f"查询后端到前端连接失败: {e}")
    
    return {
        "data_collection_to_kafka": data_collection_to_kafka,
        "kafka_to_database": kafka_to_database,
        "database_to_backend": database_to_backend,
        "redis_to_backend": redis_to_backend,
        "backend_to_frontend": backend_to_frontend
    }

def extract_ip_from_address(address: Optional[str]) -> Optional[str]:
    """从地址中提取IP地址"""
    if not address:
        return None
    
    # 使用正则表达式提取IP地址
    ip_pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
    match = re.search(ip_pattern, address)
    if match:
        return match.group(1)
    
    return None