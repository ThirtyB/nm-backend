from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import MachineScore, DimensionScore, ScoreQueryParams, ScoreResponse
from app.auth import get_current_user, User
from app.routers.alert_management import AlertRuleEngine, AlertInfo
from app.cache import cache, CacheTTL, cache_key
from app.decorators import cached

router = APIRouter(
    prefix="/scoring",
    tags=["评分系统"],
    responses={404: {"description": "Not found"}},
)

class AlertScoringEngine:
    """告警评分引擎"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_dimension_for_field(self, field_name: str) -> str:
        """根据字段名确定所属维度"""
        cpu_fields = ["cpu_usr", "cpu_sys", "cpu_iow", "cpu_usage_rate", "system_in", "system_cs"]
        memory_fields = ["mem_total", "mem_free", "mem_buff", "mem_cache", "memory_usage_rate"]
        disk_fields = ["disk_total", "disk_used", "disk_used_percent", "disk_iops", "disk_r", "disk_w"]
        network_fields = ["net_rx_kbps", "net_tx_kbps", "net_rx_kbytes", "net_tx_kbytes", "network_rate"]
        swap_fields = ["swap_total", "swap_used", "swap_in", "swap_out", "swap_usage_rate"]
        
        if field_name in cpu_fields:
            return "CPU"
        elif field_name in memory_fields:
            return "内存"
        elif field_name in disk_fields:
            return "磁盘"
        elif field_name in network_fields:
            return "网络"
        elif field_name in swap_fields:
            return "Swap"
        else:
            return "其他"
    
    def get_deduction_for_alert_level(self, alert_level: str) -> float:
        """根据告警级别获取扣分数值"""
        deduction_map = {
            "info": 5,      # 轻微告警扣5分
            "warning": 10,  # 警告扣10分
            "error": 20,    # 错误扣20分
            "critical": 40  # 严重告警扣40分
        }
        return deduction_map.get(alert_level, 0)
    
    def calculate_dimension_score(self, alerts: List[AlertInfo], dimension: str, include_details: bool = True) -> DimensionScore:
        """计算单个维度分数"""
        dimension_alerts = [alert for alert in alerts if self.get_dimension_for_field(alert.condition_field) == dimension]
        
        # 计算总扣分
        total_deduction = 0
        deductions = []
        
        for alert in dimension_alerts:
            deduction = self.get_deduction_for_alert_level(alert.alert_level)
            total_deduction += deduction
            
            if include_details:
                deductions.append({
                    "rule_name": alert.rule_name,
                    "alert_level": alert.alert_level,
                    "alert_message": alert.alert_message,
                    "current_value": alert.current_value,
                    "threshold_value": alert.threshold_value,
                    "deduction": deduction
                })
        
        # 计算分数（100分减去总扣分，最低0分）
        score = max(0, 100 - total_deduction)
        
        return DimensionScore(
            name=dimension,
            score=round(score, 2),
            alert_count=len(dimension_alerts),
            deductions=deductions if include_details else []
        )
    
    def calculate_machine_score(self, ip: str, start_time: int, end_time: int, include_details: bool = True) -> Optional[MachineScore]:
        """计算单个机器的评分"""
        # 获取该机器在指定时间范围内的告警
        alert_engine = AlertRuleEngine(self.db)
        alerts = alert_engine.evaluate_rules_for_ip_with_time_range(ip, start_time, end_time)
        
        if not alerts:
            # 如果没有告警，所有维度都是满分
            dimensions = {
                "CPU": DimensionScore(name="CPU", score=100.0, alert_count=0, deductions=[]),
                "内存": DimensionScore(name="内存", score=100.0, alert_count=0, deductions=[]),
                "磁盘": DimensionScore(name="磁盘", score=100.0, alert_count=0, deductions=[]),
                "网络": DimensionScore(name="网络", score=100.0, alert_count=0, deductions=[]),
                "Swap": DimensionScore(name="Swap", score=100.0, alert_count=0, deductions=[])
            }
            return MachineScore(
                ip=ip,
                total_score=100.0,
                dimensions=dimensions,
                evaluation_time=datetime.now()
            )
        
        # 计算各维度分数
        dimensions = {}
        all_dimensions = ["CPU", "内存", "磁盘", "网络", "Swap"]
        
        for dimension in all_dimensions:
            dimensions[dimension] = self.calculate_dimension_score(alerts, dimension, include_details)
        
        # 计算总分（各维度分数的平均值）
        total_score = sum(dim.score for dim in dimensions.values()) / len(dimensions)
        
        return MachineScore(
            ip=ip,
            total_score=round(total_score, 2),
            dimensions=dimensions,
            evaluation_time=datetime.now()
        )
    
    def get_all_scores(self, params: ScoreQueryParams) -> ScoreResponse:
        """获取所有机器的评分"""
        # 获取指定时间段内有监控数据的IP
        from sqlalchemy import text
        active_ips_query = text("""
            SELECT DISTINCT ip FROM node_monitor_metrics 
            WHERE ts BETWEEN :start_time AND :end_time
            ORDER BY ip
        """)
        result = self.db.execute(active_ips_query, {
            "start_time": params.start_time,
            "end_time": params.end_time
        })
        ips = [row[0] for row in result.fetchall()]
        
        # 如果指定了IP列表，进行过滤
        if params.ips:
            ips = [ip for ip in ips if ip in params.ips]
        
        # 计算每个机器的评分
        scores = []
        for ip in ips:
            machine_score = self.calculate_machine_score(
                ip, params.start_time, params.end_time, params.include_details
            )
            if machine_score:
                scores.append(machine_score)
        
        return ScoreResponse(
            scores=scores,
            total_count=len(scores),
            query_time=datetime.now()
        )

def machine_scores_cache_key(start_time: int, end_time: int, ips: Optional[str], include_details: bool) -> str:
    """生成机器评分缓存键"""
    ips_str = ips or "all"
    details_str = str(include_details)
    return cache_key("scoring", "machines", start_time, end_time, ips_str, details_str)

@router.get("/machines", response_model=ScoreResponse)
@cached(ttl_seconds=CacheTTL.ONE_MINUTE, key_func=machine_scores_cache_key)
async def get_machine_scores(
    start_time: int = Query(..., description="开始时间戳"),
    end_time: int = Query(..., description="结束时间戳"),
    ips: Optional[str] = Query(None, description="指定IP列表，逗号分隔"),
    include_details: bool = Query(True, description="是否包含详细扣分信息"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取机器评分（所有认证用户）
    
    查询参数：
    - start_time: 开始时间戳（必填，Unix时间戳）
    - end_time: 结束时间戳（必填，Unix时间戳）
    - ips: 指定IP列表（可选，逗号分隔的IP地址字符串）
    - include_details: 是否包含详细扣分信息（可选，默认true）
    
    返回参数：
    - scores: 机器评分列表，每个评分包含：
      - ip: IP地址
      - total_score: 总分(0-100)
      - dimensions: 各维度分数字典，包含：
        - CPU: CPU维度分数
        - 内存: 内存维度分数
        - 磁盘: 磁盘维度分数
        - 网络: 网络维度分数
        - Swap: Swap维度分数
        每个维度包含：
        - name: 维度名称
        - score: 分数(0-100)
        - alert_count: 告警数量
        - deductions: 扣分详情列表（当include_details=true时）
      - evaluation_time: 评估时间
    - total_count: 机器总数
    - query_time: 查询时间
    
    评分规则：
    - 初始分数：100分
    - 扣分规则：
      * info级别告警：扣5分
      * warning级别告警：扣10分
      * error级别告警：扣20分
      * critical级别告警：扣40分
    - 维度划分：
      * CPU：cpu_usr, cpu_sys, cpu_iow, cpu_usage_rate, system_in, system_cs
      * 内存：mem_total, mem_free, mem_buff, mem_cache, memory_usage_rate
      * 磁盘：disk_total, disk_used, disk_used_percent, disk_iops, disk_r, disk_w
      * 网络：net_rx_kbps, net_tx_kbps, net_rx_kbytes, net_tx_kbytes, network_rate
      * Swap：swap_total, swap_used, swap_in, swap_out, swap_usage_rate
    - 总分计算：各维度分数的平均值
    
    说明：
    - 实时计算评分，不存储在数据库中
    - 基于指定时间段内的监控数据和告警规则进行评估
    - 只查询指定时间段内有监控数据的机器
    - 无告警的机器各维度均为100分，总分100分
    """
    try:
        # 解析查询参数
        ip_list = None
        if ips:
            ip_list = [ip.strip() for ip in ips.split(",") if ip.strip()]
        
        params = ScoreQueryParams(
            start_time=start_time,
            end_time=end_time,
            ips=ip_list,
            include_details=include_details
        )
        
        engine = AlertScoringEngine(db)
        return engine.get_all_scores(params)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询评分失败: {str(e)}")

