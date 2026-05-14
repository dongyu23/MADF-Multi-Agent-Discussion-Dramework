"""Configuration / settings unit tests."""
from backend.config import Settings


class TestSettings:
    def test_default_values(self):
        s = Settings(app_name="MADF", debug=True, db_host="localhost", db_port=5432,
                     jwt_algorithm="HS256", jwt_expire_minutes=1440)
        assert s.app_name == "MADF"
        assert s.debug is True
        assert s.db_host == "localhost"
        assert s.db_port == 5432
        assert s.jwt_algorithm == "HS256"
        assert s.jwt_expire_minutes == 1440

    def test_db_url_asyncpg(self):
        s = Settings(db_user="u", db_password="p", db_host="h", db_port=5432, db_name="d")
        assert s.db_url == "postgresql+asyncpg://u:p@h:5432/d"

    def test_db_url_sync(self):
        s = Settings(db_user="u", db_password="p", db_host="h", db_port=5432, db_name="d")
        assert s.db_url_sync == "postgresql://u:p@h:5432/d"

    def test_redis_url(self):
        s = Settings(redis_host="redis.local", redis_port=6379, redis_db=0)
        assert s.redis_url == "redis://redis.local:6379/0"

    def test_redis_url_custom_db(self):
        s = Settings(redis_host="r", redis_port=6380, redis_db=2)
        assert s.redis_url == "redis://r:6380/2"

    def test_jwt_expire_positive(self):
        s = Settings()
        assert s.jwt_expire_minutes > 0

    def test_cors_origins_comma_separated(self):
        s = Settings(cors_origins="http://a.com,http://b.com")
        origins = [o.strip() for o in s.cors_origins.split(",")]
        assert len(origins) == 2

    def test_llm_defaults_override_env(self):
        s = Settings(llm_model="gpt-4o", llm_api_base="https://api.openai.com/v1", llm_api_key="")
        assert s.llm_model == "gpt-4o"
        assert s.llm_api_base == "https://api.openai.com/v1"
        assert s.llm_api_key == ""
