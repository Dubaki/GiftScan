"""
Retry logic with exponential backoff for handling transient failures.
"""

import asyncio
import logging
from functools import wraps
from typing import Callable, TypeVar, Any

import aiohttp

logger = logging.getLogger(__name__)

T = TypeVar("T")


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    retry_on: tuple = (aiohttp.ClientError, asyncio.TimeoutError),
):
    """
    Decorator for retrying async functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay cap
        exponential_base: Multiplier for exponential backoff
        retry_on: Tuple of exceptions to retry on

    Usage:
        @retry_with_backoff(max_retries=3)
        async def fetch_data():
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retry_on as exc:
                    last_exception = exc

                    # Don't retry on client errors (4xx except 429)
                    if isinstance(exc, aiohttp.ClientResponseError):
                        if 400 <= exc.status < 500 and exc.status != 429:
                            logger.debug(
                                "%s: Client error %d, not retrying",
                                func.__name__,
                                exc.status,
                            )
                            raise

                    if attempt < max_retries:
                        delay = min(base_delay * (exponential_base ** attempt), max_delay)
                        logger.debug(
                            "%s: Attempt %d/%d failed (%s), retrying in %.1fs",
                            func.__name__,
                            attempt + 1,
                            max_retries,
                            type(exc).__name__,
                            delay,
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.warning(
                            "%s: All %d attempts failed: %s",
                            func.__name__,
                            max_retries + 1,
                            last_exception,
                        )

            # If we get here, all retries failed
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


async def retry_async(
    func: Callable[..., T],
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    **kwargs,
) -> T:
    """
    Programmatic retry function (alternative to decorator).

    Usage:
        result = await retry_async(fetch_data, slug="example", max_retries=3)
    """
    retry_decorator = retry_with_backoff(max_retries=max_retries, base_delay=base_delay)
    retried_func = retry_decorator(func)
    return await retried_func(*args, **kwargs)
