from pydantic import BaseModel, Field
from typing import Optional, Literal, List, Dict
from datetime import datetime

class UserBase(BaseModel):
    username: str
    user_type: Optional[Literal["admin", "user"]] = "user"
    is_active: bool = True

class UserCreate(BaseModel):
    username: str
    password: str

class AdminUserCreate(BaseModel):
    username: str
    password: str
    user_type: Literal["admin", "user"] = "user"

class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    user_type: Optional[Literal["admin", "user"]] = None
    is_active: Optional[bool] = None

class UserPartialUpdate(BaseModel):
    """部分更新用户信息，只更新提供的字段"""
    password: Optional[str] = None
    user_type: Optional[Literal["admin", "user"]] = None
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    id: int
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

# 节点监控相关schemas
class NodeMetricsBase(BaseModel):
    ip: str
    ts: int
    cpu_usr: Optional[float] = None
    cpu_sys: Optional[float] = None
    cpu_iow: Optional[float] = None
    mem_total: Optional[int] = None
    mem_free: Optional[int] = None
    mem_buff: Optional[int] = None
    mem_cache: Optional[int] = None
    swap_total: Optional[int] = None
    swap_used: Optional[int] = None
    swap_in: Optional[int] = None
    swap_out: Optional[int] = None
    system_in: Optional[int] = None
    system_cs: Optional[int] = None
    disk_name: Optional[str] = None
    disk_total: Optional[int] = None
    disk_used: Optional[int] = None
    disk_used_percent: Optional[float] = None
    disk_iops: Optional[int] = None
    disk_r: Optional[int] = None
    disk_w: Optional[int] = None
    net_rx_kbytes: Optional[float] = None
    net_tx_kbytes: Optional[float] = None
    net_rx_kbps: Optional[float] = None
    net_tx_kbps: Optional[float] = None
    version: Optional[str] = None

class NodeMetricsResponse(NodeMetricsBase):
    id: int
    inserted_at: datetime
    
    class Config:
        from_attributes = True

class NodeLatestMetrics(BaseModel):
    ip: str
    latest_ts: int
    cpu_usage_rate: Optional[float] = None
    disk_usage_rate: Optional[float] = None
    memory_usage_rate: Optional[float] = None
    swap_usage_rate: Optional[float] = None
    network_rate: Optional[float] = None

class ActiveIPsResponse(BaseModel):
    active_ips: list[NodeLatestMetrics]
    total_count: int
    time_range: dict

class TimeRangeParams(BaseModel):
    start_time: int = Field(..., description="开始时间戳")
    end_time: int = Field(..., description="结束时间戳")

class IPMetricsRequest(TimeRangeParams):
    ip: str = Field(..., description="IP地址")

# 告警管理相关schemas
class AlertRuleBase(BaseModel):
    rule_name: str = Field(..., description="规则名称")
    rule_type: Literal["global", "specific"] = Field(..., description="规则类型")
    target_ip: Optional[str] = Field(None, description="目标IP（个例规则必填）")
    condition_field: str = Field(..., description="监控字段")
    condition_operator: Literal[">", "<", ">=", "<=", "==", "!="] = Field(..., description="比较操作符")
    condition_value: float = Field(..., description="阈值")
    time_range_start: Optional[int] = Field(None, description="时间范围开始")
    time_range_end: Optional[int] = Field(None, description="时间范围结束")
    alert_level: Literal["info", "warning", "error", "critical"] = Field("warning", description="告警级别")
    alert_message: Optional[str] = Field(None, description="告警消息模板")
    is_active: bool = Field(True, description="是否激活")

class AlertRuleCreate(AlertRuleBase):
    pass

