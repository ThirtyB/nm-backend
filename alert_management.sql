-- 告警规则表
CREATE TABLE IF NOT EXISTS alert_rules (
    id SERIAL PRIMARY KEY,
    rule_name VARCHAR(100) NOT NULL,
    rule_type VARCHAR(20) NOT NULL CHECK (rule_type IN ('global', 'specific')),
    target_ip VARCHAR(45),  -- 个例配置的目标IP，全局配置时为NULL
    
    -- 规则条件配置
    condition_field VARCHAR(50) NOT NULL,
    condition_operator VARCHAR(10) NOT NULL CHECK (condition_operator IN ('>', '<', '>=', '<=', '==', '!=')),
    condition_value FLOAT NOT NULL,
    
    -- 时间条件（可选）
    time_range_start BIGINT,
    time_range_end BIGINT,
    
    -- 告警级别和消息
    alert_level VARCHAR(20) DEFAULT 'warning' CHECK (alert_level IN ('info', 'warning', 'error', 'critical')),
    alert_message TEXT,
    
    -- 状态管理
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    
    -- 约束：个例规则必须有target_ip，全局规则不能有target_ip
    CONSTRAINT chk_target_ip_required 
        CHECK (
            (rule_type = 'specific' AND target_ip IS NOT NULL) OR 
            (rule_type = 'global' AND target_ip IS NULL)
        )
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_alert_rules_type_ip ON alert_rules(rule_type, target_ip);
CREATE INDEX IF NOT EXISTS idx_alert_rules_active ON alert_rules(is_active);
CREATE INDEX IF NOT EXISTS idx_alert_rules_field ON alert_rules(condition_field);
CREATE INDEX IF NOT EXISTS idx_alert_rules_time_range ON alert_rules(time_range_start, time_range_end);

-- 添加更新时间触发器（PostgreSQL）
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_alert_rules_updated_at 
    BEFORE UPDATE ON alert_rules 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- 插入示例数据
INSERT INTO alert_rules (rule_name, rule_type, condition_field, condition_operator, condition_value, alert_level, alert_message) VALUES
('CPU使用率过高告警', 'global', 'cpu_usage_rate', '>', 80.0, 'warning', 'CPU使用率 {current_value}% 超过阈值 {threshold_value}%'),
('内存使用率过高告警', 'global', 'memory_usage_rate', '>', 85.0, 'error', '内存使用率 {current_value}% 超过阈值 {threshold_value}%'),
('磁盘使用率过高告警', 'global', 'disk_used_percent', '>', 90.0, 'critical', '磁盘使用率 {current_value}% 超过阈值 {threshold_value}%'),
('网络速率异常告警', 'global', 'network_rate', '<', 0.1, 'info', '网络速率 {current_value} kbps 低于阈值 {threshold_value} kbps');

-- 个例规则示例
INSERT INTO alert_rules (rule_name, rule_type, target_ip, condition_field, condition_operator, condition_value, alert_level, alert_message) VALUES
('特定服务器CPU告警', 'specific', '192.168.1.100', 'cpu_usage_rate', '>', 70.0, 'warning', '服务器 {ip} CPU使用率 {current_value}% 超过阈值 {threshold_value}%'),
('特定服务器内存告警', 'specific', '192.168.1.100', 'memory_usage_rate', '>', 80.0, 'error', '服务器 {ip} 内存使用率 {current_value}% 超过阈值 {threshold_value}%');

-- 查询所有活跃规则的视图
CREATE OR REPLACE VIEW active_alert_rules AS
SELECT 
    id,
    rule_name,
    rule_type,
    target_ip,
    condition_field,
    condition_operator,
    condition_value,
    time_range_start,
    time_range_end,
    alert_level,
    alert_message,
    created_at,
    updated_at
FROM alert_rules 
WHERE is_active = TRUE
ORDER BY 
    CASE WHEN rule_type = 'specific' THEN 0 ELSE 1 END,  -- 个例规则优先
    rule_type,
    target_ip,
    condition_field;