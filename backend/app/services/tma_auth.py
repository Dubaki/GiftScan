"""
TMA (Telegram Mini App) authentication token generator.

Auto-generates authorization tokens for Telegram Mini App marketplaces
(e.g., Portals) using Telethon. Falls back to manual token from settings.

Token format: "tma <initData>" where initData is the web app auth string.
"""

import asyncio
import logging
import time
from typing import Optional
from urllib.parse import unquote, urlparse, parse_qs

from app.core.config import settings

logger = logging.getLogger(__name__)

# Cached token state
_token_cache: dict[str, dict] = {}

# Token refresh interval (12 hours)
TOKEN_TTL_SEC = 12 * 3600


async def get_portals_auth_token() -> str:
    """
    Get Portals TMA auth token.

    Priority:
    1. Cached token (if not expired)
    2. Auto-generated via Telethon (if credentials configured)
    3. Manual token from settings.PORTALS_AUTH_TOKEN

    Returns:
        Auth token string (without "tma " prefix) or empty string if unavailable.
    """
    cache_key = "portals"

    # Check cache
    if cache_key in _token_cache:
        cached = _token_cache[cache_key]
        if time.time() - cached["timestamp"] < TOKEN_TTL_SEC:
            logger.debug("Portals: Using cached TMA token (age: %.0fs)", time.time() - cached["timestamp"])
            return cached["token"]
        logger.info("Portals: Cached TMA token expired, refreshing")

    # Try auto-generation via Telethon
    if settings.TELEGRAM_API_ID and settings.TELEGRAM_API_HASH and settings.TELEGRAM_PHONE:
        token = await _generate_token_telethon()
        if token:
            _token_cache[cache_key] = {"token": token, "timestamp": time.time()}
            logger.info("Portals: TMA token auto-generated via Telethon")
            return token

    # Fallback to manual token
    if settings.PORTALS_AUTH_TOKEN:
        logger.info("Portals: Using manual PORTALS_AUTH_TOKEN from settings")
        return settings.PORTALS_AUTH_TOKEN

    logger.warning("Portals: No auth token available (configure Telethon credentials or PORTALS_AUTH_TOKEN)")
    return ""


async def _generate_token_telethon() -> Optional[str]:
    """
    Generate TMA initData using Telethon by requesting web app view
    for @portals_ton_bot.

    Returns initData string or None on failure.
    """
    try:
        from telethon import TelegramClient
        from telethon.tl.functions.messages import RequestWebViewRequest
        from telethon.tl.types import InputBotAppShortName
    except ImportError:
        logger.warning("Portals: telethon not installed, cannot auto-generate token")
        return None

    try:
        client = TelegramClient(
            "portals_session",
            int(settings.TELEGRAM_API_ID),
            settings.TELEGRAM_API_HASH,
        )

        await client.start(phone=settings.TELEGRAM_PHONE)

        # Get the bot entity
        bot = await client.get_entity("portals_ton_bot")

        # Request web app view
        result = await client(RequestWebViewRequest(
            peer=bot,
            bot=bot,
            platform="android",
            url="https://portal-market.com",
        ))

        # Extract initData from the webapp URL
        url = result.url
        parsed = urlparse(url)
        fragment = parsed.fragment

        # The initData is in tgWebAppData parameter
        if "tgWebAppData=" in fragment:
            params = parse_qs(fragment)
            init_data = params.get("tgWebAppData", [""])[0]
            init_data = unquote(init_data)

            if init_data:
                logger.info("Portals: Successfully extracted initData from Telethon web view")
                await client.disconnect()
                return init_data

        logger.warning("Portals: Could not extract initData from web view URL: %s", url[:100])
        await client.disconnect()
        return None

    except Exception as exc:
        logger.error("Portals: Telethon token generation failed: %s", exc)
        return None


def invalidate_portals_token():
    """Force token refresh on next request."""
    _token_cache.pop("portals", None)
    logger.info("Portals: Token cache invalidated")
