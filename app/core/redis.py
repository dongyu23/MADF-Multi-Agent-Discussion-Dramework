import redis
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class RedisManager:
    _client = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            try:
                cls._client = redis.from_url(
                    settings.REDIS_URL, 
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5
                )
                # Test connection
                cls._client.ping()
                logger.info(f"Connected to Redis at {settings.REDIS_URL}")
            except redis.ConnectionError as e:
                logger.warning(f"Failed to connect to Redis: {e}. Caching will be disabled.")
                cls._client = None
        return cls._client

def get_redis():
    return RedisManager.get_client()
