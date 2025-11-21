-- 访问日志记录表结构
-- 创建时间: 2025-11-21

-- Redis访问日志表
CREATE TABLE redis_access_log (
    id SERIAL PRIMARY KEY,
    client_ip VARCHAR(45) NOT NULL,
    operation VARCHAR(20) NOT NULL,
    redis_key VARCHAR(255) NOT NULL,
    access_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    execution_time_ms INTEGER,
    status VARCHAR(10) DEFAULT 'success',
    error_message TEXT,
    additional_info JSONB
);

-- 数据库访问日志表
CREATE TABLE database_access_log (
    id SERIAL PRIMARY KEY,
    client_ip VARCHAR(45) NOT NULL,
    operation VARCHAR(20) NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    access_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    execution_time_ms INTEGER,
    status VARCHAR(10) DEFAULT 'success',
    error_message TEXT,
    affected_rows INTEGER,
    query_hash VARCHAR(64)
);

-- 创建索引以提高查询性能
CREATE INDEX idx_redis_access_log_time ON redis_access_log(access_time);
CREATE INDEX idx_redis_access_log_ip ON redis_access_log(client_ip);
CREATE INDEX idx_redis_access_log_operation ON redis_access_log(operation);

CREATE INDEX idx_database_access_log_time ON database_access_log(access_time);
CREATE INDEX idx_database_access_log_ip ON database_access_log(client_ip);
CREATE INDEX idx_database_access_log_operation ON database_access_log(operation);
CREATE INDEX idx_database_access_log_table ON database_access_log(table_name);