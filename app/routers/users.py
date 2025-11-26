from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserResponse, UserUpdate, UserPartialUpdate, AdminUserCreate
from app.auth import get_current_admin_user, get_password_hash
from app.utils.phone_validation import check_phone_unique

router = APIRouter(prefix="/users", tags=["用户管理"])

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: AdminUserCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        if db_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        else:
            # 用户存在但已停用，重新激活并更新密码，按照管理员指定的权限设置
            # 检查手机号唯一性（如果提供了新手机号）
            if user.phone is not None and user.phone.strip() != "":
                if not check_phone_unique(db, user.phone, exclude_user_id=db_user.id):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Phone number already registered"
                    )
            
            db_user.hashed_password = get_password_hash(user.password)
            db_user.is_active = True
            db_user.user_type = user.user_type  # 按照管理员指定的权限设置
            db_user.set_phone_encrypted(user.phone)  # 使用加密方法设置手机号
            db.commit()
            db.refresh(db_user)
            return db_user
    
    # 检查手机号唯一性
    if user.phone is not None and user.phone.strip() != "":
        if not check_phone_unique(db, user.phone):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )
    
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        hashed_password=hashed_password,
        user_type=user.user_type,  # 按照管理员指定的权限设置
        is_active=True
    )
    # 使用加密方法设置手机号
    db_user.set_phone_encrypted(user.phone)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.get("/", response_model=List[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    include_inactive: bool = Query(False, description="是否包含已停用用户"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    query = db.query(User)
    if not include_inactive:
        query = query.filter(User.is_active == True)
    users = query.order_by(User.id).offset(skip).limit(limit).all()
    return users

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user_update.username is not None:
        existing_user = db.query(User).filter(User.username == user_update.username).first()
        if existing_user and existing_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        db_user.username = user_update.username
    
    if user_update.password is not None:
        db_user.hashed_password = get_password_hash(user_update.password)
    
    if user_update.user_type is not None:
        db_user.user_type = user_update.user_type
    
    if user_update.is_active is not None:
        db_user.is_active = user_update.is_active
    
    if user_update.phone is not None:
        # 检查手机号唯一性
        if user_update.phone.strip() != "":
            if not check_phone_unique(db, user_update.phone, exclude_user_id=user_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Phone number already registered"
                )
        db_user.set_phone_encrypted(user_update.phone)
    
    db.commit()
    db.refresh(db_user)
    return db_user

@router.patch("/{user_id}", response_model=UserResponse)
async def partial_update_user(
    user_id: int,
    user_update: UserPartialUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """部分更新用户信息，只更新提供的字段"""
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 只更新提供的字段
    if user_update.password is not None:
        db_user.hashed_password = get_password_hash(user_update.password)
    
    if user_update.user_type is not None:
        db_user.user_type = user_update.user_type
    
    if user_update.is_active is not None:
        db_user.is_active = user_update.is_active
    
    if user_update.phone is not None:
        # 检查手机号唯一性
        if user_update.phone.strip() != "":
            if not check_phone_unique(db, user_update.phone, exclude_user_id=user_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Phone number already registered"
                )
        db_user.set_phone_encrypted(user_update.phone)
    
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """停用用户"""
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    if db_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself"
        )
    
    # 停用用户
    db_user.is_active = False
    db.commit()
    
    return {"message": "User deactivated successfully"}

@router.post("/{user_id}/activate")
async def activate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """激活用户"""
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 激活用户
    db_user.is_active = True
    db.commit()
    
    return {"message": "User activated successfully"}