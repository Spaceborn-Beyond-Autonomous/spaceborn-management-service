import redis.asyncio as redis
from typing import Optional
import json
import os

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# Create async Redis client
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWORD,
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5,
    retry_on_timeout=True
)


async def test_redis_connection():
    """Test Redis connection on startup"""
    try:
        redis_client.ping()
        print("✓ Redis connected successfully")
    except redis.ConnectionError:
        print("✗ Redis connection failed - caching will be disabled")


class RedisCache:
    """Async Redis cache helper class"""
    
    @staticmethod
    async def get(key: str) -> Optional[dict]:
        """Get value from cache"""
        try:
            cached = await redis_client.get(key)  # await the async call
            if cached:
                return json.loads(cached)  # Now cached is a string
        except Exception as e:
            print(f"Redis GET error: {e}")
        return None
    
    @staticmethod
    async def set(key: str, value: dict, ttl: int = 300):
        """Set value in cache with TTL (seconds)"""
        try:
            await redis_client.setex(key, ttl, json.dumps(value))  # await the async call
        except Exception as e:
            print(f"Redis SET error: {e}")
    
    @staticmethod
    async def delete(key: str):
        """Delete key from cache"""
        try:
            await redis_client.delete(key)  # await the async call
        except Exception as e:
            print(f"Redis DELETE error: {e}")
    
    @staticmethod
    async def clear_pattern(pattern: str):
        """Delete all keys matching pattern"""
        try:
            keys = await redis_client.keys(pattern)  # await the async call
            if keys:
                await redis_client.delete(*keys)  # await the async call
        except Exception as e:
            print(f"Redis CLEAR error: {e}")
