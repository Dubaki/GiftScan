"""
Rate limiter for API requests using token bucket algorithm.
"""

import asyncio
import time
from collections import defaultdict
from typing import Optional


class RateLimiter:
    """
    Token bucket rate limiter for controlling API request rates.

    Usage:
        limiter = RateLimiter(max_requests=10, window_sec=1.0)
        async with limiter.acquire("tonapi"):
            # Make API request
            ...
    """

    def __init__(self, max_requests: int, window_sec: float = 1.0):
        """
        Args:
            max_requests: Maximum requests allowed per window
            window_sec: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_sec = window_sec
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def acquire(self, key: str = "default") -> "RateLimiterContext":
        """
        Acquire permission to make a request. Blocks if rate limit exceeded.

        Args:
            key: Identifier for separate rate limit buckets (e.g., "tonapi", "portals")
        """
        return RateLimiterContext(self, key)


class RateLimiterContext:
    """Async context manager for rate limiting."""

    def __init__(self, limiter: RateLimiter, key: str):
        self.limiter = limiter
        self.key = key

    async def __aenter__(self):
        async with self.limiter._locks[self.key]:
            now = time.time()
            bucket = self.limiter._buckets[self.key]

            # Remove expired timestamps
            cutoff = now - self.limiter.window_sec
            bucket[:] = [ts for ts in bucket if ts > cutoff]

            # If at limit, wait until oldest request expires
            if len(bucket) >= self.limiter.max_requests:
                sleep_time = bucket[0] - cutoff
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    # Retry after sleep (recursive call)
                    return await self.__aenter__()

            # Add current timestamp
            bucket.append(now)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


# Global rate limiters for common APIs
_limiters: dict[str, RateLimiter] = {}


def get_rate_limiter(name: str, max_requests: int, window_sec: float = 1.0) -> RateLimiter:
    """Get or create a named rate limiter."""
    if name not in _limiters:
        _limiters[name] = RateLimiter(max_requests, window_sec)
    return _limiters[name]
