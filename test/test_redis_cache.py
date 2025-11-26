#!/usr/bin/env python3
"""
Redis缓存功能测试脚本
运行此脚本前请确保：
1. Redis服务已启动
2. 已安装redis包：pip install redis
3. .env文件中已配置REDIS_URL
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.cache import cache, CacheTTL
from app.config import settings

def test_redis_connection():
    """测试Redis连接"""
    print("=== 测试Redis连接 ===")
    print(f"Redis URL: {settings.redis_url}")
    
    if cache.is_available():
        print("✅ Redis连接成功")
        
        # 获取Redis信息
        try:
            info = cache.redis_client.info()
            print(f"Redis版本: {info.get('redis_version')}")
            print(f"已使用内存: {info.get('used_memory_human')}")
        except Exception as e:
            print(f"获取Redis信息失败: {e}")
    else:
        print("❌ Redis连接失败")
        return False
    
    return True

def test_basic_cache_operations():
    """测试基本缓存操作"""
    print("\n=== 测试基本缓存操作 ===")
    
    # 测试设置和获取
    test_key = "test:key"
    test_value = {"message": "Hello Redis!", "timestamp": 1234567890}
    
    # 设置缓存
    if cache.set(test_key, test_value, CacheTTL.ONE_MINUTE):
        print(f"✅ 成功设置缓存: {test_key}")
    else:
        print(f"❌ 设置缓存失败: {test_key}")
        return False
    
    # 获取缓存
    cached_value = cache.get(test_key)
    if cached_value == test_value:
        print(f"✅ 成功获取缓存: {test_key}")
        print(f"   缓存值: {cached_value}")
    else:
        print(f"❌ 获取缓存失败: {test_key}")
        return False
    
    # 删除缓存
    if cache.delete(test_key):
        print(f"✅ 成功删除缓存: {test_key}")
    else:
        print(f"❌ 删除缓存失败: {test_key}")
    
    # 验证删除
    deleted_value = cache.get(test_key)
    if deleted_value is None:
        print(f"✅ 缓存已成功删除: {test_key}")
    else:
        print(f"❌ 缓存删除失败: {test_key}")
        return False
    
    return True

def test_cache_ttl():
    """测试缓存TTL"""
    print("\n=== 测试缓存TTL ===")
    
    test_key = "test:ttl"
    test_value = {"message": "This will expire"}
    
    # 设置2秒过期的缓存
    if cache.set(test_key, test_value, 2):
        print(f"✅ 设置2秒过期缓存: {test_key}")
        
        # 立即获取
        value = cache.get(test_key)
        if value:
            print("✅ 缓存立即可获取")
        else:
            print("❌ 缓存立即可获取失败")
            return False
        
        # 等待3秒后获取
        import time
        print("等待3秒...")
        time.sleep(3)
        
        value = cache.get(test_key)
        if value is None:
            print("✅ 缓存已正确过期")
        else:
            print("❌ 缓存未过期")
            return False
    else:
        print(f"❌ 设置TTL缓存失败: {test_key}")
        return False
    
    return True

def test_pattern_deletion():
    """测试模式删除"""
    print("\n=== 测试模式删除 ===")
    
    # 创建多个测试键
    test_keys = [
        ("test:pattern:1", {"value": 1}),
        ("test:pattern:2", {"value": 2}),
        ("test:other:1", {"value": 3}),
    ]
    
    # 设置测试缓存
    for key, value in test_keys:
        cache.set(key, value, CacheTTL.ONE_MINUTE)
    
    print("设置了3个测试缓存键")
    
    # 删除匹配模式的缓存
    deleted_count = cache.delete_pattern("test:pattern:*")
    print(f"删除了 {deleted_count} 个匹配 'test:pattern:*' 的缓存")
    
    # 验证删除结果
    remaining_pattern = cache.get("test:pattern:1")
    remaining_other = cache.get("test:other:1")
    
    if remaining_pattern is None and remaining_other is not None:
        print("✅ 模式删除功能正常")
        # 清理剩余缓存
        cache.delete("test:other:1")
        return True
    else:
        print("❌ 模式删除功能异常")
        return False

def main():
    """主测试函数"""
    print("Redis缓存功能测试开始\n")
    
    tests = [
        test_redis_connection,
        test_basic_cache_operations,
        test_cache_ttl,
        test_pattern_deletion,
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ 测试 {test_func.__name__} 出现异常: {e}")
    
    print(f"\n=== 测试结果 ===")
    print(f"通过: {passed}/{total}")
    
    if passed == total:
        print("🎉 所有测试通过！Redis缓存功能正常")
        return True
    else:
        print("⚠️ 部分测试失败，请检查Redis配置")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)