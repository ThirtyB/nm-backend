from sqlalchemy import create_engine, MetaData, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.access_logger import log_database_access, generate_query_hash, get_client_ip
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
    start_time = conn.info.get('query_start_time', []).pop()
    execution_time = int((time.time() - start_time) * 1000)
    
    try:
        # 跳过日志表的记录，避免无限循环
        sql = str(clauseelement).upper()
        if "REDIS_ACCESS_LOG" in sql or "DATABASE_ACCESS_LOG" in sql:
            return
            
        # 获取SQL语句和表名
        try:
            compiled_sql = str(clauseelement.compile(compile_kwargs={"literal_binds": True}))
        except:
            compiled_sql = str(clauseelement)
        
        # 提取表名
        table_name = "unknown"
        try:
            if hasattr(clauseelement, 'table') and clauseelement.table:
                table_name = clauseelement.table.name
            elif hasattr(clauseelement, 'froms') and clauseelement.froms:
                first_from = clauseelement.froms[0]
                if hasattr(first_from, 'name'):
                    table_name = first_from.name
                else:
                    table_name = str(first_from).split()[0] if first_from else "unknown"
        except Exception as table_error:
            logger.debug(f"提取表名失败: {table_error}")
            table_name = "unknown"
        
        # 确定操作类型
        operation = "SELECT"
        try:
            if hasattr(clauseelement, 'type'):
                operation = str(clauseelement.type).upper()
            elif "INSERT" in compiled_sql.upper():
                operation = "INSERT"
            elif "UPDATE" in compiled_sql.upper():
                operation = "UPDATE"
            elif "DELETE" in compiled_sql.upper():
                operation = "DELETE"
            elif "CREATE" in compiled_sql.upper():
                operation = "CREATE"
            elif "DROP" in compiled_sql.upper():
                operation = "DROP"
            elif "ALTER" in compiled_sql.upper():
                operation = "ALTER"
        except Exception as op_error:
            logger.debug(f"提取操作类型失败: {op_error}")
            operation = "UNKNOWN"
        
        # 获取影响的行数
        affected_rows = None
        try:
            if hasattr(result, 'rowcount'):
                affected_rows = result.rowcount
        except Exception as rows_error:
            logger.debug(f"获取影响行数失败: {rows_error}")
        
        # 生成查询hash
        try:
            query_hash = generate_query_hash(compiled_sql)
        except Exception as hash_error:
            logger.debug(f"生成查询hash失败: {hash_error}")
            query_hash = None
        
        # 异步记录日志
        try:
            db = SessionLocal()
            log_database_access(
                db=db,
                operation=operation,
                table_name=table_name,
                execution_time_ms=execution_time,
                status="success",
                affected_rows=affected_rows,
                query_hash=query_hash
            )
            db.close()
        except Exception as log_error:
            logger.error(f"记录数据库访问日志失败: {log_error}")
            
    except Exception as e:
        logger.error(f"数据库访问日志处理失败: {e}")
        logger.debug(f"详细的错误信息: {type(e).__name__}: {e}")

@event.listens_for(engine, "handle_error")
def handle_error(exception_context):
    try:
        # 跳过日志表的错误记录，避免无限循环
        sql = str(exception_context.statement).upper()
        if "REDIS_ACCESS_LOG" in sql or "DATABASE_ACCESS_LOG" in sql:
            return
            
        # 记录错误日志
        try:
            compiled_sql = str(exception_context.statement.compile(compile_kwargs={"literal_binds": True}))
        except:
            compiled_sql = str(exception_context.statement)
        
        # 提取表名
        table_name = "unknown"
        try:
            if hasattr(exception_context.statement, 'table') and exception_context.statement.table:
                table_name = exception_context.statement.table.name
            elif hasattr(exception_context.statement, 'froms') and exception_context.statement.froms:
                first_from = exception_context.statement.froms[0]
                if hasattr(first_from, 'name'):
                    table_name = first_from.name
                else:
                    table_name = str(first_from).split()[0] if first_from else "unknown"
        except Exception as table_error:
            logger.debug(f"提取表名失败: {table_error}")
            table_name = "unknown"
        
        # 确定操作类型
        operation = "SELECT"
        try:
            if hasattr(exception_context.statement, 'type'):
                operation = str(exception_context.statement.type).upper()
            elif "INSERT" in compiled_sql.upper():
                operation = "INSERT"
            elif "UPDATE" in compiled_sql.upper():
                operation = "UPDATE"
            elif "DELETE" in compiled_sql.upper():
                operation = "DELETE"
            elif "CREATE" in compiled_sql.upper():
                operation = "CREATE"
            elif "DROP" in compiled_sql.upper():
                operation = "DROP"
            elif "ALTER" in compiled_sql.upper():
                operation = "ALTER"
        except Exception as op_error:
            logger.debug(f"提取操作类型失败: {op_error}")
            operation = "UNKNOWN"
        
        # 生成查询hash
        try:
            query_hash = generate_query_hash(compiled_sql)
        except Exception as hash_error:
            logger.debug(f"生成查询hash失败: {hash_error}")
            query_hash = None
        
        # 记录错误日志
        try:
            db = SessionLocal()
            log_database_access(
                db=db,
                operation=operation,
                table_name=table_name,
                status="failed",
                error_message=str(exception_context.original_exception),
                query_hash=query_hash
            )
            db.close()
        except Exception as log_error:
            logger.error(f"记录数据库错误日志失败: {log_error}")
            
    except Exception as e:
        logger.error(f"数据库错误日志处理失败: {e}")
        logger.debug(f"详细的错误信息: {type(e).__name__}: {e}")