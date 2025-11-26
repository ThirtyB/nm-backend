#!/usr/bin/env python3
"""
手机号加密迁移脚本
将现有的明文手机号迁移到 SM4-GCM 加密存储
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.database import DATABASE_URL
from app.models import User
from app.security.field_encryption import get_field_encryption_service
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def migrate_phone_encryption():
    """迁移手机号到加密存储"""
    logger.info("开始手机号加密迁移...")
    
    # 创建数据库引擎
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # 创建会话
    db = SessionLocal()
    
    try:
        # 检查是否已经包含加密字段
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            AND column_name = 'phone_encrypted'
        """))
        
        if not result.fetchone():
            logger.error("数据库表结构未更新，请先运行 schema.sql")
            return False
        
        # 查询所有用户
        users = db.query(User).all()
        logger.info(f"找到 {len(users)} 个用户")
        
        # 迁移每个用户的手机号
        migrated_count = 0
        skipped_count = 0
        
        for user in users:
            try:
                # 检查是否已经加密
                if user.phone_encrypted is not None:
                    logger.info(f"用户 {user.username} 的手机号已加密，跳过")
                    skipped_count += 1
                    continue
                
                # 检查是否有明文手机号
                if user.phone is None or user.phone.strip() == "":
                    logger.info(f"用户 {user.username} 没有手机号，跳过")
                    skipped_count += 1
                    continue
                
                # 加密手机号
                logger.info(f"正在迁移用户 {user.username} 的手机号...")
                user.set_phone_encrypted(user.phone)
                
                # 清空明文字段
                user.phone = None
                
                migrated_count += 1
                logger.info(f"用户 {user.username} 的手机号迁移成功")
                
            except Exception as e:
                logger.error(f"迁移用户 {user.username} 的手机号失败: {e}")
                continue
        
        # 提交更改
        db.commit()
        logger.info(f"迁移完成！成功迁移 {migrated_count} 个用户，跳过 {skipped_count} 个用户")
        
        return True
        
    except Exception as e:
        logger.error(f"迁移过程中发生错误: {e}")
        db.rollback()
        return False
        
    finally:
        db.close()


def verify_migration():
    """验证迁移结果"""
    logger.info("开始验证迁移结果...")
    
    # 创建数据库引擎
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # 创建会话
    db = SessionLocal()
    
    try:
        # 统计信息
        total_users = db.query(User).count()
        encrypted_users = db.query(User).filter(User.phone_encrypted.isnot(None)).count()
        plain_phone_users = db.query(User).filter(User.phone.isnot(None)).count()
        
        logger.info(f"总用户数: {total_users}")
        logger.info(f"已加密手机号用户数: {encrypted_users}")
        logger.info(f"仍有明文手机号用户数: {plain_phone_users}")
        
        # 测试解密
        test_users = db.query(User).filter(User.phone_encrypted.isnot(None)).limit(3).all()
        for user in test_users:
            try:
                decrypted_phone = user.phone_decrypted
                logger.info(f"用户 {user.username} 解密测试成功: {decrypted_phone}")
            except Exception as e:
                logger.error(f"用户 {user.username} 解密测试失败: {e}")
        
        logger.info("验证完成")
        
    except Exception as e:
        logger.error(f"验证过程中发生错误: {e}")
        
    finally:
        db.close()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='手机号加密迁移工具')
    parser.add_argument(
        '--migrate', 
        action='store_true',
        help='执行手机号加密迁移'
    )
    parser.add_argument(
        '--verify', 
        action='store_true',
        help='验证迁移结果'
    )
    parser.add_argument(
        '--all', 
        action='store_true',
        help='执行迁移和验证'
    )
    
    args = parser.parse_args()
    
    if not any([args.migrate, args.verify, args.all]):
        parser.print_help()
        return
    
    try:
        if args.migrate or args.all:
            success = migrate_phone_encryption()
            if not success:
                logger.error("迁移失败")
                sys.exit(1)
        
        if args.verify or args.all:
            verify_migration()
        
        logger.info("操作完成")
        
    except KeyboardInterrupt:
        logger.info("操作被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"操作失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()