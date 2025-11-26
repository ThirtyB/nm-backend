#!/usr/bin/env python3
"""
测试手机号验证工具函数
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.phone_validation import check_phone_unique, get_all_phone_numbers, find_user_by_phone
from app.database import get_db, engine, Base
from app.models import User
from sqlalchemy.orm import sessionmaker

def test_phone_validation_utils():
    """测试手机号验证工具函数"""
    print("=== 测试手机号验证工具函数 ===")
    
    # 创建数据库会话
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # 测试获取所有手机号
        print("\n1. 获取所有手机号:")
        phone_numbers = get_all_phone_numbers(db)
        print(f"   当前数据库中的手机号: {phone_numbers}")
        
        # 测试检查唯一性
        print("\n2. 检查手机号唯一性:")
        
        # 检查不存在的手机号
        test_phone_1 = "19999999999"
        is_unique_1 = check_phone_unique(db, test_phone_1)
        print(f"   手机号 {test_phone_1} 是否唯一: {is_unique_1}")
        
        # 检查空手机号
        is_unique_empty = check_phone_unique(db, "")
        print(f"   空手机号是否唯一: {is_unique_empty}")
        
        # 检查None手机号
        is_unique_none = check_phone_unique(db, None)
        print(f"   None手机号是否唯一: {is_unique_none}")
        
        # 如果数据库中有手机号，测试检查重复
        if phone_numbers:
            existing_phone = phone_numbers[0]
            is_unique_existing = check_phone_unique(db, existing_phone)
            print(f"   已存在手机号 {existing_phone} 是否唯一: {is_unique_existing}")
        
        # 测试根据手机号查找用户
        print("\n3. 根据手机号查找用户:")
        
        # 查找不存在的用户
        user_1 = find_user_by_phone(db, test_phone_1)
        print(f"   手机号 {test_phone_1} 对应的用户: {user_1}")
        
        # 查找存在的用户
        if phone_numbers:
            existing_phone = phone_numbers[0]
            user_existing = find_user_by_phone(db, existing_phone)
            if user_existing:
                print(f"   手机号 {existing_phone} 对应的用户ID: {user_existing.id}, 用户名: {user_existing.username}")
            else:
                print(f"   手机号 {existing_phone} 未找到对应用户")
        
        print("\n✓ 手机号验证工具函数测试完成")
        
    except Exception as e:
        print(f"\n✗ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    print("开始测试手机号验证工具函数...")
    test_phone_validation_utils()
    print("\n测试完成!")