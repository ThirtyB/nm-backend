from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from app.database import get_db
from app.models import NodeMonitorMetrics
from app.schemas import ActiveIPsResponse, NodeLatestMetrics, NodeMetricsResponse, IPMetricsRequest, TimeRangeParams, UsageTopRequest, UsageTopResponse, DimensionUsage
from app.auth import get_current_user, User
from app.cache import cache, CacheTTL, cache_key
from app.decorators import cached

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
    if mem_free is None:
        return None
    # 使用公式：1 - free/total
    return round((1 - mem_free / mem_total) * 100, 2)

def calculate_swap_usage(swap_total: Optional[int], swap_used: Optional[int]) -> Optional[float]:
    """计算Swap使用率"""
    if swap_total is None or swap_total == 0 or swap_used is None:
        return None
    return round((swap_used / swap_total) * 100, 2)

def calculate_network_rate(net_rx_kbps: Optional[float], net_tx_kbps: Optional[float]) -> Optional[float]:
    """计算网络速率（总速率）"""
    if net_rx_kbps is None or net_tx_kbps is None:
        return None
    
    # 处理负数情况：将负数视为0
    rx_rate = max(0, net_rx_kbps) if net_rx_kbps is not None else 0
    tx_rate = max(0, net_tx_kbps) if net_tx_kbps is not None else 0
    
    return round(rx_rate + tx_rate, 2)

def clean_network_data(net_rx_kbps: Optional[float], net_tx_kbps: Optional[float]) -> tuple:
    """清理网络数据，处理负数"""
    clean_rx = max(0, net_rx_kbps) if net_rx_kbps is not None and net_rx_kbps >= 0 else 0
    clean_tx = max(0, net_tx_kbps) if net_tx_kbps is not None and net_tx_kbps >= 0 else 0
    return clean_rx, clean_tx

def active_ips_cache_key(start_time: int, end_time: int) -> str:
    """生成活跃IP缓存键"""
    return cache_key("node_monitor", "active_ips", start_time, end_time)

@router.get("/active-ips", response_model=ActiveIPsResponse)
@cached(ttl_seconds=CacheTTL.ONE_MINUTE, key_func=active_ips_cache_key)
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

def ip_metrics_cache_key(ip: str, start_time: int, end_time: int) -> str:
    """生成IP指标缓存键"""
    return cache_key("node_monitor", "ip_metrics", ip, start_time, end_time)

@router.get("/ip-metrics/{ip}", response_model=List[NodeMetricsResponse])
@cached(ttl_seconds=CacheTTL.TEN_MINUTES, key_func=ip_metrics_cache_key)
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
        
        # 清理网络数据中的负数
        cleaned_metrics = []
        for metric in metrics:
            clean_rx, clean_tx = clean_network_data(metric.net_rx_kbps, metric.net_tx_kbps)
            # 创建新的对象，保持其他字段不变
            cleaned_metric = NodeMetricsResponse(
                id=metric.id,
                ip=metric.ip,
                ts=metric.ts,
                cpu_usr=metric.cpu_usr,
                cpu_sys=metric.cpu_sys,
                cpu_iow=metric.cpu_iow,
                mem_total=metric.mem_total,
                mem_free=metric.mem_free,
                mem_buff=metric.mem_buff,
                mem_cache=metric.mem_cache,
                swap_total=metric.swap_total,
                swap_used=metric.swap_used,
                swap_in=metric.swap_in,
                swap_out=metric.swap_out,
                system_in=metric.system_in,
                system_cs=metric.system_cs,
                disk_name=metric.disk_name,
                disk_total=metric.disk_total,
                disk_used=metric.disk_used,
                disk_used_percent=metric.disk_used_percent,
                disk_iops=metric.disk_iops,
                disk_r=metric.disk_r,
                disk_w=metric.disk_w,
                net_rx_kbytes=metric.net_rx_kbytes,
                net_tx_kbytes=metric.net_tx_kbytes,
                net_rx_kbps=clean_rx,
                net_tx_kbps=clean_tx,
                version=metric.version,
                inserted_at=metric.inserted_at
            )
            cleaned_metrics.append(cleaned_metric)
        
        return cleaned_metrics
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询IP监控数据失败: {str(e)}")

def ip_metrics_body_cache_key(request: IPMetricsRequest) -> str:
    """生成IP指标POST请求缓存键"""
    return cache_key("node_monitor", "ip_metrics", request.ip, request.start_time, request.end_time)

