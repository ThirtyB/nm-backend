#!/usr/bin/env python3
"""
启动资源监视器后端服务
"""

import uvicorn
import os
import sys
from pathlib import Path

def check_env_file():
    """检查.env文件是否存在"""
    env_file = Path(".env")
    if not env_file.exists():
        print("⚠️  .env文件不存在，将使用默认配置")
        print("建议创建.env文件并配置以下内容：")
        print("""
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
DATABASE_URL=postgresql://username:password@localhost:5432/dbname
        """)
        return False
    return True

def main():
    print("🚀 启动资源监视器后端服务...")
    
    # 检查环境文件
    check_env_file()
    
    # 启动参数
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "true").lower() == "true"
    
    print(f"📍 服务地址: http://{host}:{port}")
    print(f"📚 API文档: http://{host}:{port}/docs")
    print(f"📚 ReDoc文档: http://{host}:{port}/redoc")
    print(f"🔄 热重载: {'开启' if reload else '关闭'}")
    print()
    
    try:
        # 启动FastAPI应用
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()