#!/usr/bin/env python3
"""
用户删除和禁用功能演示脚本
"""

import requests
import json
import time

# API基础URL
BASE_URL = "http://localhost:8000"

def get_auth_token(username="admin", password="admin123"):
    """获取管理员token"""
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": username,
        "password": password
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("access_token")
    return None

def demo_user_lifecycle():
    """演示用户生命周期管理"""
    print("🚀 用户生命周期管理演示")
    print("=" * 60)
    
    admin_token = get_auth_token()
    if not admin_token:
        print("❌ 无法获取管理员权限")
        return
    
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }
    
    # 创建测试用户
    user_data = {
        "username": "lifecycle_user",
        "password": "demo123456",
        "user_type": "user",
        "phone": "13800137777"
    }
    
    print("\n📝 1. 创建用户")
    response = requests.post(f"{BASE_URL}/users/", json=user_data, headers=headers)
    if response.status_code == 201:
        user = response.json()
        user_id = user['id']
        print(f"✅ 用户创建成功")
        print(f"   ID: {user_id}")
        print(f"   用户名: {user['username']}")
        print(f"   手机号: {user['phone']}")
        print(f"   状态: {'激活' if user['is_active'] else '禁用'}")
    else:
        print(f"❌ 创建用户失败: {response.text}")
        return
    
    time.sleep(1)
    
    # 测试登录
    print(f"\n🔐 2. 测试用户登录")
    login_response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": user_data["username"],
        "password": user_data["password"]
    })
    
    if login_response.status_code == 200:
        print("✅ 用户登录成功")
    else:
        print(f"❌ 用户登录失败: {login_response.text}")
    
    time.sleep(1)
    
    # 禁用用户
    print(f"\n🚫 3. 禁用用户")
    deactivate_response = requests.post(f"{BASE_URL}/users/{user_id}/deactivate", headers=headers)
    if deactivate_response.status_code == 200:
        print("✅ 用户禁用成功")
    else:
        print(f"❌ 用户禁用失败: {deactivate_response.text}")
    
    time.sleep(1)
    
    # 测试禁用后登录
    print(f"\n🔒 4. 测试禁用用户登录")
    login_disabled_response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": user_data["username"],
        "password": user_data["password"]
    })
    
    if login_disabled_response.status_code == 401:
        error_detail = login_disabled_response.json().get("detail")
        if error_detail == "Account is disabled":
            print("✅ 禁用用户登录被正确拒绝")
            print(f"   错误信息: {error_detail}")
        else:
            print(f"❌ 错误信息不正确: {error_detail}")
    else:
        print(f"❌ 禁用用户登录应该被拒绝: {login_disabled_response.text}")
    
    time.sleep(1)
    
    # 测试使用禁用用户名注册
    print(f"\n📝 5. 测试使用禁用用户名注册")
    register_response = requests.post(f"{BASE_URL}/auth/register", json={
        "username": user_data["username"],
        "password": "newpassword123",
        "phone": "13900139999"
    })
    
    if register_response.status_code == 400:
        error_detail = register_response.json().get("detail")
        if error_detail == "Username is disabled and cannot be registered":
            print("✅ 使用禁用用户名注册被正确拒绝")
            print(f"   错误信息: {error_detail}")
        else:
            print(f"❌ 错误信息不正确: {error_detail}")
    else:
        print(f"❌ 使用禁用用户名注册应该被拒绝: {register_response.text}")
    
    time.sleep(1)
    
    # 重新激活用户
    print(f"\n✅ 6. 重新激活用户")
    activate_response = requests.post(f"{BASE_URL}/users/{user_id}/activate", headers=headers)
    if activate_response.status_code == 200:
        print("✅ 用户重新激活成功")
    else:
        print(f"❌ 用户重新激活失败: {activate_response.text}")
    
    time.sleep(1)
    
    # 测试重新激活后登录
    print(f"\n🔓 7. 测试重新激活后登录")
    relogin_response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": user_data["username"],
        "password": user_data["password"]
    })
    
    if relogin_response.status_code == 200:
        print("✅ 重新激活后登录成功")
    else:
        print(f"❌ 重新激活后登录失败: {relogin_response.text}")
    
    time.sleep(1)
    
    # 删除用户
    print(f"\n🗑️ 8. 删除用户")
    delete_response = requests.delete(f"{BASE_URL}/users/{user_id}", headers=headers)
    if delete_response.status_code == 200:
        print("✅ 用户删除成功")
    else:
        print(f"❌ 用户删除失败: {delete_response.text}")
    
    time.sleep(1)
    
    # 验证用户已删除
    print(f"\n🔍 9. 验证用户已删除")
    verify_response = requests.get(f"{BASE_URL}/users/{user_id}", headers=headers)
    if verify_response.status_code == 404:
        print("✅ 用户已成功删除")
    else:
        print(f"❌ 用户删除验证失败: {verify_response.text}")

