-- 创建简化的服务访问日志表
DROP TABLE IF EXISTS service_access_logs CASCADE;

CREATE TABLE service_access_logs (
    id SERIAL PRIMARY KEY,
    client_ip VARCHAR(45) NOT NULL,           -- 访问后端的客户端IP
    service_ip VARCHAR(45) NOT NULL,           -- 被访问的服务IP（数据库或Redis）
    service_type VARCHAR(20) NOT NULL,         -- 服务类型：'database' 或 'redis'
    access_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 创建索引
CREATE INDEX idx_service_access_client_ip ON service_access_logs(client_ip);
CREATE INDEX idx_service_access_service_ip ON service_access_logs(service_ip);
CREATE INDEX idx_service_access_service_type ON service_access_logs(service_type);
CREATE INDEX idx_service_access_time ON service_access_logs(access_time);
CREATE INDEX idx_service_access_composite ON service_access_logs(service_type, access_time);