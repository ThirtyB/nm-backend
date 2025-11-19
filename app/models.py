from sqlalchemy import Column, Integer, String, DateTime, Boolean, BigInteger, Float, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    user_type = Column(String(20), default="user", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_login = Column(DateTime(timezone=True))

class NodeMonitorMetrics(Base):
    __tablename__ = "node_monitor_metrics"
    
    id = Column(BigInteger, primary_key=True, index=True)
    ip = Column(Text, nullable=False, index=True)
    ts = Column(BigInteger, nullable=False, index=True)
    cpu_usr = Column(Float)
    cpu_sys = Column(Float)
    cpu_iow = Column(Float)
    mem_total = Column(BigInteger)
    mem_free = Column(BigInteger)
    mem_buff = Column(BigInteger)
    mem_cache = Column(BigInteger)
    swap_total = Column(BigInteger)
    swap_used = Column(BigInteger)
    swap_in = Column(BigInteger)
    swap_out = Column(BigInteger)
    system_in = Column(BigInteger)
    system_cs = Column(BigInteger)
    disk_name = Column(Text)
    disk_total = Column(BigInteger)
    disk_used = Column(BigInteger)
    disk_used_percent = Column(Float)
    disk_iops = Column(BigInteger)
    disk_r = Column(BigInteger)
    disk_w = Column(BigInteger)
    net_rx_kbytes = Column(Float)
    net_tx_kbytes = Column(Float)
    net_rx_kbps = Column(Float)
    net_tx_kbps = Column(Float)
    version = Column(Text)
    inserted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class AlertRule(Base):
    __tablename__ = "alert_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    rule_name = Column(String(100), nullable=False)
    rule_type = Column(String(20), nullable=False)  # "global" 或 "specific"
    target_ip = Column(String(45))  # 个例配置的目标IP，全局配置时为NULL
    
    # 规则条件配置
    condition_field = Column(String(50), nullable=False)
    condition_operator = Column(String(10), nullable=False)  # >, <, >=, <=, ==, !=
    condition_value = Column(Float, nullable=False)
    
    # 时间条件（可选）
    time_range_start = Column(BigInteger)
    time_range_end = Column(BigInteger)
    
    # 告警级别和消息
    alert_level = Column(String(20), default="warning")  # info, warning, error, critical
    alert_message = Column(Text)
    
    # 状态管理
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True))

class ServiceHeartbeat(Base):
    __tablename__ = "service_heartbeat"
    
    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String(45), nullable=False, index=True)
    service_name = Column(String(100), nullable=False, index=True)
    report_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)