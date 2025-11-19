from pydantic import BaseModel, Field
from typing import Optional, Literal
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