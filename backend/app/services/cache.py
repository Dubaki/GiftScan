"""
Redis cache service for gift prices.

Caches pre-computed API responses for fast retrieval.
Invalidated after each scan cycle completes.
"""

import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional, Any

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)

# Cache keys
GIFTS_CACHE_KEY = "giftscan:gifts:latest"
SCAN_TIMESTAMP_KEY = "giftscan:scan:timestamp"

# Cache TTL (15 minutes - slightly longer than scan interval)
CACHE_TTL_SECONDS = 900


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal and datetime."""

    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class CacheService:
    """Redis cache for gift price data."""

    _redis: Optional[redis.Redis] = None

    @classmethod
    async def get_redis(cls) -> redis.Redis:
        """Get or create Redis connection."""
        if cls._redis is None:
            cls._redis = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
            )
        return cls._redis

    @classmethod
    async def close(cls):
        """Close Redis connection."""
        if cls._redis is not None:
            await cls._redis.close()
            cls._redis = None

    @classmethod
    async def get_cached_gifts(cls) -> Optional[dict]:
        """
        Get cached gift list response.
        Returns None if cache miss or error.
        """
        try:
            r = await cls.get_redis()
            data = await r.get(GIFTS_CACHE_KEY)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning("Cache get failed: %s", e)
        return None

    @classmethod
    async def set_cached_gifts(cls, response_data: dict):
        """Cache the full gift list response."""
        try:
            r = await cls.get_redis()
            await r.set(
                GIFTS_CACHE_KEY,
                json.dumps(response_data, cls=DecimalEncoder),
                ex=CACHE_TTL_SECONDS,
            )
            await r.set(
                SCAN_TIMESTAMP_KEY,
                datetime.utcnow().isoformat(),
                ex=CACHE_TTL_SECONDS,
            )
            logger.info("Cache updated with %d gifts", len(response_data.get("gifts", [])))
        except Exception as e:
            logger.warning("Cache set failed: %s", e)

    @classmethod
    async def invalidate(cls):
        """Clear the cache after a new scan."""
        try:
            r = await cls.get_redis()
            await r.delete(GIFTS_CACHE_KEY, SCAN_TIMESTAMP_KEY)
            logger.info("Cache invalidated")
        except Exception as e:
            logger.warning("Cache invalidation failed: %s", e)

    @classmethod
    async def get_scan_timestamp(cls) -> Optional[datetime]:
        """Get timestamp of last cached scan."""
        try:
            r = await cls.get_redis()
            ts = await r.get(SCAN_TIMESTAMP_KEY)
            if ts:
                return datetime.fromisoformat(ts)
        except Exception as e:
            logger.debug("Get scan timestamp failed: %s", e)
        return None

    @classmethod
    async def health_check(cls) -> bool:
        """Check if Redis is reachable."""
        try:
            r = await cls.get_redis()
            await r.ping()
            return True
        except Exception:
            return False
