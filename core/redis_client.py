import redis.asyncio as redis
from typing import Optional
import json
import os
import logging

logger = logging.getLogger(__name__)

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")


# Create async Redis client directly - DON'T wrap in function during initialization
if REDIS_URL:
    logger.info("🔗 Using Redis URL connection")
    redis_client = redis.from_url(
        REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True,
        max_connections=50,
    )
else:
    logger.info(f"🔗 Using Redis local connection: {REDIS_HOST}:{REDIS_PORT}")
    # Construct connection string
    if REDIS_PASSWORD:
        redis_url = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    else:
        redis_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    
    redis_client = redis.from_url(
        redis_url,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True,
        max_connections=50,
    )


async def test_redis_connection() -> bool:
    """Test Redis connection on startup"""
    try:
        # This will now properly await
        ping_result=await redis_client.execute_command('PING')
        logger.info(f"✅ Redis ping successful: {ping_result}")
        
        # Test read/write
        await redis_client.set("test_key", "test_value", ex=10)
        value = await redis_client.get("test_key")
        
        if value == "test_value":
            logger.info("✅ Redis read/write test successful")
            logger.info(f"📍 Redis location: {'Remote (URL)' if REDIS_URL else f'Local ({REDIS_HOST}:{REDIS_PORT})'}")
            return True
        else:
            logger.warning("⚠️  Redis read/write test failed")
            return False
            
    except redis.ConnectionError as e:
        logger.error(f"❌ Redis connection failed: {e}")
        logger.warning("⚠️  Caching will be disabled")
        return False
    except Exception as e:
        logger.error(f"❌ Redis error: {e}")
        logger.warning(f"⚠️  Error type: {type(e).__name__}")
        return False


async def close_redis_connection():
    """Close Redis connection"""
    try:
        await redis_client.aclose()
        logger.info("✅ Redis connection closed")
    except Exception as e:
        logger.error(f"❌ Error closing Redis: {e}")


class RedisCache:
    """Async Redis cache helper class"""
    
    @staticmethod
    async def get(key: str) -> Optional[dict]:
        """Get value from cache"""
        try:
            cached = await redis_client.get(key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.error(f"Redis GET error for key '{key}': {e}")
        return None
    
    @staticmethod
    async def set(key: str, value: dict, ttl: int = 300):
        """Set value in cache with TTL (seconds)"""
        try:
            await redis_client.setex(key, ttl, json.dumps(value))
        except Exception as e:
            logger.error(f"Redis SET error for key '{key}': {e}")
    
    @staticmethod
    async def delete(key: str):
        """Delete key from cache"""
        try:
            await redis_client.delete(key)
        except Exception as e:
            logger.error(f"Redis DELETE error for key '{key}': {e}")
    
    @staticmethod
    async def clear_pattern(pattern: str):
        """Delete all keys matching pattern"""
        try:
            cursor = 0
            keys_to_delete = []
            
            while True:
                cursor, keys = await redis_client.scan(cursor, match=pattern, count=100)
                keys_to_delete.extend(keys)
                if cursor == 0:
                    break
            
            if keys_to_delete:
                await redis_client.delete(*keys_to_delete)
                logger.info(f"🗑️  Cleared {len(keys_to_delete)} keys matching pattern: {pattern}")
        except Exception as e:
            logger.error(f"Redis CLEAR error for pattern '{pattern}': {e}")
    
    @staticmethod
    async def exists(key: str) -> bool:
        """Check if key exists"""
        try:
            result = await redis_client.exists(key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis EXISTS error for key '{key}': {e}")
            return False
    
    @staticmethod
    async def get_ttl(key: str) -> int:
        """Get TTL for key in seconds"""
        try:
            return await redis_client.ttl(key)
        except Exception as e:
            logger.error(f"Redis TTL error for key '{key}': {e}")
            return -2


class CacheService:
    """Generic cache service for entities"""
    
    @staticmethod
    def _get_cache_key(entity_type: str, entity_id: int) -> str:
        """Generate cache key for entity"""
        return f"{entity_type}:{entity_id}"
    
    @staticmethod
    async def get(entity_type: str, entity_id: int) -> Optional[dict]:
        """Get entity from cache"""
        key = CacheService._get_cache_key(entity_type, entity_id)
        return await RedisCache.get(key)
    
    @staticmethod
    async def set(entity_type: str, entity_id: int, data: dict, ttl: int = 300):
        """Cache entity data"""
        key = CacheService._get_cache_key(entity_type, entity_id)
        await RedisCache.set(key, data, ttl)
    
    @staticmethod
    async def invalidate(entity_type: str, entity_id: int):
        """Invalidate entity cache"""
        key = CacheService._get_cache_key(entity_type, entity_id)
        await RedisCache.delete(key)
    
    @staticmethod
    async def invalidate_pattern(pattern: str):
        """Invalidate all caches matching pattern"""
        await RedisCache.clear_pattern(pattern)