class AlertRuleUpdate(BaseModel):
    rule_name: Optional[str] = None
    rule_type: Optional[Literal["global", "specific"]] = None
    target_ip: Optional[str] = None
    condition_field: Optional[str] = None
    condition_operator: Optional[Literal[">", "<", ">=", "<=", "==", "!="]] = None
    condition_value: Optional[float] = None
    time_range_start: Optional[int] = None
    time_range_end: Optional[int] = None
    alert_level: Optional[Literal["info", "warning", "error", "critical"]] = None
    alert_message: Optional[str] = None
    is_active: Optional[bool] = None

class AlertRuleResponse(AlertRuleBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class AlertInfo(BaseModel):
    ip: str
    rule_id: int
    rule_name: str
    alert_level: str
    alert_message: str
    current_value: float
    threshold_value: float
    condition_field: str
    condition_operator: str
    timestamp: int
    rule_type: str  # "global" 或 "specific"

class AlertsResponse(BaseModel):
    alerts: List[AlertInfo]
    total_count: int
    query_time: datetime

class AlertQueryParams(BaseModel):
    ips: Optional[List[str]] = Field(None, description="指定IP列表，为空则查询所有IP")
    alert_levels: Optional[List[Literal["info", "warning", "error", "critical"]]] = Field(None, description="告警级别过滤")
    rule_types: Optional[List[Literal["global", "specific"]]] = Field(None, description="规则类型过滤")

# 评分系统相关schemas
class DimensionScore(BaseModel):
    """维度分数"""
    name: str = Field(..., description="维度名称")
    score: float = Field(..., description="分数(0-100)")
    alert_count: int = Field(..., description="告警数量")
    deductions: List[dict] = Field(..., description="扣分详情")

class MachineScore(BaseModel):
    """机器评分"""
    ip: str = Field(..., description="IP地址")
    total_score: float = Field(..., description="总分(0-100)")
    dimensions: Dict[str, DimensionScore] = Field(..., description="各维度分数")
    evaluation_time: datetime = Field(..., description="评估时间")

class ScoreQueryParams(BaseModel):
    """评分查询参数"""
    start_time: int = Field(..., description="开始时间戳")
    end_time: int = Field(..., description="结束时间戳")
    ips: Optional[List[str]] = Field(None, description="指定IP列表，为空则查询所有IP")
    include_details: bool = Field(True, description="是否包含详细扣分信息")

class ScoreResponse(BaseModel):
    """评分响应"""
    scores: List[MachineScore] = Field(..., description="机器评分列表")
    total_count: int = Field(..., description="机器总数")
    query_time: datetime = Field(..., description="查询时间")

# 使用率top相关schemas
class UsageTimeSeries(BaseModel):
    """使用率时间序列"""
    timestamp: int = Field(..., description="时间戳")
    usage_rate: float = Field(..., description="使用率")

class UsageTopItem(BaseModel):
    """使用率top项目"""
    ip: str = Field(..., description="IP地址")
    usage_rate: float = Field(..., description="最新使用率")
    latest_timestamp: int = Field(..., description="最新数据时间戳")
    time_series: List[UsageTimeSeries] = Field(..., description="时间段内的使用率序列")

class DimensionUsage(BaseModel):
    """维度使用率"""
    name: str = Field(..., description="维度名称")
    unit: str = Field(..., description="单位")
    top_items: List[UsageTopItem] = Field(..., description="top项目列表")

class UsageTopRequest(BaseModel):
    """使用率top查询请求"""
    start_time: int = Field(..., description="开始时间戳（Unix时间戳）")
    end_time: int = Field(..., description="结束时间戳（Unix时间戳）")
    top_count: int = Field(10, description="返回top数量，默认10")
    dimensions: Optional[List[Literal["CPU", "内存", "磁盘", "网络", "Swap"]]] = Field(None, description="指定维度列表，默认全部维度")

class UsageTopResponse(BaseModel):
    """使用率top查询响应"""
    time_range: dict = Field(..., description="查询时间范围")
    dimensions: Dict[str, DimensionUsage] = Field(..., description="各维度top数据")
    query_time: datetime = Field(..., description="查询时间")