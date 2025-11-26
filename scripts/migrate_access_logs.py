#!/usr/bin/env python3
"""
创建 access_logs 表的迁移脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.config import settings
from app.models import Base

def create_access_logs_table():
    """创建 access_logs 表"""
    try:
        # 创建数据库引擎
        engine = create_engine(settings.database_url)
        
        # 读取 SQL 文件
        with open('access_logs.sql', 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # 执行 SQL
        with engine.connect() as connection:
            # 检查表是否已存在
            result = connection.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'access_logs'
                );
            """))
            
            table_exists = result.fetchone()[0]
            
            if table_exists:
                print("access_logs 表已存在，跳过创建")
                return True
            
            # 创建表
            connection.execute(text(sql_content))
            connection.commit()
            print("access_logs 表创建成功")
            return True
            
    except Exception as e:
        print(f"创建 access_logs 表失败: {e}")
        return False

def main():
    """主函数"""
    print("开始创建 access_logs 表...")
    
    if create_access_logs_table():
        print("迁移完成！")
    else:
        print("迁移失败！")
        sys.exit(1)

if __name__ == "__main__":
    main()