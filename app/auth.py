from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
import hashlib
import os
import base64
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import TokenData
from app.config import settings
from app.cache import cache, CacheTTL, cache_key

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)
security = HTTPBearer(auto_error=False)

# PBKDF2-HMAC-SM3 配置
PBKDF2_ITERATIONS = 100000  # 推荐的迭代次数
SALT_LENGTH = 32  # 盐的长度（字节）

def sm3_hash(data: bytes) -> bytes:
    """SM3哈希函数实现"""
    try:
        from gmssl import sm3
        return bytes.fromhex(sm3.sm3_hash(data))
    except ImportError:
        # 如果gmssl不可用，回退到SHA-256
        return hashlib.sha256(data).digest()

def get_password_hash(password: str) -> str:
    """使用PBKDF2-HMAC-SM3对密码进行哈希"""
    password_bytes = password.encode('utf-8')
    salt = os.urandom(SALT_LENGTH)
    
    # 使用PBKDF2-HMAC-SM3
    dk = hashlib.pbkdf2_hmac(
        'sha256',  # 由于Python标准库不支持SM3作为HMAC，先用SHA256
        password_bytes,
        salt,
        PBKDF2_ITERATIONS
    )
    
    # 应用SM3作为额外的哈希层
    final_hash = sm3_hash(dk)
    
    # 组合盐和哈希值进行存储
    salt_b64 = base64.b64encode(salt).decode('ascii')
    hash_b64 = base64.b64encode(final_hash).decode('ascii')
    
    return f"pbkdf2_sm3${PBKDF2_ITERATIONS}${salt_b64}${hash_b64}"

def is_bcrypt_hash(hashed_password: str) -> bool:
    """检查是否为bcrypt哈希"""
    return hashed_password.startswith('$2b$') or hashed_password.startswith('$2a$')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码是否匹配PBKDF2-HMAC-SM3哈希"""
    try:
        if not hashed_password:
            return False
            
        # 检查是否是新的PBKDF2-HMAC-SM3格式
        if hashed_password.startswith('pbkdf2_sm3$'):
            parts = hashed_password.split('$')
            if len(parts) != 4:
                return False
                
            iterations = int(parts[1])
            salt = base64.b64decode(parts[2])
            stored_hash = base64.b64decode(parts[3])
            
            # 使用相同的参数重新计算哈希
            password_bytes = plain_password.encode('utf-8')
            dk = hashlib.pbkdf2_hmac(
                'sha256',
                password_bytes,
                salt,
                iterations
            )
            
            # 应用SM3作为额外的哈希层
            computed_hash = sm3_hash(dk)
            
            # 比较哈希值
            return computed_hash == stored_hash
        else:
            # 向后兼容：支持旧的bcrypt格式
            try:
                return bcrypt.checkpw(plain_password.encode('utf-8')[:72], hashed_password.encode('utf-8'))
            except:
                return pwd_context.verify(plain_password, hashed_password)
                
    except Exception:
        return False

def get_user(db: Session, username: str):
    # 缓存不包含密码哈希，直接从数据库查询
    user = db.query(User).filter(User.username == username).first()
    if user:
        # 存入缓存基本信息（不包含密码哈希）
        cache_key_str = cache_key("user", "info", username)
        user_data = {
            "id": user.id,
            "username": user.username,
            "user_type": user.user_type,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None
        }
        cache.set(cache_key_str, user_data, CacheTTL.TWO_HOURS)
    
    return user

def authenticate_user(db: Session, username: str, password: str):
    user = get_user(db, username)
    if not user:
        return False
    if not user.is_active:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)):
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_admin_user(current_user: User = Depends(get_current_user)):
    if current_user.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

# 便捷的管理员依赖
async def get_admin_user(current_user: User = Depends(get_current_user)):
    """获取管理员用户（用于权限控制）"""
    if current_user.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user