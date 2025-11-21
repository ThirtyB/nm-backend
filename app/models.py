from sqlalchemy import Column, Integer, String, DateTime, Boolean, BigInteger, Float, Text, JSON
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

class RedisAccessLog(Base):
    __tablename__ = "redis_access_log"
    
    id = Column(Integer, primary_key=True, index=True)
    client_ip = Column(String(45), nullable=False, index=True)
    operation = Column(String(20), nullable=False, index=True)
    redis_key = Column(String(255), nullable=False)
    access_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    execution_time_ms = Column(Integer)
    status = Column(String(10), default="success")
    error_message = Column(Text)
    additional_info = Column(JSON)

class DatabaseAccessLog(Base):
    __tablename__ = "database_access_log"
    
    id = Column(Integer, primary_key=True, index=True)
    client_ip = Column(String(45), nullable=False, index=True)
    operation = Column(String(20), nullable=False, index=True)
    table_name = Column(String(100), nullable=False, index=True)
    access_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    execution_time_ms = Column(Integer)
    status = Column(String(10), default="success")
    error_message = Column(Text)
    affected_rows = Column(Integer)
    query_hash = Column(String(64))

class AccessLog(Base):
    __tablename__ = "access_logs"
    
    id = Column(BigInteger, primary_key=True, index=True)
    trace_id = Column(Text)
    logtime = Column(DateTime(timezone=True))
    remote_addr = Column(String(45))  # 客户端IP
    server_addr = Column(String(45))  # 服务器IP
    server_port = Column(Integer)
    ssl_protocol = Column(Text)
    connection = Column(Text)
    connection_requests = Column(Integer)
    connection_time = Column(Float)
    request_method = Column(Text)  # HTTP方法
    request_uri = Column(Text)     # 请求URI
    server_protocol = Column(Text)
    request_body = Column(Text)
    request_time = Column(Float)
    request_completion = Column(Text)
    status = Column(Integer)        # HTTP状态码
    bytes_sent = Column(BigInteger)
    body_bytes_sent = Column(BigInteger)
    http_referer = Column(Text)
    http_user_agent = Column(Text)
    upstream_addr = Column(Text)
    upstream_bytes_received = Column(Text)
    upstream_bytes_sent = Column(Text)
    upstream_response_time = Column(Text)
    upstream_connect_time = Column(Text)
    inserted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)