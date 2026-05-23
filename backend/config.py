from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    # ── Application ──
    app_name: str = "MADF"
    debug: bool = True
    cors_origins: str = "http://localhost:5173"

    # ── Database ──
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "madf"
    db_password: str = "madf"
    db_name: str = "madf"

    @property
    def db_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def db_url_sync(self) -> str:
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    # ── Redis ──
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # ── JWT ──
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours

    # ── LLM ──
    llm_api_key: str = ""
    llm_api_base: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o"

    # ── Tavily ──
    tavily_api_key: str = ""


settings = Settings()
