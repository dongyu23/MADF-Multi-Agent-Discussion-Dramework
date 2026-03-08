from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "MADF User Management API"
    API_V1_STR: str = "/api/v1"
    
    # Database Configuration
    TURSO_DATABASE_URL: str | None = os.environ.get("TURSO_DATABASE_URL")
    TURSO_AUTH_TOKEN: str | None = os.environ.get("TURSO_AUTH_TOKEN")
    
    # Determine which database to use
    @property
    def DATABASE_URL(self) -> str:
        # 1. Turso (Remote)
        if self.TURSO_DATABASE_URL and self.TURSO_AUTH_TOKEN:
            return self.TURSO_DATABASE_URL
            
        # 2. Local SQLite (Dev/Docker)
        # Check environment variable first for override
        env_db_url = os.environ.get("DATABASE_URL")
        if env_db_url:
            return env_db_url
            
        return "file:madf.db"

    class Config:
        case_sensitive = True

settings = Settings()
