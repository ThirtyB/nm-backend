#!/usr/bin/env python3
"""
测试心跳检查器功能
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from app.heartbeat_checker import heartbeat_checker
from app.database import SessionLocal
from app.models import ServiceHeartbeat
from datetime import datetime, timedelta

async def test_heartbeat_checker():
    """测试心跳检查器"""
    print("🧪 开始测试心跳检查器...")
    
    # 执行一次检查
    await heartbeat_checker.check_all_services()
    
    # 检查数据库中是否有记录
    db = SessionLocal()
    try:
        # 查询最近5分钟内的记录
        five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
        recent_records = db.query(ServiceHeartbeat).filter(
            ServiceHeartbeat.report_time >= five_minutes_ago
        ).all()
        
        print(f"\n📊 最近5分钟内的心跳记录数: {len(recent_records)}")
        
        for record in recent_records:
            print(f"  - 服务: {record.service_name}, IP: {record.ip_address}, 时间: {record.report_time}")
        
        if len(recent_records) > 0:
            print("✅ 心跳检查器测试成功！")
        else:
            print("❌ 心跳检查器测试失败，没有找到记录")
            
    finally:
        db.close()

def test_individual_functions():
    """测试各个功能函数"""
    print("\n🔧 测试各个功能函数...")
    
    # 测试获取本机IP
    local_ip = heartbeat_checker.get_local_ip()
    print(f"📍 本机IP: {local_ip}")
    
    # 测试从URL提取IP
    from app.config import settings
    redis_ip = heartbeat_checker.extract_ip_from_url(settings.redis_url)
    database_ip = heartbeat_checker.extract_ip_from_url(settings.database_url)
    print(f"🔗 Redis IP: {redis_ip}")
    print(f"🗄️  数据库IP: {database_ip}")
    
    # 测试连接
    redis_alive = heartbeat_checker.test_redis_connection(settings.redis_url)
    database_alive = heartbeat_checker.test_database_connection(settings.database_url)
    print(f"❤️  Redis连接状态: {'✅ 正常' if redis_alive else '❌ 异常'}")
    print(f"💾 数据库连接状态: {'✅ 正常' if database_alive else '❌ 异常'}")

async def main():
    """主测试函数"""
    try:
        # 测试各个功能函数
        test_individual_functions()
        
        # 测试完整的心跳检查
        await test_heartbeat_checker()
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())