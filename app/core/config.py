from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    PROJECT_NAME: str = "MADF User Management API"
    API_V1_STR: str = "/api/v1"
    
    # LLM API Configuration
    API_KEY: str
    MODEL_NAME: str = "glm-4.6"
    BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4/"
    
    # Search API Configuration
    SERPAPI_API_KEY: Optional[str] = None
    
    # Security
    # In production, this should be set via environment variable.
    # For dev/convenience, we default to a hardcoded insecure key if not provided.
    SECRET_KEY: str = "MADF_DEFAULT_INSECURE_SECRET_KEY_PLEASE_CHANGE_IN_PROD"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    # Database Configuration
    TURSO_DATABASE_URL: Optional[str] = None
    TURSO_AUTH_TOKEN: Optional[str] = None
    DATABASE_URL_OVERRIDE: Optional[str] = None # Renamed from DATABASE_URL to avoid conflict
    
    # Determine which database to use
    @property
    def DATABASE_URL(self) -> str:
        # 1. Turso (Remote)
        if self.TURSO_DATABASE_URL and self.TURSO_AUTH_TOKEN:
            return self.TURSO_DATABASE_URL
            
        # 2. Local SQLite (Dev/Docker)
        # Check environment variable first for override
        # Pydantic loads DATABASE_URL_OVERRIDE from env var DATABASE_URL_OVERRIDE
        # But we also want to support standard DATABASE_URL env var if user sets it directly
        if self.DATABASE_URL_OVERRIDE:
             return self.DATABASE_URL_OVERRIDE
        
        # Fallback to direct env check for DATABASE_URL if Pydantic didn't catch it 
        # (though Pydantic usually prefers exact field names, so DATABASE_URL env var might be ignored if no field matches)
        # Let's check os.environ directly for backward compat or Docker convenience
        env_db = os.environ.get("DATABASE_URL")
        if env_db:
            return env_db
            
        return "file:madf.db"

settings = Settings()
