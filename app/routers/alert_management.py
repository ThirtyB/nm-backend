from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, and_, or_
from app.database import get_db
from app.models import AlertRule, NodeMonitorMetrics
from app.schemas import AlertRuleCreate, AlertRuleUpdate, AlertRuleResponse, AlertInfo, AlertsResponse, AlertQueryParams
from app.auth import get_current_user, User, get_admin_user

router = APIRouter(
    prefix="/alert-management",
    tags=["告警管理"],
    responses={404: {"description": "Not found"}},
)

class AlertRuleEngine:
    """告警规则引擎"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_latest_metrics(self, ip: str) -> Optional[NodeMonitorMetrics]:
        """获取指定IP的最新监控数据"""
        query = text("""
            SELECT * FROM node_monitor_metrics 
            WHERE ip = :ip 
            ORDER BY ts DESC 
            LIMIT 1
        """)
        result = self.db.execute(query, {"ip": ip})
        row = result.fetchone()
        if row:
            return NodeMonitorMetrics(**row._asdict())
        return None
    
    def calculate_derived_metrics(self, metrics: NodeMonitorMetrics) -> Dict[str, float]:
        """计算衍生指标"""
        derived = {}
        
        # CPU使用率
        if metrics.cpu_usr is not None and metrics.cpu_sys is not None and metrics.cpu_iow is not None:
            derived["cpu_usage_rate"] = round(metrics.cpu_usr + metrics.cpu_sys + metrics.cpu_iow, 2)
        
        # 内存使用率
        if metrics.mem_total is not None and metrics.mem_total > 0:
            if metrics.mem_free is not None and metrics.mem_buff is not None and metrics.mem_cache is not None:
                used = metrics.mem_total - metrics.mem_free - metrics.mem_buff - metrics.mem_cache
                derived["memory_usage_rate"] = round((used / metrics.mem_total) * 100, 2)
        
        # Swap使用率
        if metrics.swap_total is not None and metrics.swap_total > 0 and metrics.swap_used is not None:
            derived["swap_usage_rate"] = round((metrics.swap_used / metrics.swap_total) * 100, 2)
        
        # 网络总速率
        if metrics.net_rx_kbps is not None and metrics.net_tx_kbps is not None:
            rx_rate = max(0, metrics.net_rx_kbps) if metrics.net_rx_kbps is not None else 0
            tx_rate = max(0, metrics.net_tx_kbps) if metrics.net_tx_kbps is not None else 0
            derived["network_rate"] = round(rx_rate + tx_rate, 2)
        
        return derived
    
    def get_field_value(self, metrics: NodeMonitorMetrics, field_name: str) -> Optional[float]:
        """获取字段值，支持衍生指标"""
        # 先尝试衍生指标
        derived = self.calculate_derived_metrics(metrics)
        if field_name in derived:
            return derived[field_name]
        
        # 尝试原始字段
        if hasattr(metrics, field_name):
            value = getattr(metrics, field_name)
            if value is not None:
                return float(value)
        
        return None
    
    def evaluate_condition(self, current_value: float, operator: str, threshold: float) -> bool:
        """评估条件"""
        if operator == ">":
            return current_value > threshold
        elif operator == "<":
            return current_value < threshold
        elif operator == ">=":
            return current_value >= threshold
        elif operator == "<=":
            return current_value <= threshold
        elif operator == "==":
            return current_value == threshold
        elif operator == "!=":
            return current_value != threshold
        return False
    
    def format_alert_message(self, template: str, ip: str, current_value: float, threshold: float, field_name: str) -> str:
        """格式化告警消息"""
        if not template:
            template = f"IP {ip} {field_name} 值 {current_value} {field_name} 阈值 {threshold}"
        
        return template.format(
            ip=ip,
            current_value=current_value,
            threshold=threshold,
            threshold_value=threshold,  # 添加 threshold_value 以兼容数据库中的模板
            field_name=field_name
        )
    
    def evaluate_rules_for_ip(self, ip: str) -> List[AlertInfo]:
        """评估指定IP的所有规则"""
        metrics = self.get_latest_metrics(ip)
        if not metrics:
            return []
        
        alerts = []
        current_time = int(datetime.now().timestamp())
        
        # 分别获取全局规则和该IP的个例规则
        global_rules_query = self.db.query(AlertRule).filter(
            AlertRule.is_active == True,
            AlertRule.rule_type == "global"
        ).order_by(AlertRule.id)
        
        specific_rules_query = self.db.query(AlertRule).filter(
            AlertRule.is_active == True,
            AlertRule.rule_type == "specific",
            AlertRule.target_ip == ip
        ).order_by(AlertRule.id)
        
        global_rules = global_rules_query.all()
        specific_rules = specific_rules_query.all()
        
        # 构建规则冲突检测字典
        # key: (alert_level, condition_field, condition_operator)
        # value: specific_rule
        specific_rule_override = {}
        for specific_rule in specific_rules:
            # 检查规则时间范围
            if specific_rule.time_range_start and current_time < specific_rule.time_range_start:
                continue
            if specific_rule.time_range_end and current_time > specific_rule.time_range_end:
                continue
            
            key = (specific_rule.alert_level, specific_rule.condition_field, specific_rule.condition_operator)
            specific_rule_override[key] = specific_rule
        
        # 处理全局规则，排除被个例规则覆盖的规则
        effective_rules = []
        for global_rule in global_rules:
            # 检查规则时间范围
            if global_rule.time_range_start and current_time < global_rule.time_range_start:
                continue
            if global_rule.time_range_end and current_time > global_rule.time_range_end:
                continue
            
            key = (global_rule.alert_level, global_rule.condition_field, global_rule.condition_operator)
            # 如果存在相同key的个例规则，跳过这个全局规则
            if key not in specific_rule_override:
                effective_rules.append(global_rule)
        
        # 添加所有个例规则
        for specific_rule in specific_rules:
            # 检查规则时间范围
            if specific_rule.time_range_start and current_time < specific_rule.time_range_start:
                continue
            if specific_rule.time_range_end and current_time > specific_rule.time_range_end:
                continue
            effective_rules.append(specific_rule)
        
        # 评估所有有效规则
        for rule in effective_rules:
            # 获取字段值
            field_value = self.get_field_value(metrics, rule.condition_field)
            if field_value is None:
                continue
            
            # 评估条件
            if self.evaluate_condition(field_value, rule.condition_operator, rule.condition_value):
                alert_message = self.format_alert_message(
                    rule.alert_message or "",
                    ip,
                    field_value,
                    rule.condition_value,
                    rule.condition_field
                )
                
                alert = AlertInfo(
                    ip=ip,
                    rule_id=rule.id,
                    rule_name=rule.rule_name,
                    alert_level=rule.alert_level,
                    alert_message=alert_message,
                    current_value=field_value,
                    threshold_value=rule.condition_value,
                    condition_field=rule.condition_field,
                    condition_operator=rule.condition_operator,
                    timestamp=metrics.ts,
                    rule_type=rule.rule_type
                )
                alerts.append(alert)
        
        return alerts
    
    def get_all_alerts(self, params: AlertQueryParams) -> AlertsResponse:
        """获取所有告警信息"""
        # 获取所有活跃IP
        active_ips_query = text("""
            SELECT DISTINCT ip FROM node_monitor_metrics 
            ORDER BY ip
        """)
        result = self.db.execute(active_ips_query)
        ips = [row[0] for row in result.fetchall()]
        
        # 如果指定了IP列表，进行过滤
        if params.ips:
            ips = [ip for ip in ips if ip in params.ips]
        
        all_alerts = []
        for ip in ips:
            alerts = self.evaluate_rules_for_ip(ip)
            all_alerts.extend(alerts)
        
        # 过滤告警级别
        if params.alert_levels:
            all_alerts = [alert for alert in all_alerts if alert.alert_level in params.alert_levels]
        
        # 过滤规则类型
        if params.rule_types:
            all_alerts = [alert for alert in all_alerts if alert.rule_type in params.rule_types]
        
        return AlertsResponse(
            alerts=all_alerts,
            total_count=len(all_alerts),
            query_time=datetime.now()
        )
    
    def get_all_alerts_with_time_range(self, start_time: int, end_time: int, 
                                     ips: Optional[List[str]] = None,
                                     alert_levels: Optional[List[str]] = None,
                                     rule_types: Optional[List[str]] = None) -> AlertsResponse:
        """获取指定时间段内的所有告警信息"""
        # 获取指定时间段内有监控数据的IP
        active_ips_query = text("""
            SELECT DISTINCT ip FROM node_monitor_metrics 
            WHERE ts BETWEEN :start_time AND :end_time
            ORDER BY ip
        """)
        result = self.db.execute(active_ips_query, {
            "start_time": start_time,
            "end_time": end_time
        })
        time_range_ips = [row[0] for row in result.fetchall()]
        
        # 如果指定了IP列表，进行过滤
        if ips:
            time_range_ips = [ip for ip in time_range_ips if ip in ips]
        
        all_alerts = []
        for ip in time_range_ips:
            alerts = self.evaluate_rules_for_ip_with_time_range(ip, start_time, end_time)
            all_alerts.extend(alerts)
        
        # 过滤告警级别
        if alert_levels:
            all_alerts = [alert for alert in all_alerts if alert.alert_level in alert_levels]
        
        # 过滤规则类型
        if rule_types:
            all_alerts = [alert for alert in all_alerts if alert.rule_type in rule_types]
        
        return AlertsResponse(
            alerts=all_alerts,
            total_count=len(all_alerts),
            query_time=datetime.now()
        )
    
    def get_latest_metrics_in_time_range(self, ip: str, start_time: int, end_time: int) -> Optional[NodeMonitorMetrics]:
        """获取指定IP在时间段内的最新监控数据"""
        query = text("""
            SELECT * FROM node_monitor_metrics 
            WHERE ip = :ip AND ts BETWEEN :start_time AND :end_time
            ORDER BY ts DESC 
            LIMIT 1
        """)
        result = self.db.execute(query, {
            "ip": ip,
            "start_time": start_time,
            "end_time": end_time
        })
        row = result.fetchone()
        if row:
            return NodeMonitorMetrics(**row._asdict())
        return None
    
    def evaluate_rules_for_ip_with_time_range(self, ip: str, start_time: int, end_time: int) -> List[AlertInfo]:
        """评估指定IP在时间段内的所有规则"""
        metrics = self.get_latest_metrics_in_time_range(ip, start_time, end_time)
        if not metrics:
            return []
        
        alerts = []
        current_time = int(datetime.now().timestamp())
        
        # 分别获取全局规则和该IP的个例规则
        global_rules_query = self.db.query(AlertRule).filter(
            AlertRule.is_active == True,
            AlertRule.rule_type == "global"
        ).order_by(AlertRule.id)
        
        specific_rules_query = self.db.query(AlertRule).filter(
            AlertRule.is_active == True,
            AlertRule.rule_type == "specific",
            AlertRule.target_ip == ip
        ).order_by(AlertRule.id)
        
        global_rules = global_rules_query.all()
        specific_rules = specific_rules_query.all()
        
        # 构建规则冲突检测字典
        # key: (alert_level, condition_field, condition_operator)
        # value: specific_rule
        specific_rule_override = {}
        for specific_rule in specific_rules:
            # 检查规则时间范围
            if specific_rule.time_range_start and current_time < specific_rule.time_range_start:
                continue
            if specific_rule.time_range_end and current_time > specific_rule.time_range_end:
                continue
            
            key = (specific_rule.alert_level, specific_rule.condition_field, specific_rule.condition_operator)
            specific_rule_override[key] = specific_rule
        
        # 处理全局规则，排除被个例规则覆盖的规则
        effective_rules = []
        for global_rule in global_rules:
            # 检查规则时间范围
            if global_rule.time_range_start and current_time < global_rule.time_range_start:
                continue
            if global_rule.time_range_end and current_time > global_rule.time_range_end:
                continue
            
            key = (global_rule.alert_level, global_rule.condition_field, global_rule.condition_operator)
            # 如果存在相同key的个例规则，跳过这个全局规则
            if key not in specific_rule_override:
                effective_rules.append(global_rule)
        
        # 添加所有个例规则
        for specific_rule in specific_rules:
            # 检查规则时间范围
            if specific_rule.time_range_start and current_time < specific_rule.time_range_start:
                continue
            if specific_rule.time_range_end and current_time > specific_rule.time_range_end:
                continue
            effective_rules.append(specific_rule)
        
        # 评估所有有效规则
        for rule in effective_rules:
            # 获取字段值
            field_value = self.get_field_value(metrics, rule.condition_field)
            if field_value is None:
                continue
            
            # 评估条件
            if self.evaluate_condition(field_value, rule.condition_operator, rule.condition_value):
                alert_message = self.format_alert_message(
                    rule.alert_message or "",
                    ip,
                    field_value,
                    rule.condition_value,
                    rule.condition_field
                )
                
                alert = AlertInfo(
                    ip=ip,
                    rule_id=rule.id,
                    rule_name=rule.rule_name,
                    alert_level=rule.alert_level,
                    alert_message=alert_message,
                    current_value=field_value,
                    threshold_value=rule.condition_value,
                    condition_field=rule.condition_field,
                    condition_operator=rule.condition_operator,
                    timestamp=metrics.ts,
                    rule_type=rule.rule_type
                )
                alerts.append(alert)
        
        return alerts

# 规则管理API（仅管理员）
@router.post("/rules", response_model=AlertRuleResponse)
async def create_alert_rule(
    rule: AlertRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    创建告警规则（仅管理员）
    
    请求参数：
    - rule_name: 规则名称（必填，字符串，最大100字符）
    - rule_type: 规则类型（必填，"global"全局或"specific"个例）
    - target_ip: 目标IP（个例规则必填，全局规则必须为空）
    - condition_field: 监控字段（必填，支持以下字段）
      * 衍生指标：cpu_usage_rate, memory_usage_rate, swap_usage_rate, network_rate
      * CPU相关：cpu_usr, cpu_sys, cpu_iow
      * 内存相关：mem_total, mem_free, mem_buff, mem_cache
      * Swap相关：swap_total, swap_used, swap_in, swap_out
      * 磁盘相关：disk_used_percent, disk_iops, disk_r, disk_w, disk_total, disk_used
      * 网络相关：net_rx_kbps, net_tx_kbps, net_rx_kbytes, net_tx_kbytes
      * 系统相关：system_in, system_cs
    - condition_operator: 比较操作符（必填，支持>, <, >=, <=, ==, !=）
    - condition_value: 阈值（必填，浮点数）
    - time_range_start: 生效开始时间（可选，Unix时间戳）
    - time_range_end: 生效结束时间（可选，Unix时间戳）
    - alert_level: 告警级别（可选，"info", "warning", "error", "critical"，默认"warning"）
    - alert_message: 告警消息模板（可选，支持{ip}, {current_value}, {threshold_value}, {field_name}变量）
    - is_active: 是否激活（可选，布尔值，默认true）
    
    返回参数：
    - id: 规则ID
    - rule_name: 规则名称
    - rule_type: 规则类型
    - target_ip: 目标IP
    - condition_field: 监控字段
    - condition_operator: 比较操作符
    - condition_value: 阈值
    - time_range_start: 生效开始时间
    - time_range_end: 生效结束时间
    - alert_level: 告警级别
    - alert_message: 告警消息模板
    - is_active: 是否激活
    - created_at: 创建时间
    - updated_at: 更新时间
    """
    try:
        # 验证个例规则必须有target_ip
        if rule.rule_type == "specific" and not rule.target_ip:
            raise HTTPException(status_code=400, detail="个例规则必须指定target_ip")
        
        # 验证全局规则不能有target_ip
        if rule.rule_type == "global" and rule.target_ip:
            raise HTTPException(status_code=400, detail="全局规则不能指定target_ip")
        
        db_rule = AlertRule(**rule.dict())
        db.add(db_rule)
        db.commit()
        db.refresh(db_rule)
        
        return db_rule
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建规则失败: {str(e)}")

