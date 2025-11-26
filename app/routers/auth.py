from datetime import timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import Token, UserLogin, UserCreate, UserResponse
from app.auth import authenticate_user, create_access_token, get_password_hash, get_current_user
from app.models import User
from app.config import settings
from app.utils.phone_validation import check_phone_unique, find_user_by_phone

router = APIRouter(prefix="/auth", tags=["认证"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # 检查用户名是否已存在
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        if existing_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        else:
            # 用户存在但已停用，重新激活并更新密码，强制设置为普通用户
            # 检查手机号唯一性（如果提供了新手机号）
            if user_data.phone is not None and user_data.phone.strip() != "":
                if not check_phone_unique(db, user_data.phone, exclude_user_id=existing_user.id):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Phone number already registered"
                    )
            
            existing_user.hashed_password = get_password_hash(user_data.password)
            existing_user.is_active = True
            existing_user.user_type = "user"  # 强制为普通用户
            existing_user.set_phone_encrypted(user_data.phone)  # 更新加密的手机号
            db.commit()
            db.refresh(existing_user)
            return existing_user
    
    # 检查手机号唯一性
    if user_data.phone is not None and user_data.phone.strip() != "":
        if not check_phone_unique(db, user_data.phone):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )
    
    # 创建新用户
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        hashed_password=hashed_password,
        user_type="user",  # 强制为普通用户
        is_active=True
    )
    # 设置加密的手机号
    new_user.set_phone_encrypted(user_data.phone)
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@router.post("/login", response_model=Token)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    from app.auth import is_bcrypt_hash
    
    # 首先尝试用户名登录
    user = db.query(User).filter(User.username == user_data.username).first()
    
    # 如果用户名登录失败，尝试手机号登录
    if not user:
        user = find_user_by_phone(db, user_data.username)
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 验证密码
    from app.auth import verify_password
    if not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 检查是否需要迁移密码哈希（从bcrypt到PBKDF2-HMAC-SM3）
    if is_bcrypt_hash(user.hashed_password):
        print(f"迁移用户 {user.username} 的密码哈希到PBKDF2-HMAC-SM3")
        # 生成新的PBKDF2-HMAC-SM3哈希
        from app.auth import get_password_hash
        new_hash = get_password_hash(user_data.password)
        user.hashed_password = new_hash
        print(f"密码哈希迁移完成")
    
    # 更新最后登录时间
    user.last_login = datetime.utcnow()
    db.commit()
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return current_user