@router.get("/ip-metrics", response_model=List[NodeMetricsResponse])
@cached(ttl_seconds=CacheTTL.TEN_MINUTES, key_func=ip_metrics_body_cache_key)
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
        
        # 清理网络数据中的负数
        cleaned_metrics = []
        for metric in metrics:
            clean_rx, clean_tx = clean_network_data(metric.net_rx_kbps, metric.net_tx_kbps)
            # 创建新的对象，保持其他字段不变
            cleaned_metric = NodeMetricsResponse(
                id=metric.id,
                ip=metric.ip,
                ts=metric.ts,
                cpu_usr=metric.cpu_usr,
                cpu_sys=metric.cpu_sys,
                cpu_iow=metric.cpu_iow,
                mem_total=metric.mem_total,
                mem_free=metric.mem_free,
                mem_buff=metric.mem_buff,
                mem_cache=metric.mem_cache,
                swap_total=metric.swap_total,
                swap_used=metric.swap_used,
                swap_in=metric.swap_in,
                swap_out=metric.swap_out,
                system_in=metric.system_in,
                system_cs=metric.system_cs,
                disk_name=metric.disk_name,
                disk_total=metric.disk_total,
                disk_used=metric.disk_used,
                disk_used_percent=metric.disk_used_percent,
                disk_iops=metric.disk_iops,
                disk_r=metric.disk_r,
                disk_w=metric.disk_w,
                net_rx_kbytes=metric.net_rx_kbytes,
                net_tx_kbytes=metric.net_tx_kbytes,
                net_rx_kbps=clean_rx,
                net_tx_kbps=clean_tx,
                version=metric.version,
                inserted_at=metric.inserted_at
            )
            cleaned_metrics.append(cleaned_metric)
        
        return cleaned_metrics
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询IP监控数据失败: {str(e)}")

def summary_cache_key(start_time: int, end_time: int) -> str:
    """生成监控汇总缓存键"""
    return cache_key("node_monitor", "summary", start_time, end_time)

@router.get("/summary")
@cached(ttl_seconds=CacheTTL.ONE_MINUTE, key_func=summary_cache_key)
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

def usage_top_cache_key(request: UsageTopRequest) -> str:
    """生成TOP使用率缓存键"""
    dimensions_str = ",".join(sorted(request.dimensions)) if request.dimensions else "all"
    return cache_key("node_monitor", "usage_top", request.start_time, request.end_time, request.top_count, dimensions_str)