@router.get("/rules", response_model=List[AlertRuleResponse])
async def get_alert_rules(
    rule_type: Optional[str] = Query(None, description="规则类型过滤"),
    is_active: Optional[bool] = Query(None, description="是否激活过滤"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    获取所有告警规则（仅管理员）
    
    查询参数：
    - rule_type: 规则类型过滤（可选，"global"或"specific"）
    - is_active: 是否激活过滤（可选，true或false）
    
    返回参数：
    返回AlertRuleResponse对象列表，每个对象包含：
    - id: 规则ID
    - rule_name: 规则名称
    - rule_type: 规则类型
    - target_ip: 目标IP
    - condition_field: 监控字段
    - condition_operator: 比较操作符
    - condition_value: 阈值
    - time_range_start: 生效开始时间
    - time_range_end: 生效结束时间
    - alert_level: 告警级别
    - alert_message: 告警消息模板
    - is_active: 是否激活
    - created_at: 创建时间
    - updated_at: 更新时间
    """
    try:
        query = db.query(AlertRule)
        
        if rule_type:
            query = query.filter(AlertRule.rule_type == rule_type)
        
        if is_active is not None:
            query = query.filter(AlertRule.is_active == is_active)
        
        rules = query.order_by(AlertRule.rule_type.desc(), AlertRule.id).all()
        return rules
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询规则失败: {str(e)}")

@router.get("/rules/{rule_id}", response_model=AlertRuleResponse)
async def get_alert_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    获取特定告警规则（仅管理员）
    
    路径参数：
    - rule_id: 规则ID（必填，整数）
    
    返回参数：
    返回AlertRuleResponse对象，包含：
    - id: 规则ID
    - rule_name: 规则名称
    - rule_type: 规则类型
    - target_ip: 目标IP
    - condition_field: 监控字段
    - condition_operator: 比较操作符
    - condition_value: 阈值
    - time_range_start: 生效开始时间
    - time_range_end: 生效结束时间
    - alert_level: 告警级别
    - alert_message: 告警消息模板
    - is_active: 是否激活
    - created_at: 创建时间
    - updated_at: 更新时间
    
    错误码：
    - 404: 规则不存在
    """
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    return rule

@router.put("/rules/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(
    rule_id: int,
    rule_update: AlertRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    更新告警规则（仅管理员）
    
    路径参数：
    - rule_id: 规则ID（必填，整数）
    
    请求参数：
    - rule_name: 规则名称（可选，字符串）
    - rule_type: 规则类型（可选，"global"或"specific"）
    - target_ip: 目标IP（可选，字符串）
    - condition_field: 监控字段（可选，字符串）
    - condition_operator: 比较操作符（可选，">", "<", ">=", "<=", "==", "!="）
    - condition_value: 阈值（可选，浮点数）
    - time_range_start: 生效开始时间（可选，Unix时间戳）
    - time_range_end: 生效结束时间（可选，Unix时间戳）
    - alert_level: 告警级别（可选，"info", "warning", "error", "critical"）
    - alert_message: 告警消息模板（可选，字符串）
    - is_active: 是否激活（可选，布尔值）
    
    返回参数：
    返回更新后的AlertRuleResponse对象，包含所有规则信息
    
    错误码：
    - 400: 规则类型与target_ip不匹配
    - 404: 规则不存在
    """
    try:
        db_rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
        if not db_rule:
            raise HTTPException(status_code=404, detail="规则不存在")
        
        update_data = rule_update.dict(exclude_unset=True)
        
        # 验证rule_type和target_ip的一致性
        if "rule_type" in update_data:
            if update_data["rule_type"] == "specific" and not update_data.get("target_ip", db_rule.target_ip):
                raise HTTPException(status_code=400, detail="个例规则必须指定target_ip")
            if update_data["rule_type"] == "global" and update_data.get("target_ip", db_rule.target_ip):
                raise HTTPException(status_code=400, detail="全局规则不能指定target_ip")
        
        for field, value in update_data.items():
            setattr(db_rule, field, value)
        
        db.commit()
        db.refresh(db_rule)
        return db_rule
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新规则失败: {str(e)}")

@router.delete("/rules/{rule_id}")
async def delete_alert_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    删除告警规则（仅管理员）
    
    路径参数：
    - rule_id: 规则ID（必填，整数）
    
    返回参数：
    - message: 删除成功消息
    
    错误码：
    - 404: 规则不存在
    """
    try:
        db_rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
        if not db_rule:
            raise HTTPException(status_code=404, detail="规则不存在")
        
        db.delete(db_rule)
        db.commit()
        return {"message": "规则删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除规则失败: {str(e)}")

# 告警查询API（所有认证用户）
@router.get("/alerts", response_model=AlertsResponse)
async def get_alerts(
    start_time: int = Query(..., description="开始时间戳"),
    end_time: int = Query(..., description="结束时间戳"),
    ips: Optional[str] = Query(None, description="指定IP列表，逗号分隔"),
    alert_levels: Optional[str] = Query(None, description="告警级别过滤，逗号分隔"),
    rule_types: Optional[str] = Query(None, description="规则类型过滤，逗号分隔"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取告警信息（所有认证用户）
    
    查询参数：
    - start_time: 开始时间戳（必填，Unix时间戳）
    - end_time: 结束时间戳（必填，Unix时间戳）
    - ips: 指定IP列表（可选，逗号分隔的IP地址字符串）
    - alert_levels: 告警级别过滤（可选，逗号分隔的级别："info", "warning", "error", "critical"）
    - rule_types: 规则类型过滤（可选，逗号分隔的类型："global", "specific"）
    
    返回参数：
    - alerts: 告警信息列表，每个告警包含：
      - ip: IP地址
      - rule_id: 规则ID
      - rule_name: 规则名称
      - alert_level: 告警级别
      - alert_message: 告警消息
      - current_value: 当前值
      - threshold_value: 阈值
      - condition_field: 监控字段
      - condition_operator: 比较操作符
      - timestamp: 数据时间戳
      - rule_type: 规则类型
    - total_count: 告警总数
    - query_time: 查询时间
    
    说明：
    - 实时生成告警信息，不存储在数据库中
    - 只查询指定时间段内有监控数据的机器
    - 基于每个IP在时间段内的最新监控数据进行规则匹配
    - 个例规则优先级高于全局规则
    """
    try:
        # 解析查询参数
        ip_list = None
        if ips:
            ip_list = [ip.strip() for ip in ips.split(",") if ip.strip()]
        
        level_list = None
        if alert_levels:
            level_list = [level.strip() for level in alert_levels.split(",") if level.strip()]
        
        type_list = None
        if rule_types:
            type_list = [t.strip() for t in rule_types.split(",") if t.strip()]
        
        engine = AlertRuleEngine(db)
        return engine.get_all_alerts_with_time_range(
            start_time=start_time,
            end_time=end_time,
            ips=ip_list,
            alert_levels=level_list,
            rule_types=type_list
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询告警失败: {str(e)}")

@router.get("/alerts/{ip}", response_model=AlertsResponse)
async def get_ip_alerts(
    ip: str,
    start_time: int = Query(..., description="开始时间戳"),
    end_time: int = Query(..., description="结束时间戳"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取特定IP的告警信息（所有认证用户）
    
    路径参数：
    - ip: IP地址（必填，字符串）
    
    查询参数：
    - start_time: 开始时间戳（必填，Unix时间戳）
    - end_time: 结束时间戳（必填，Unix时间戳）
    
    返回参数：
    - alerts: 该IP的告警信息列表，每个告警包含：
      - ip: IP地址
      - rule_id: 规则ID
      - rule_name: 规则名称
      - alert_level: 告警级别
      - alert_message: 告警消息
      - current_value: 当前值
      - threshold_value: 阈值
      - condition_field: 监控字段
      - condition_operator: 比较操作符
      - timestamp: 数据时间戳
      - rule_type: 规则类型
    - total_count: 告警总数
    - query_time: 查询时间
    
    说明：
    - 实时生成告警信息，不存储在数据库中
    - 基于该IP在指定时间段内的最新监控数据进行规则匹配
    - 如果该IP在时间段内没有监控数据，返回空告警列表
    """
    try:
        engine = AlertRuleEngine(db)
        alerts = engine.evaluate_rules_for_ip_with_time_range(ip, start_time, end_time)
        
        return AlertsResponse(
            alerts=alerts,
            total_count=len(alerts),
            query_time=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询IP告警失败: {str(e)}")