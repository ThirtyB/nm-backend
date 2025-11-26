-- 创建用户表
DROP TABLE IF EXISTS users CASCADE;

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    user_type VARCHAR(20) DEFAULT 'user' NOT NULL CHECK (user_type IN ('admin', 'user')),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    phone VARCHAR(20),  -- 保留原字段用于向后兼容，建议设为 NULL
    -- SM4-CBC + HMAC 加密字段
    phone_encrypted BYTEA,  -- 加密后的手机号密文
    phone_iv BYTEA,         -- CBC 初始化向量 (16字节)
    phone_tag BYTEA,        -- HMAC-SHA256 认证标签 (32字节)
    phone_alg VARCHAR(20) DEFAULT 'SM4-CBC-HMAC',  -- 加密算法标识
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_login TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_user_type ON users(user_type);
CREATE INDEX idx_users_is_active ON users(is_active);
-- 不再为 phone 字段创建索引，因为它是加密的
-- CREATE INDEX idx_users_phone ON users(phone);  -- 移除手机号索引