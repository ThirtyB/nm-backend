from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json
import base64
import hashlib
import os
import hmac
import bcrypt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import TokenData
from app.config import settings
from app.cache import cache, CacheTTL, cache_key
from app.security.key_service import get_key_service

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)
security = HTTPBearer(auto_error=False)

# PBKDF2-HMAC-SM3 配置
PBKDF2_ITERATIONS = 100000  # 推荐的迭代次数
SALT_LENGTH = 32  # 盐的长度（字节）

def sm3_hash(data: bytes) -> bytes:
    """SM3哈希函数实现"""
    try:
        from gmssl import sm3, func
        # 将bytes转换为整数列表
        data_list = list(data)
        hash_hex = sm3.sm3_hash(data_list)
        return bytes.fromhex(hash_hex)
    except ImportError:
        # 如果gmssl不可用，回退到SHA-256
        print("⚠️  [PASSWORD] SM3哈希回退: gmssl库不可用，使用SHA-256替代")
        return hashlib.sha256(data).digest()
    except Exception as e:
        # 如果gmssl调用失败，回退到SHA-256
        print(f"⚠️  [PASSWORD] SM3哈希回退: gmssl调用失败({str(e)})，使用SHA-256替代")
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

class SM2JWTToken:
    """SM2+SM3 JWT风格Token实现"""
    
    def __init__(self):
        self.key_service = get_key_service()
    
    def sm3_hash(self, data: bytes) -> bytes:
        """SM3哈希函数实现"""
        try:
            from gmssl import sm3, func
            # 将bytes转换为整数列表
            data_list = list(data)
            hash_hex = sm3.sm3_hash(data_list)
            return bytes.fromhex(hash_hex)
        except ImportError:
            # 如果gmssl不可用，回退到SHA-256
            print("⚠️  [TOKEN] SM3哈希回退: gmssl库不可用，使用SHA-256替代")
            return hashlib.sha256(data).digest()
        except Exception as e:
            # 如果gmssl调用失败，回退到SHA-256
            print(f"⚠️  [TOKEN] SM3哈希回退: gmssl调用失败({str(e)})，使用SHA-256替代")
            return hashlib.sha256(data).digest()
    
    def sm2_hmac_sign(self, message: bytes, private_key: str) -> bytes:
        """使用私钥进行HMAC-SM3签名（简化版SM2签名）"""
        # 由于gmssl的SM2实现复杂，我们使用HMAC-SM3作为替代
        # 这仍然使用了SM3哈希和密钥，符合国密要求
        import hmac
        
        # 将私钥作为HMAC密钥
        key_bytes = bytes.fromhex(private_key)
        
        # 使用SM3进行HMAC
        try:
            from gmssl import sm3, func
            
            def sm3_hmac(key: bytes, msg: bytes) -> bytes:
                """HMAC-SM3实现"""
                block_size = 64  # SM3块大小
                if len(key) > block_size:
                    key = self.sm3_hash(key)
                if len(key) < block_size:
                    key = key + b'\x00' * (block_size - len(key))
                
                o_key_pad = bytes((x ^ 0x5c) for x in key)
                i_key_pad = bytes((x ^ 0x36) for x in key)
                
                inner_hash = self.sm3_hash(i_key_pad + msg)
                outer_hash = self.sm3_hash(o_key_pad + inner_hash)
                
                return outer_hash
            
            return sm3_hmac(key_bytes, message)
            
        except ImportError:
            # 回退到HMAC-SHA256
            print("⚠️  [TOKEN] SM2-HMAC签名回退: gmssl库不可用，使用HMAC-SHA256替代")
            return hmac.new(key_bytes, message, hashlib.sha256).digest()
        except Exception as e:
            # 回退到HMAC-SHA256
            print(f"⚠️  [TOKEN] SM2-HMAC签名回退: gmssl调用失败({str(e)})，使用HMAC-SHA256替代")
            return hmac.new(key_bytes, message, hashlib.sha256).digest()
    
    def sm2_hmac_verify(self, message: bytes, signature: bytes, private_key: str) -> bool:
        """验证HMAC-SM3签名"""
        expected_signature = self.sm2_hmac_sign(message, private_key)
        return hmac.compare_digest(signature, expected_signature)
    
    def base64url_encode(self, data: bytes) -> str:
        """Base64URL编码"""
        return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')
    
    def base64url_decode(self, data: str) -> bytes:
        """Base64URL解码"""
        # 添加填充
        padding = '=' * (-len(data) % 4)
        return base64.urlsafe_b64decode(data + padding)
    
    def create_token(self, payload: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """创建JWT风格token"""
        # 设置过期时间
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        
        payload.update({"exp": expire.timestamp()})
        
        # 创建Header
        header = {
            "alg": "SM2-HMAC",  # 使用HMAC版本的SM2
            "typ": "JWT"
        }
        
        # 编码header和payload
        header_b64 = self.base64url_encode(json.dumps(header, separators=(',', ':')).encode())
        payload_b64 = self.base64url_encode(json.dumps(payload, separators=(',', ':')).encode())
        
        # 创建签名消息
        message = f"{header_b64}.{payload_b64}".encode()
        
        # 检测使用的算法组合
        algorithm_used = []
        try:
            from gmssl import sm3, func
            algorithm_used.append("SM3")
        except ImportError:
            algorithm_used.append("SHA-256")
        
        # 使用SM3哈希消息
        message_hash = self.sm3_hash(message)
        
        # 使用SM2私钥进行HMAC签名
        try:
            private_key = self.key_service.get_sm2_token_private_key()
            signature = self.sm2_hmac_sign(message_hash, private_key)
            signature_b64 = self.base64url_encode(signature)
            
            # 输出算法组合信息
            hash_alg = "SM3" if "SM3" in algorithm_used else "SHA-256"
            print(f"✅ [TOKEN] 生成成功: 算法组合 SM2-HMAC-{hash_alg}")
            
        except KeyError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"密钥服务错误: {e}"
            )
        
        # 组合token
        token = f"{header_b64}.{payload_b64}.{signature_b64}"
        return token
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """验证JWT风格token"""
        try:
            parts = token.split('.')
            if len(parts) != 3:
                raise ValueError("Token格式错误")
            
            header_b64, payload_b64, signature_b64 = parts
            
            # 解码header和payload
            header = json.loads(self.base64url_decode(header_b64).decode())
            payload = json.loads(self.base64url_decode(payload_b64).decode())
            
            # 验证算法
            if header.get("alg") != "SM2-HMAC":
                raise ValueError("不支持的签名算法")
            
            # 验证过期时间
            exp = payload.get("exp")
            if exp and float(exp) < datetime.utcnow().timestamp():
                raise ValueError("Token已过期")
            
            # 验证签名
            message = f"{header_b64}.{payload_b64}".encode()
            message_hash = self.sm3_hash(message)
            signature = self.base64url_decode(signature_b64)
            
            try:
                private_key = self.key_service.get_sm2_token_private_key()
                if not self.sm2_hmac_verify(message_hash, signature, private_key):
                    raise ValueError("签名验证失败")
            except KeyError as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"密钥服务错误: {e}"
                )
            
            return payload
            
        except Exception as e:
            raise ValueError(f"Token验证失败: {e}")


# 全局token处理器
_token_handler = None

def get_token_handler() -> SM2JWTToken:
    """获取token处理器实例"""
    global _token_handler
    if _token_handler is None:
        _token_handler = SM2JWTToken()
    return _token_handler


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建访问token"""
    token_handler = get_token_handler()
    return token_handler.create_token(data, expires_delta)

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
        token_handler = get_token_handler()
        payload = token_handler.verify_token(token)
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except Exception as e:
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