from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import UserProfile, UserPhoneUpdate
from app.auth import get_current_user
from app.utils.phone_validation import check_phone_unique

router = APIRouter(prefix="/profile", tags=["用户个人信息"])

@router.get("/me", response_model=UserProfile)
async def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    """获取当前用户的个人信息"""
    return current_user

@router.put("/phone", response_model=UserProfile)
async def update_my_phone(
    phone_update: UserPhoneUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新当前用户的手机号"""
    # 简单的手机号格式验证
    if phone_update.phone is not None:
        if phone_update.phone and not phone_update.phone.isdigit():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="手机号只能包含数字"
            )
        if phone_update.phone and len(phone_update.phone) not in [11, 12, 13, 14, 15]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="手机号长度不正确"
            )
    
    # 检查手机号唯一性
    if phone_update.phone is not None and phone_update.phone.strip() != "":
        if not check_phone_unique(db, phone_update.phone, exclude_user_id=current_user.id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )
    
    # 更新手机号（使用加密方法）
    current_user.set_phone_encrypted(phone_update.phone)
    db.commit()
    db.refresh(current_user)
    
    return current_user

@router.delete("/phone")
async def delete_my_phone(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除当前用户的手机号（设置为空）"""
    current_user.set_phone_encrypted(None)
    db.commit()
    
    return {"message": "手机号已删除"}