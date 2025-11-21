from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import auth, users, node_monitor, alert_management, scoring, heartbeat, cache_management
from app.access_logger import set_client_ip

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="资源监视器后端API",
    description="资源监视器系统的用户管理接口",
    version="1.0.0",
    swagger_ui_parameters={
        "persistAuthorization": True,
        "displayRequestDuration": True
    }
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    # 获取客户端IP地址
    client_ip = request.client.host
    if "x-forwarded-for" in request.headers:
        client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
    elif "x-real-ip" in request.headers:
        client_ip = request.headers["x-real-ip"]
    
    # 设置当前请求的客户端IP
    set_client_ip(client_ip)
    
    response = await call_next(request)
    return response

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(node_monitor.router)
app.include_router(alert_management.router)
app.include_router(scoring.router)
app.include_router(heartbeat.router)
app.include_router(cache_management.router)

@app.get("/")
async def root():
    return {"message": "资源监视器后端API运行中"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}