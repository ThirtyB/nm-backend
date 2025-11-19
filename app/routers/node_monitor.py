from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from app.database import get_db
from app.models import NodeMonitorMetrics
from app.schemas import ActiveIPsResponse, NodeLatestMetrics, NodeMetricsResponse, IPMetricsRequest, TimeRangeParams
from app.auth import get_current_user, User

router = APIRouter(
    prefix="/node-monitor",
    tags=["节点监控"],
    responses={404: {"description": "Not found"}},
)

def calculate_cpu_usage(cpu_usr: Optional[float], cpu_sys: Optional[float], cpu_iow: Optional[float]) -> Optional[float]:
    """计算CPU使用率"""
    if cpu_usr is None or cpu_sys is None or cpu_iow is None:
        return None
    return round(cpu_usr + cpu_sys + cpu_iow, 2)

def calculate_memory_usage(mem_total: Optional[int], mem_free: Optional[int], mem_buff: Optional[int], mem_cache: Optional[int]) -> Optional[float]:
    """计算内存使用率"""
    if mem_total is None or mem_total == 0:
        return None
    used = (mem_total - mem_free - mem_buff - mem_cache) if mem_free is not None else None
    if used is None:
        return None
    return round((used / mem_total) * 100, 2)

def calculate_swap_usage(swap_total: Optional[int], swap_used: Optional[int]) -> Optional[float]:
    """计算Swap使用率"""
    if swap_total is None or swap_total == 0 or swap_used is None:
        return None
    return round((swap_used / swap_total) * 100, 2)

def calculate_network_rate(net_rx_kbps: Optional[float], net_tx_kbps: Optional[float]) -> Optional[float]:
    """计算网络速率（总速率）"""
    if net_rx_kbps is None or net_tx_kbps is None:
        return None
    return round(net_rx_kbps + net_tx_kbps, 2)

@router.get("/active-ips", response_model=ActiveIPsResponse)
async def get_active_ips(
    start_time: int = Query(..., description="开始时间戳"),
    end_time: int = Query(..., description="结束时间戳"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    返回当前选中的时间段活跃的IP地址信息，和每个IP的最新CPU使用率、磁盘使用率、内存使用率、Swap使用率、网络速率
    """
    try:
        # 使用窗口函数获取每个IP的最新记录，避免使用DISTINCT
        query = text("""
            WITH ranked_metrics AS (
                SELECT 
                    ip,
                    ts,
                    cpu_usr,
                    cpu_sys,
                    cpu_iow,
                    mem_total,
                    mem_free,
                    mem_buff,
                    mem_cache,
                    swap_total,
                    swap_used,
                    disk_used_percent,
                    net_rx_kbps,
                    net_tx_kbps,
                    ROW_NUMBER() OVER (PARTITION BY ip ORDER BY ts DESC) as rn
                FROM node_monitor_metrics 
                WHERE ts BETWEEN :start_time AND :end_time
            )
            SELECT 
                ip,
                ts as latest_ts,
                cpu_usr,
                cpu_sys,
                cpu_iow,
                mem_total,
                mem_free,
                mem_buff,
                mem_cache,
                swap_total,
                swap_used,
                disk_used_percent,
                net_rx_kbps,
                net_tx_kbps
            FROM ranked_metrics 
            WHERE rn = 1
            ORDER BY ip
        """)
        
        result = db.execute(query, {
            "start_time": start_time,
            "end_time": end_time
        })
        
        rows = result.fetchall()
        
        active_ips = []
        for row in rows:
            cpu_usage = calculate_cpu_usage(row.cpu_usr, row.cpu_sys, row.cpu_iow)
            memory_usage = calculate_memory_usage(row.mem_total, row.mem_free, row.mem_buff, row.mem_cache)
            swap_usage = calculate_swap_usage(row.swap_total, row.swap_used)
            network_rate = calculate_network_rate(row.net_rx_kbps, row.net_tx_kbps)
            
            latest_metrics = NodeLatestMetrics(
                ip=row.ip,
                latest_ts=row.latest_ts,
                cpu_usage_rate=cpu_usage,
                disk_usage_rate=round(row.disk_used_percent, 2) if row.disk_used_percent is not None else None,
                memory_usage_rate=memory_usage,
                swap_usage_rate=swap_usage,
                network_rate=network_rate
            )
            active_ips.append(latest_metrics)
        
        return ActiveIPsResponse(
            active_ips=active_ips,
            total_count=len(active_ips),
            time_range={
                "start_time": start_time,
                "end_time": end_time
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询活跃IP失败: {str(e)}")

@router.get("/ip-metrics/{ip}", response_model=List[NodeMetricsResponse])
async def get_ip_metrics(
    ip: str,
    start_time: int = Query(..., description="开始时间戳"),
    end_time: int = Query(..., description="结束时间戳"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    返回某一个IP选定时间段的所有记录信息，按照时间先后顺序排序
    """
    try:
        # 查询指定IP在时间段内的所有记录
        query = db.query(NodeMonitorMetrics).filter(
            NodeMonitorMetrics.ip == ip,
            NodeMonitorMetrics.ts >= start_time,
            NodeMonitorMetrics.ts <= end_time
        ).order_by(NodeMonitorMetrics.ts.asc())
        
        metrics = query.all()
        
        if not metrics:
            raise HTTPException(status_code=404, detail=f"IP {ip} 在指定时间段内没有监控数据")
        
        return metrics
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询IP监控数据失败: {str(e)}")

@router.get("/ip-metrics", response_model=List[NodeMetricsResponse])
async def get_ip_metrics_with_body(
    request: IPMetricsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    返回某一个IP选定时间段的所有记录信息，按照时间先后顺序排序（POST方式）
    """
    try:
        # 查询指定IP在时间段内的所有记录
        query = db.query(NodeMonitorMetrics).filter(
            NodeMonitorMetrics.ip == request.ip,
            NodeMonitorMetrics.ts >= request.start_time,
            NodeMonitorMetrics.ts <= request.end_time
        ).order_by(NodeMonitorMetrics.ts.asc())
        
        metrics = query.all()
        
        if not metrics:
            raise HTTPException(status_code=404, detail=f"IP {request.ip} 在指定时间段内没有监控数据")
        
        return metrics
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询IP监控数据失败: {str(e)}")

@router.get("/summary")
async def get_monitoring_summary(
    start_time: int = Query(..., description="开始时间戳"),
    end_time: int = Query(..., description="结束时间戳"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取监控数据的汇总信息
    """
    try:
        # 统计活跃IP数量
        active_ips_query = text("""
            SELECT COUNT(DISTINCT ip) as active_ip_count
            FROM node_monitor_metrics 
            WHERE ts BETWEEN :start_time AND :end_time
        """)
        
        # 统计总记录数
        total_records_query = text("""
            SELECT COUNT(*) as total_records
            FROM node_monitor_metrics 
            WHERE ts BETWEEN :start_time AND :end_time
        """)
        
        active_ips_result = db.execute(active_ips_query, {
            "start_time": start_time,
            "end_time": end_time
        })
        
        total_records_result = db.execute(total_records_query, {
            "start_time": start_time,
            "end_time": end_time
        })
        
        active_ip_count = active_ips_result.fetchone()[0]
        total_records = total_records_result.fetchone()[0]
        
        return {
            "active_ip_count": active_ip_count,
            "total_records": total_records,
            "time_range": {
                "start_time": start_time,
                "end_time": end_time
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取监控汇总信息失败: {str(e)}")