@router.post("/usage-top", response_model=UsageTopResponse)
@cached(ttl_seconds=CacheTTL.FIVE_MINUTES, key_func=usage_top_cache_key)
async def get_usage_top(
    request: UsageTopRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取一段时间内五维使用率top数据（基于最新数据排序）及对应的时间序列
    
    输入参数：
    - start_time: 开始时间戳（Unix时间戳，必填）
    - end_time: 结束时间戳（Unix时间戳，必填）
    - top_count: 返回top数量，默认10（可选）
    - dimensions: 指定维度列表，可选值：["CPU", "内存", "磁盘", "网络", "Swap"]，默认全部维度
    
    输出格式：
    {
        "time_range": {
            "start_time": 1700000000,
            "end_time": 1700003600
        },
        "dimensions": {
            "CPU": {
                "name": "CPU",
                "unit": "%",
                "top_items": [
                    {
                        "ip": "192.168.1.100",
                        "usage_rate": 85.5,
                        "latest_timestamp": 1700003500,
                        "time_series": [
                            {"timestamp": 1700000000, "usage_rate": 80.2},
                            {"timestamp": 1700000100, "usage_rate": 82.1},
                            {"timestamp": 1700000200, "usage_rate": 85.5}
                        ]
                    }
                ]
            },
            "内存": {...},
            "磁盘": {...},
            "网络": {...},
            "Swap": {...}
        },
        "query_time": "2024-01-01T12:00:00"
    }
    
    说明：
    - 基于指定时间段内每个IP的最新监控数据计算使用率进行排序
    - 同时返回每个top IP在时间段内的完整使用率时间序列（按时间排序）
    - 网络使用率 = net_rx_kbps + net_tx_kbps（单位：kbps）
    - CPU使用率 = cpu_usr + cpu_sys + cpu_iow
    - 内存使用率 = (1 - mem_free / mem_total) * 100
    - Swap使用率 = swap_used / swap_total * 100
    - 磁盘使用率直接使用disk_used_percent字段
    """
    try:
        # 默认查询所有维度
        if not request.dimensions:
            request.dimensions = ["CPU", "内存", "磁盘", "网络", "Swap"]
        
        # 获取时间段内的所有监控数据
        all_data_query = text("""
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
                net_tx_kbps
            FROM node_monitor_metrics 
            WHERE ts BETWEEN :start_time AND :end_time
            ORDER BY ip, ts
        """)
        
        result = db.execute(all_data_query, {
            "start_time": request.start_time,
            "end_time": request.end_time
        })
        
        rows = result.fetchall()
        
        # 按IP分组数据
        ip_data = {}
        for row in rows:
            if row.ip not in ip_data:
                ip_data[row.ip] = []
            ip_data[row.ip].append(row)
        
        # 计算每个IP的最新使用率
        ip_latest_usage = {}
        for ip, data_rows in ip_data.items():
            # 获取最新记录
            latest_row = max(data_rows, key=lambda x: x.ts)
            
            ip_latest_usage[ip] = {
                "latest_timestamp": latest_row.ts,
                "cpu_usage": calculate_cpu_usage(latest_row.cpu_usr, latest_row.cpu_sys, latest_row.cpu_iow),
                "memory_usage": calculate_memory_usage(latest_row.mem_total, latest_row.mem_free, latest_row.mem_buff, latest_row.mem_cache),
                "disk_usage": round(latest_row.disk_used_percent, 2) if latest_row.disk_used_percent is not None else None,
                "network_usage": calculate_network_rate(latest_row.net_rx_kbps, latest_row.net_tx_kbps),
                "swap_usage": calculate_swap_usage(latest_row.swap_total, latest_row.swap_used),
                "all_data": data_rows
            }
        
        # 按维度计算使用率并排序
        dimension_data = {}
        for dimension in request.dimensions:
            dimension_data[dimension] = []
            
            for ip, usage_data in ip_latest_usage.items():
                # 正确的维度映射
                usage_key_map = {
                    "CPU": "cpu_usage",
                    "内存": "memory_usage", 
                    "磁盘": "disk_usage",
                    "网络": "network_usage",
                    "Swap": "swap_usage"
                }
                
                usage_key = usage_key_map.get(dimension)
                if usage_key and usage_data[usage_key] is not None:
                    dimension_data[dimension].append({
                        "ip": ip,
                        "usage_rate": usage_data[usage_key],
                        "latest_timestamp": usage_data["latest_timestamp"],
                        "all_data": usage_data["all_data"]
                    })
        
        # 对每个维度按使用率降序排序，取前top_count个
        result_dimensions = {}
        dimension_units = {
            "CPU": "%",
            "内存": "%", 
            "磁盘": "%",
            "网络": "kbps",
            "Swap": "%"
        }
        
        for dimension in request.dimensions:
            items = dimension_data[dimension]
            # 按使用率降序排序
            items.sort(key=lambda x: x["usage_rate"], reverse=True)
            # 取前top_count个
            top_items = items[:request.top_count]
            
            # 为每个top item生成时间序列
            top_items_with_series = []
            for item in top_items:
                # 生成时间序列数据
                time_series = []
                
                for data_row in item["all_data"]:
                    if dimension == "CPU":
                        usage = calculate_cpu_usage(data_row.cpu_usr, data_row.cpu_sys, data_row.cpu_iow)
                    elif dimension == "内存":
                        usage = calculate_memory_usage(data_row.mem_total, data_row.mem_free, data_row.mem_buff, data_row.mem_cache)
                    elif dimension == "磁盘":
                        usage = round(data_row.disk_used_percent, 2) if data_row.disk_used_percent is not None else None
                    elif dimension == "网络":
                        usage = calculate_network_rate(data_row.net_rx_kbps, data_row.net_tx_kbps)
                    elif dimension == "Swap":
                        usage = calculate_swap_usage(data_row.swap_total, data_row.swap_used)
                    else:
                        usage = None
                    
                    if usage is not None:
                        time_series.append({
                            "timestamp": data_row.ts,
                            "usage_rate": usage
                        })
                
                # 按时间戳排序时间序列
                time_series.sort(key=lambda x: x["timestamp"])
                
                top_items_with_series.append({
                    "ip": item["ip"],
                    "usage_rate": item["usage_rate"],
                    "latest_timestamp": item["latest_timestamp"],
                    "time_series": time_series
                })
            
            result_dimensions[dimension] = DimensionUsage(
                name=dimension,
                unit=dimension_units.get(dimension, "%"),
                top_items=top_items_with_series
            )
        
        return UsageTopResponse(
            time_range={
                "start_time": request.start_time,
                "end_time": request.end_time
            },
            dimensions=result_dimensions,
            query_time=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取使用率top数据失败: {str(e)}")