#!/usr/bin/env python3
"""
测试访问日志记录功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine, Base
from app.models import RedisAccessLog, DatabaseAccessLog
from app.cache import cache
from app.access_logger import set_client_ip, log_redis_access, log_database_access
import time

def test_access_logging():
    """测试访问日志记录功能"""
    print("开始测试访问日志记录功能...")
    
    # 创建数据库表
    Base.metadata.create_all(bind=engine)
    print("✓ 数据库表创建完成")
    
    # 设置客户端IP
    set_client_ip("127.0.0.1")
    print("✓ 设置客户端IP为 127.0.0.1")
    
    db = SessionLocal()
    
    try:
        # 测试Redis访问日志
        print("\n--- 测试Redis访问日志 ---")
        
        # 测试设置缓存
        cache.set("test_key", {"data": "test_value"}, expire_seconds=60)
        print("✓ Redis SET操作完成")
        
        # 测试获取缓存
        result = cache.get("test_key")
        print(f"✓ Redis GET操作完成，结果: {result}")
        
        # 测试删除缓存
        cache.delete("test_key")
        print("✓ Redis DELETE操作完成")
        
        # 手动记录一条Redis日志
        log_redis_access(
            db=db,
            operation="MANUAL_TEST",
            redis_key="manual_test_key",
            execution_time_ms=10,
            status="success"
        )
        print("✓ 手动记录Redis日志完成")
        
        # 测试数据库访问日志
        print("\n--- 测试数据库访问日志 ---")
        
        # 手动记录一条数据库日志
        log_database_access(
            db=db,
            operation="MANUAL_TEST",
            table_name="test_table",
            execution_time_ms=15,
            status="success",
            affected_rows=1
        )
        print("✓ 手动记录数据库日志完成")
        
        # 查询日志记录
        print("\n--- 查询日志记录 ---")
        
        redis_logs = db.query(RedisAccessLog).limit(5).all()
        print(f"✓ Redis访问日志记录数: {len(redis_logs)}")
        for log in redis_logs:
            print(f"  - {log.access_time}: {log.operation} {log.redis_key} ({log.status})")
        
        db_logs = db.query(DatabaseAccessLog).limit(5).all()
        print(f"✓ 数据库访问日志记录数: {len(db_logs)}")
        for log in db_logs:
            print(f"  - {log.access_time}: {log.operation} {log.table_name} ({log.status})")
        
        print("\n✅ 访问日志记录功能测试完成!")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_access_logging()