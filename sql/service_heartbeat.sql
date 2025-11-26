-- 创建服务探活表
DROP TABLE IF EXISTS service_heartbeat CASCADE;

CREATE TABLE service_heartbeat (
    id SERIAL PRIMARY KEY,
    ip_address VARCHAR(45) NOT NULL,
    service_name VARCHAR(100) NOT NULL,
    report_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 创建索引
CREATE INDEX idx_service_heartbeat_ip ON service_heartbeat(ip_address);
CREATE INDEX idx_service_heartbeat_service ON service_heartbeat(service_name);
CREATE INDEX idx_service_heartbeat_report_time ON service_heartbeat(report_time);
CREATE INDEX idx_service_heartbeat_ip_service ON service_heartbeat(ip_address, service_name);