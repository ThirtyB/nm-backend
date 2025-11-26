"""
手机号唯一性验证工具
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from app.models import User


def check_phone_unique(db: Session, phone: Optional[str], exclude_user_id: Optional[int] = None) -> bool:
    """
    检查手机号是否唯一
    
    Args:
        db: 数据库会话
        phone: 要检查的手机号
        exclude_user_id: 排除的用户ID（用于更新时排除自己）
    
    Returns:
        True: 手机号唯一或为空
        False: 手机号已存在
    """
    if not phone or phone.strip() == "":
        return True  # 空手机号不需要检查唯一性
    
    # 获取所有用户
    query = db.query(User)
    if exclude_user_id is not None:
        query = query.filter(User.id != exclude_user_id)
    
    users = query.all()
    
    # 检查每个用户的解密手机号
    for user in users:
        try:
            decrypted_phone = user.phone_decrypted
            if decrypted_phone and decrypted_phone == phone:
                return False
        except Exception:
            # 如果解密失败，跳过该用户
            continue
    
    return True


def get_all_phone_numbers(db: Session) -> List[str]:
    """
    获取数据库中所有已解密的手机号列表
    
    Args:
        db: 数据库会话
    
    Returns:
        手机号列表
    """
    users = db.query(User).all()
    phone_numbers = []
    
    for user in users:
        try:
            decrypted_phone = user.phone_decrypted
            if decrypted_phone:
                phone_numbers.append(decrypted_phone)
        except Exception:
            # 如果解密失败，跳过该用户
            continue
    
    return phone_numbers


def find_user_by_phone(db: Session, phone: str) -> Optional[User]:
    """
    根据手机号查找用户
    
    Args:
        db: 数据库会话
        phone: 手机号
    
    Returns:
        找到的用户对象，如果没找到返回None
    """
    if not phone or phone.strip() == "":
        return None
    
    users = db.query(User).all()
    
    for user in users:
        try:
            decrypted_phone = user.phone_decrypted
            if decrypted_phone and decrypted_phone == phone:
                return user
        except Exception:
            # 如果解密失败，跳过该用户
            continue
    
    return None