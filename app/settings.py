# app/settings.py
from pydantic import BaseSettings

class Settings(BaseSettings):
    REDIS_URL: str = "redis://redis:6379/0"
    BROKER_URL: str = "redis://redis:6379/1"
    RESULT_BACKEND: str = "redis://redis:6379/2"
    STORAGE_LOCAL_PATH: str = "/data/storage"
    S3_BUCKET: str | None = None
    ADMIN_WEBHOOK: str | None = None  # call to notify human operator
    PLAYWRIGHT_HEADLESS: bool = True

    class Config:
        env_file = ".env"

settings = Settings()