def demo_self_delete_prevention():
    """演示防止用户删除自己"""
    print("\n" + "=" * 60)
    print("🛡️ 防止自删除演示")
    print("=" * 60)
    
    admin_token = get_auth_token()
    if not admin_token:
        print("❌ 无法获取管理员权限")
        return
    
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }
    
    # 获取当前管理员用户信息
    print("\n👤 1. 获取当前用户信息")
    me_response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    if me_response.status_code == 200:
        admin_user = me_response.json()
        admin_id = admin_user['id']
        print(f"✅ 当前用户ID: {admin_id}")
        print(f"   用户名: {admin_user['username']}")
        print(f"   用户类型: {admin_user['user_type']}")
    else:
        print(f"❌ 获取用户信息失败: {me_response.text}")
        return
    
    time.sleep(1)
    
    # 尝试删除自己
    print(f"\n🚫 2. 尝试删除自己")
    delete_response = requests.delete(f"{BASE_URL}/users/{admin_id}", headers=headers)
    
    if delete_response.status_code == 400:
        error_detail = delete_response.json().get("detail")
        if error_detail == "Cannot delete yourself":
            print("✅ 防止用户删除自己功能正常")
            print(f"   错误信息: {error_detail}")
        else:
            print(f"❌ 错误信息不正确: {error_detail}")
    else:
        print(f"❌ 应该防止用户删除自己: {delete_response.text}")

def demo_user_management():
    """演示用户管理功能"""
    print("\n" + "=" * 60)
    print("👥 用户管理功能演示")
    print("=" * 60)
    
    admin_token = get_auth_token()
    if not admin_token:
        print("❌ 无法获取管理员权限")
        return
    
    headers = {
        "Authorization": f"Bearer {admin_token}"
    }
    
    # 获取用户列表
    print("\n📋 1. 获取用户列表")
    users_response = requests.get(f"{BASE_URL}/users/", headers=headers)
    if users_response.status_code == 200:
        users = users_response.json()
        print(f"✅ 获取用户列表成功，共 {len(users)} 个用户")
        for user in users[:5]:  # 只显示前5个
            status = "激活" if user['is_active'] else "禁用"
            phone = user['phone'] if user['phone'] else "未设置"
            print(f"   ID: {user['id']:<3} | 用户名: {user['username']:<15} | 类型: {user['user_type']:<5} | 状态: {status:<4} | 手机号: {phone}")
        if len(users) > 5:
            print(f"   ... 还有 {len(users) - 5} 个用户")
    else:
        print(f"❌ 获取用户列表失败: {users_response.text}")
    
    time.sleep(1)
    
    # 获取包含禁用用户的列表
    print(f"\n📋 2. 获取包含禁用用户的列表")
    users_inactive_response = requests.get(f"{BASE_URL}/users/?include_inactive=true", headers=headers)
    if users_inactive_response.status_code == 200:
        users_inactive = users_inactive_response.json()
        print(f"✅ 获取用户列表成功，共 {users_inactive} 个用户（包含禁用）")
        active_count = sum(1 for user in users_inactive if user['is_active'])
        inactive_count = len(users_inactive) - active_count
        print(f"   激活用户: {active_count} 个")
        print(f"   禁用用户: {inactive_count} 个")
    else:
        print(f"❌ 获取用户列表失败: {users_inactive_response.text}")

def main():
    """主演示函数"""
    print("🎭 用户删除和禁用功能完整演示")
    print("⚠️  请确保服务器正在运行: python start_server.py")
    
    # 检查服务器是否运行
    try:
        response = requests.get(f"{BASE_URL}/docs")
        if response.status_code != 200:
            print("❌ 服务器未运行，请先启动服务器")
            return
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请先启动服务器")
        return
    
    try:
        # 演示用户生命周期
        demo_user_lifecycle()
        
        # 演示防止自删除
        demo_self_delete_prevention()
        
        # 演示用户管理
        demo_user_management()
        
        print("\n" + "=" * 60)
        print("🎉 演示完成！")
        print("\n💡 功能总结:")
        print("- ✅ 支持用户物理删除")
        print("- ✅ 禁用用户无法登录")
        print("- ✅ 禁用用户名/手机号无法注册")
        print("- ✅ 防止用户删除自己")
        print("- ✅ 完整的用户生命周期管理")
        
    except Exception as e:
        print(f"\n❌ 演示过程中出错: {e}")

if __name__ == "__main__":
    main()