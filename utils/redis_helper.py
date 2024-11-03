import os
from redis import Redis, ConnectionError, TimeoutError
from typing import Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RedisHelper:
    _instance = None
    _redis_conn = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisHelper, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._redis_conn is None:
            self._initialize_connection()

    def _initialize_connection(self) -> None:
        """Initialize Redis connection with retries and proper error handling"""
        redis_url = os.environ.get('REDIS_URL')
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                # Use Redis URL if available, otherwise use default local connection
                if redis_url:
                    self._redis_conn = Redis.from_url(redis_url)
                else:
                    self._redis_conn = Redis(
                        host='localhost',
                        port=6379,
                        decode_responses=True,
                        socket_timeout=5,
                        retry_on_timeout=True
                    )
                # Test connection
                self._redis_conn.ping()
                logger.info("Successfully connected to Redis")
                break
            except (ConnectionError, TimeoutError) as e:
                retry_count += 1
                logger.warning(f"Redis connection attempt {retry_count} failed: {str(e)}")
                if retry_count == max_retries:
                    logger.error("Failed to connect to Redis after maximum retries")
                    self._redis_conn = None
                    raise

    def get_connection(self) -> Optional[Redis]:
        """Get Redis connection with automatic reconnection"""
        if self._redis_conn is None:
            try:
                self._initialize_connection()
            except (ConnectionError, TimeoutError) as e:
                logger.error(f"Failed to establish Redis connection: {str(e)}")
                return None
        return self._redis_conn

    def health_check(self) -> bool:
        """Check if Redis connection is healthy"""
        try:
            if self._redis_conn:
                self._redis_conn.ping()
                return True
            return False
        except (ConnectionError, TimeoutError):
            return False
