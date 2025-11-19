from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import List, Optional
from app.database import get_db
from app.models import ServiceHeartbeat
from app.auth import get_current_user, get_admin_user, User

router = APIRouter(prefix="/heartbeat", tags=["系统探活"])

class HeartbeatRequest(BaseModel):
    ip_address: str
    service_name: str

class ServiceInfo(BaseModel):
    service_name: str
    ip_address: str
    is_online: bool
    last_report_time: datetime

class ServiceStatusResponse(BaseModel):
    data_collection: List[ServiceInfo] = []
    kafka_process: List[ServiceInfo] = []
    frontend: List[ServiceInfo] = []
    backend: List[ServiceInfo] = []

class TimeRangeRequest(BaseModel):
    start_time: datetime
    end_time: datetime

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
        
        return {
            "status": "success",
            "message": "探活报告已记录",
            "data": {
                "id": heartbeat.id,
                "ip_address": heartbeat.ip_address,
                "service_name": heartbeat.service_name,
                "report_time": heartbeat.report_time.isoformat()
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"记录探活失败: {str(e)}")

@router.post("/status", summary="查询服务状态")
async def get_service_status(
    request: TimeRangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    查询指定时间段内服务状态
    
    - **start_time**: 开始时间
    - **end_time**: 结束时间
    
    服务类型判断规则：
    - 数据采集开头：2分钟内汇报为在线
    - kafka开头：2分钟内汇报为在线  
    - 前端/后端开头：30秒内汇报为在线
    - 其他服务：忽略
    
    权限说明：
    - 普通用户：IP地址显示为"隐私保护"
    - 管理员：可见真实IP地址
    """
    try:
        # 获取时间段内每个服务的最新汇报记录
        latest_heartbeats = db.query(
            ServiceHeartbeat.ip_address,
            ServiceHeartbeat.service_name,
            func.max(ServiceHeartbeat.report_time).label('latest_report_time')
        ).filter(
            ServiceHeartbeat.report_time >= request.start_time,
            ServiceHeartbeat.report_time <= request.end_time
        ).group_by(
            ServiceHeartbeat.ip_address,
            ServiceHeartbeat.service_name
        ).all()
        
        # 初始化分类结果
        categorized_results = ServiceStatusResponse()
        current_time = datetime.utcnow()
        
        # 判断用户权限 - 确保用户类型存在且为admin
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
            elif service_name.startswith("前端"):
                category_field = "frontend"
                timeout_seconds = 30  # 30秒
            elif service_name.startswith("后端"):
                category_field = "backend"
                timeout_seconds = 30  # 30秒
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
            elif category_field == "frontend":
                categorized_results.frontend.append(service_info)
            elif category_field == "backend":
                categorized_results.backend.append(service_info)
        
        # 手动构建响应字典，使用中文键名
        response_dict = {
            "数据采集": categorized_results.data_collection,
            "kafka进程": categorized_results.kafka_process,
            "前端": categorized_results.frontend,
            "后端": categorized_results.backend
        }
        
        return response_dict
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询服务状态失败: {str(e)}")
    """
    查询指定时间段内服务状态
    
    - **start_time**: 开始时间
    - **end_time**: 结束时间
    
    服务类型判断规则：
    - 数据采集开头：2分钟内汇报为在线
    - kafka开头：2分钟内汇报为在线  
    - 前端/后端开头：30秒内汇报为在线
    - 其他服务：忽略
    """
    try:
        # 获取时间段内每个服务的最新汇报记录
        latest_heartbeats = db.query(
            ServiceHeartbeat.ip_address,
            ServiceHeartbeat.service_name,
            func.max(ServiceHeartbeat.report_time).label('latest_report_time')
        ).filter(
            ServiceHeartbeat.report_time >= request.start_time,
            ServiceHeartbeat.report_time <= request.end_time
        ).group_by(
            ServiceHeartbeat.ip_address,
            ServiceHeartbeat.service_name
        ).all()
        
        results = []
        current_time = datetime.utcnow()
        
        for heartbeat in latest_heartbeats:
            service_name = heartbeat.service_name
            last_report = heartbeat.latest_report_time
            
            # 判断服务类型和超时时间
            service_type = None
            timeout_seconds = None
            
            if service_name.startswith("数据采集"):
                service_type = "数据采集"
                timeout_seconds = 120  # 2分钟
            elif service_name.startswith("kafka"):
                service_type = "kafka进程"
                timeout_seconds = 120  # 2分钟
            elif service_name.startswith("前端") or service_name.startswith("后端"):
                service_type = "前端/后端"
                timeout_seconds = 30  # 30秒
            else:
                # 忽略其他服务
                continue
            
            # 判断是否在线
            time_diff = current_time - last_report
            is_online = time_diff.total_seconds() <= timeout_seconds
            
            results.append(ServiceStatusResponse(
                service_type=service_type,
                service_name=service_name,
                ip_address=heartbeat.ip_address,
                is_online=is_online,
                last_report_time=last_report
            ))
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询服务状态失败: {str(e)}")