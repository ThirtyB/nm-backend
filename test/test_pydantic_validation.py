#!/usr/bin/env python3
"""
测试 Pydantic 验证器是否正常工作
"""
from app.database import SessionLocal
from app.models import User
from app.schemas import UserResponse, UserProfile

def test_pydantic_validation():
    """测试 Pydantic 验证器"""
    print("🧪 测试 Pydantic 验证器")
    print("=" * 40)
    
    db = SessionLocal()
    try:
        # 获取测试用户
        user = db.query(User).filter(User.username == 'test_phone_user').first()
        if not user:
            print("❌ 测试用户不存在")
            return
        
        print(f"✅ 找到用户: {user.username}")
        print(f"   phone_decrypted: {user.phone_decrypted}")
        print(f"   phone_encrypted: {user.phone_encrypted is not None}")
        
        # 测试 UserResponse
        print("\n📝 测试 UserResponse...")
        try:
            user_response = UserResponse.model_validate(user)
            print(f"✅ UserResponse 验证成功")
            print(f"   phone: {user_response.phone}")
            if user_response.phone == "13812345678":
                print("✅ UserResponse 手机号解密正确！")
            else:
                print(f"❌ UserResponse 手机号解密错误，期望: 13812345678，实际: {user_response.phone}")
        except Exception as e:
            print(f"❌ UserResponse 验证失败: {e}")
        
        # 测试 UserProfile
        print("\n👤 测试 UserProfile...")
        try:
            user_profile = UserProfile.model_validate(user)
            print(f"✅ UserProfile 验证成功")
            print(f"   phone: {user_profile.phone}")
            if user_profile.phone == "13812345678":
                print("✅ UserProfile 手机号解密正确！")
            else:
                print(f"❌ UserProfile 手机号解密错误，期望: 13812345678，实际: {user_profile.phone}")
        except Exception as e:
            print(f"❌ UserProfile 验证失败: {e}")
        
        # 测试手动转换
        print("\n🔧 测试手动转换...")
        try:
            user_dict = {
                'id': user.id,
                'username': user.username,
                'user_type': user.user_type,
                'is_active': user.is_active,
                'phone': user.phone_decrypted,
                'created_at': user.created_at,
                'last_login': user.last_login
            }
            user_response_manual = UserResponse(**user_dict)
            print(f"✅ 手动转换成功")
            print(f"   phone: {user_response_manual.phone}")
            if user_response_manual.phone == "13812345678":
                print("✅ 手动转换手机号正确！")
            else:
                print(f"❌ 手动转换手机号错误，期望: 13812345678，实际: {user_response_manual.phone}")
        except Exception as e:
            print(f"❌ 手动转换失败: {e}")
            
    finally:
        db.close()

if __name__ == "__main__":
    test_pydantic_validation()