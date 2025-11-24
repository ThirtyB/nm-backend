from sqlalchemy import create_engine, MetaData, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.access_logger import log_database_access, generate_query_hash, get_client_ip, get_real_ip, get_local_ip
import time
import logging

logger = logging.getLogger(__name__)

# 根据数据库类型决定是否需要connect_args
if settings.database_url.startswith("sqlite"):
    engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
else:
    engine = create_engine(settings.database_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 数据库访问日志监听器
@event.listens_for(engine, "before_execute")
def before_execute(conn, clauseelement, multiparams, params, execution_options):
    conn.info.setdefault('query_start_time', []).append(time.time())
    return clauseelement, multiparams, params

@event.listens_for(engine, "after_execute")
def after_execute(conn, clauseelement, multiparams, params, execution_options, result):
    try:
        # 跳过日志表的记录，避免无限循环
        sql = str(clauseelement).upper()
        if "SERVICE_ACCESS_LOGS" in sql:
            return
        
        # 异步记录简化的数据库访问日志
        try:
            db = SessionLocal()
            backend_ip = get_real_ip(get_local_ip())
            log_database_access(db=db, backend_ip=backend_ip)
            db.close()
        except Exception as log_error:
            logger.error(f"记录数据库访问日志失败: {log_error}")
            
    except Exception as e:
        logger.error(f"数据库访问日志处理失败: {e}")

@event.listens_for(engine, "handle_error")
def handle_error(exception_context):
    try:
        # 跳过日志表的错误记录，避免无限循环
        sql = str(exception_context.statement).upper()
        if "SERVICE_ACCESS_LOGS" in sql:
            return
        
        # 记录简化的数据库日志（即使是错误也记录）
        try:
            db = SessionLocal()
            backend_ip = get_real_ip(get_local_ip())
            log_database_access(db=db, backend_ip=backend_ip)
            db.close()
        except Exception as log_error:
            logger.error(f"记录数据库错误日志失败: {log_error}")
            
    except Exception as e:
        logger.error(f"数据库错误日志处理失败: {e}")