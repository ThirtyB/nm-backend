-- 创建请求日志表
DROP TABLE IF EXISTS request_logs CASCADE;

CREATE TABLE request_logs (
    id SERIAL PRIMARY KEY,
    frontend_ip VARCHAR(45) NOT NULL,           -- 前端IP地址（支持IPv6）
    backend_ip VARCHAR(45) NOT NULL,            -- 后端服务器IP地址
    request_method VARCHAR(10) NOT NULL,        -- HTTP方法 (GET, POST, PUT, DELETE等)
    request_path VARCHAR(500) NOT NULL,         -- 请求路径
    query_params TEXT,                           -- 查询参数（JSON格式）
    request_time TIMESTAMP NOT NULL,             -- 请求时间
    response_status INTEGER,                     -- 响应状态码
    response_time_ms INTEGER,                    -- 响应时间（毫秒）
    user_agent TEXT,                             -- 用户代理
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 创建索引
CREATE INDEX idx_request_logs_frontend_ip ON request_logs(frontend_ip);
CREATE INDEX idx_request_logs_backend_ip ON request_logs(backend_ip);
CREATE INDEX idx_request_logs_request_time ON request_logs(request_time);
CREATE INDEX idx_request_logs_request_path ON request_logs(request_path);
CREATE INDEX idx_request_logs_response_status ON request_logs(response_status);
CREATE INDEX idx_request_logs_created_at ON request_logs(created_at);

-- 创建复合索引用于查询优化
CREATE INDEX idx_request_logs_time_ip ON request_logs(request_time, frontend_ip);
CREATE INDEX idx_request_logs_path_time ON request_logs(request_path, request_time);

-- 添加表注释
COMMENT ON TABLE request_logs IS '请求日志表，记录所有API请求信息（除/heartbeat/report外）';
COMMENT ON COLUMN request_logs.frontend_ip IS '发起请求的前端IP地址';
COMMENT ON COLUMN request_logs.backend_ip IS '处理请求的后端服务器IP地址';
COMMENT ON COLUMN request_logs.request_method IS 'HTTP请求方法';
COMMENT ON COLUMN request_logs.request_path IS '请求的API路径';
COMMENT ON COLUMN request_logs.query_params IS '请求的查询参数，以JSON格式存储';
COMMENT ON COLUMN request_logs.request_time IS '请求开始时间';
COMMENT ON COLUMN request_logs.response_status IS 'HTTP响应状态码';
COMMENT ON COLUMN request_logs.response_time_ms IS '请求处理耗时，单位毫秒';
COMMENT ON COLUMN request_logs.user_agent IS '客户端用户代理字符串';