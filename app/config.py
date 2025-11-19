from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24小时
    database_url: str
    
    class Config:
        env_file = ".env"

settings = Settings()