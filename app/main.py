from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from app.database import engine, Base
from app.routers import auth, users, node_monitor, alert_management, scoring, heartbeat

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

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(node_monitor.router)
app.include_router(alert_management.router)
app.include_router(scoring.router)
app.include_router(heartbeat.router)

@app.get("/")
async def root():
    return {"message": "资源监视器后端API运行中"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}