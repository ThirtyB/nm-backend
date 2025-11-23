#!/usr/bin/env python3
"""
测试简化的服务访问日志功能
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from app.database import SessionLocal
from app.models import ServiceAccessLog
from app.access_logger import log_service_access, log_database_access, log_redis_access
from app.config import settings
from datetime import datetime, timedelta
from urllib.parse import urlparse

def test_log_functions():
    """测试日志记录函数"""
    print("🧪 测试服务访问日志记录功能...")
    
    db = SessionLocal()
    try:
        # 测试直接记录服务访问日志
        print("\n1. 测试直接记录服务访问日志:")
        log_service_access(db, 'database', '10.1.11.129')
        log_service_access(db, 'redis', '10.1.11.128')
        print("✅ 直接记录服务访问日志成功")
        
        # 测试数据库访问日志
        print("\n2. 测试数据库访问日志:")
        log_database_access(db)
        print("✅ 数据库访问日志记录成功")
        
        # 测试Redis访问日志
        print("\n3. 测试Redis访问日志:")
        log_redis_access(db)
        print("✅ Redis访问日志记录成功")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

def check_database_records():
    """检查数据库记录"""
    print("\n📊 检查数据库记录...")
    
    db = SessionLocal()
    try:
        # 查询最近10分钟的记录
        ten_minutes_ago = datetime.utcnow() - timedelta(minutes=10)
        recent_records = db.query(ServiceAccessLog).filter(
            ServiceAccessLog.access_time >= ten_minutes_ago
        ).order_by(ServiceAccessLog.access_time.desc()).limit(10).all()
        
        print(f"最近10分钟内的记录数: {len(recent_records)}")
        
        for record in recent_records:
            print(f"  - 客户端IP: {record.client_ip}, 服务IP: {record.service_ip}, "
                  f"服务类型: {record.service_type}, 时间: {record.access_time}")
        
        # 检查IP地址是否为真实地址
        print(f"\n🔍 IP地址检查:")
        print(f"配置的Redis URL: {settings.redis_url}")
        print(f"配置的数据库URL: {settings.database_url}")
        
        redis_ip = urlparse(settings.redis_url).hostname
        db_ip = urlparse(settings.database_url).hostname
        
        print(f"提取的Redis IP: {redis_ip}")
        print(f"提取的数据库IP: {db_ip}")
        
        # 检查是否有127.0.0.1的记录
        localhost_records = db.query(ServiceAccessLog).filter(
            ServiceAccessLog.client_ip.in_(['127.0.0.1', 'localhost', 'unknown'])
        ).count()
        
        if localhost_records > 0:
            print(f"⚠️  发现 {localhost_records} 条127.0.0.1/localhost/unknown记录")
        else:
            print("✅ 没有发现127.0.0.1/localhost/unknown记录")
            
    finally:
        db.close()

def main():
    """主测试函数"""
    print("🚀 开始测试简化版服务访问日志功能")
    
    try:
        # 测试日志记录功能
        test_log_functions()
        
        # 检查数据库记录
        check_database_records()
        
        print("\n✅ 测试完成！")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()