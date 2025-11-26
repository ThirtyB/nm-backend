-- 创建访问日志表
CREATE TABLE IF NOT EXISTS access_logs (
    id BIGSERIAL PRIMARY KEY,
    trace_id TEXT,
    logtime TIMESTAMPTZ,
    remote_addr INET,
    server_addr INET,
    server_port INTEGER,
    ssl_protocol TEXT,
    connection TEXT,
    connection_requests INTEGER,
    connection_time DOUBLE PRECISION,
    request_method TEXT,
    request_uri TEXT,
    server_protocol TEXT,
    request_body TEXT,
    request_time DOUBLE PRECISION,
    request_completion TEXT,
    status INTEGER,
    bytes_sent BIGINT,
    body_bytes_sent BIGINT,
    http_referer TEXT,
    http_user_agent TEXT,
    upstream_addr TEXT,
    upstream_bytes_received TEXT,
    upstream_bytes_sent TEXT,
    upstream_response_time TEXT,
    upstream_connect_time TEXT,
    inserted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_access_logs_logtime ON access_logs(logtime);
CREATE INDEX IF NOT EXISTS idx_access_logs_remote_addr ON access_logs(remote_addr);
CREATE INDEX IF NOT EXISTS idx_access_logs_status ON access_logs(status);
CREATE INDEX IF NOT EXISTS idx_access_logs_trace_id ON access_logs(trace_id);