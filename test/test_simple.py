#!/usr/bin/env python3
"""
简单测试脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from app.database import get_db
from app.models import ServiceHeartbeat
from app.routers.heartbeat import get_service_status_internal
from app.auth import authenticate_user

def test_basic_functionality():
    """测试基本功能"""
    print("开始基本功能测试...")
    
    # 创建数据库会话
    db = next(get_db())
    
    # 测试认证
    print("1. 测试认证...")
    user = authenticate_user(db, 'admin', 'admin123')
    if user:
        print(f"   认证成功: {user.username}, 类型: {user.user_type}")
    else:
        print("   认证失败")
        return
    
    # 测试服务状态查询
    print("2. 测试服务状态查询...")
    start_datetime = datetime.now() - timedelta(hours=1)
    end_datetime = datetime.now()
    
    try:
        service_status = get_service_status_internal(
            start_datetime, end_datetime, db, user
        )
        print("   服务状态查询成功")
        print(f"   数据采集: {len(service_status.data_collection)} 个服务")
        print(f"   kafka进程: {len(service_status.kafka_process)} 个服务")
        print(f"   redis: {len(service_status.redis)} 个服务")
        print(f"   前端: {len(service_status.frontend)} 个服务")
        print(f"   后端: {len(service_status.backend)} 个服务")
        print(f"   数据库连接: {service_status.database.is_connected}")
        
        # 显示具体服务信息
        for service in service_status.data_collection:
            print(f"     - {service.service_name} ({service.ip_address}): {'在线' if service.is_online else '离线'}")
            
    except Exception as e:
        print(f"   服务状态查询失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("测试完成")

if __name__ == "__main__":
    test_basic_functionality()