def machine_score_cache_key(ip: str, start_time: int, end_time: int, include_details: bool) -> str:
    """生成单个机器评分缓存键"""
    details_str = str(include_details)
    return cache_key("scoring", "machine", ip, start_time, end_time, details_str)

@router.get("/machines/{ip}", response_model=MachineScore)
@cached(ttl_seconds=CacheTTL.ONE_MINUTE, key_func=machine_score_cache_key)
async def get_machine_score(
    ip: str,
    start_time: int = Query(..., description="开始时间戳"),
    end_time: int = Query(..., description="结束时间戳"),
    include_details: bool = Query(True, description="是否包含详细扣分信息"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取特定机器的评分（所有认证用户）
    
    路径参数：
    - ip: IP地址（必填，字符串）
    
    查询参数：
    - start_time: 开始时间戳（必填，Unix时间戳）
    - end_time: 结束时间戳（必填，Unix时间戳）
    - include_details: 是否包含详细扣分信息（可选，默认true）
    
    返回参数：
    - ip: IP地址
    - total_score: 总分(0-100)
    - dimensions: 各维度分数字典
    - evaluation_time: 评估时间
    
    错误码：
    - 404: 机器不存在或指定时间段内无监控数据
    """
    try:
        engine = AlertScoringEngine(db)
        machine_score = engine.calculate_machine_score(ip, start_time, end_time, include_details)
        
        if not machine_score:
            raise HTTPException(status_code=404, detail=f"机器 {ip} 不存在或指定时间段内无监控数据")
        
        return machine_score
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询机器评分失败: {str(e)}")

def scoring_summary_cache_key(start_time: int, end_time: int, ips: Optional[str]) -> str:
    """生成评分汇总缓存键"""
    ips_str = ips or "all"
    return cache_key("scoring", "summary", start_time, end_time, ips_str)

@router.get("/summary")
@cached(ttl_seconds=CacheTTL.ONE_MINUTE, key_func=scoring_summary_cache_key)
async def get_scoring_summary(
    start_time: int = Query(..., description="开始时间戳"),
    end_time: int = Query(..., description="结束时间戳"),
    ips: Optional[str] = Query(None, description="指定IP列表，逗号分隔"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取评分汇总统计（所有认证用户）
    
    查询参数：
    - start_time: 开始时间戳（必填，Unix时间戳）
    - end_time: 结束时间戳（必填，Unix时间戳）
    - ips: 指定IP列表（可选，逗号分隔的IP地址字符串）
    
    返回参数：
    - total_machines: 机器总数
    - average_score: 平均总分
    - dimension_averages: 各维度平均分
    - score_distribution: 分数分布统计
    - alert_distribution: 告警分布统计
    - query_time: 查询时间
    """
    try:
        # 解析查询参数
        ip_list = None
        if ips:
            ip_list = [ip.strip() for ip in ips.split(",") if ip.strip()]
        
        params = ScoreQueryParams(
            start_time=start_time,
            end_time=end_time,
            ips=ip_list,
            include_details=False  # 汇总不需要详细信息
        )
        
        engine = AlertScoringEngine(db)
        score_response = engine.get_all_scores(params)
        scores = score_response.scores
        
        if not scores:
            return {
                "total_machines": 0,
                "average_score": 0,
                "dimension_averages": {},
                "score_distribution": {},
                "alert_distribution": {},
                "query_time": datetime.now()
            }
        
        # 计算平均总分
        total_score = sum(score.total_score for score in scores)
        average_score = round(total_score / len(scores), 2)
        
        # 计算各维度平均分
        dimension_totals = {}
        for dimension in ["CPU", "内存", "磁盘", "网络", "Swap"]:
            dimension_total = sum(score.dimensions[dimension].score for score in scores)
            dimension_totals[dimension] = round(dimension_total / len(scores), 2)
        
        # 分数分布统计
        score_ranges = {
            "90-100": 0,
            "80-89": 0,
            "70-79": 0,
            "60-69": 0,
            "50-59": 0,
            "0-49": 0
        }
        
        for score in scores:
            if score.total_score >= 90:
                score_ranges["90-100"] += 1
            elif score.total_score >= 80:
                score_ranges["80-89"] += 1
            elif score.total_score >= 70:
                score_ranges["70-79"] += 1
            elif score.total_score >= 60:
                score_ranges["60-69"] += 1
            elif score.total_score >= 50:
                score_ranges["50-59"] += 1
            else:
                score_ranges["0-49"] += 1
        
        # 告警分布统计
        alert_distribution = {
            "total_alerts": 0,
            "by_level": {"info": 0, "warning": 0, "error": 0, "critical": 0},
            "by_dimension": {"CPU": 0, "内存": 0, "磁盘": 0, "网络": 0, "Swap": 0}
        }
        
        for score in scores:
            for dimension in score.dimensions.values():
                alert_distribution["total_alerts"] += dimension.alert_count
                alert_distribution["by_dimension"][dimension.name] += dimension.alert_count
        
        return {
            "total_machines": len(scores),
            "average_score": average_score,
            "dimension_averages": dimension_totals,
            "score_distribution": score_ranges,
            "alert_distribution": alert_distribution,
            "query_time": datetime.now()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询评分汇总失败: {str(e)}")