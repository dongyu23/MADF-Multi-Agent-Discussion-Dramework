from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from typing import Optional
import redis
import logging

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        # Allow reading from system environment variables if not found in .env
        case_sensitive=True 
    )

    PROJECT_NAME: str = "MADF User Management API"
    API_V1_STR: str = "/api/v1"
    
    # LLM API Configuration
    API_KEY: Optional[str] = None
    MODEL_NAME: Optional[str] = None
    BASE_URL: Optional[str] = None
    
    @property
    def final_api_key(self) -> str:
        key = self.API_KEY or os.environ.get("API_KEY") or os.environ.get("ZHIPUAI_API_KEY")
        if not key:
            raise ValueError("API_KEY is not set. Please set API_KEY in .env or environment variables.")
        return key

    @property
    def final_model_name(self) -> str:
        return self.MODEL_NAME or os.environ.get("MODEL_NAME") or "glm-4.5"

    @property
    def final_base_url(self) -> str:
        return self.BASE_URL or os.environ.get("BASE_URL") or "https://open.bigmodel.cn/api/paas/v4/"
    
    # Search API Configuration
    SERPAPI_API_KEY: Optional[str] = None
    
    # Security
    SECRET_KEY: str = "MADF_DEFAULT_INSECURE_SECRET_KEY_PLEASE_CHANGE_IN_PROD"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    # Database Configuration
    TURSO_DATABASE_URL: Optional[str] = None
    TURSO_AUTH_TOKEN: Optional[str] = None
    DATABASE_URL_OVERRIDE: Optional[str] = None # Renamed from DATABASE_URL to avoid conflict
    
    # Redis Configuration
    # Default to localhost inside the same container or service mesh
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Determine which database to use
    @property
    def DATABASE_URL(self) -> str:
        # 1. Check environment variable DATABASE_URL first
        env_db = os.environ.get("DATABASE_URL")
        if env_db:
            return env_db
            
        # 2. Turso (Legacy support)
        if self.TURSO_DATABASE_URL and self.TURSO_AUTH_TOKEN:
            return self.TURSO_DATABASE_URL
            
        # 3. Local SQLite (Dev/Docker default)
        if self.DATABASE_URL_OVERRIDE:
             return self.DATABASE_URL_OVERRIDE
        
        return "file:madf.db"

settings = Settings()

# Global Redis Client
redis_client: Optional[redis.Redis] = None

try:
    redis_client = redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5
    )
    redis_client.ping()
    logger.info(f"Redis connected to {settings.REDIS_URL}")
except Exception as e:
    logger.warning(f"Redis connection failed: {e}")
    redis_client = None
