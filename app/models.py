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