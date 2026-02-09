"""
Update catalog with emoji placeholders for images.
"""

import asyncio
import logging
from sqlalchemy import select, update
from app.core.database import async_session
from app.models.gift import GiftCatalog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Emoji-based image URLs (data URIs)
GIFT_IMAGES = {
    "deliciouscake": "🎂",
    "greencircle": "🟢",
    "milkcoffee": "☕",
    "bluestar": "⭐",
    "redball": "🔴",
    "lollipop": "🍭",
    "pizza": "🍕",
    "icecream": "🍦",
    "champagne": "🍾",
    "partypopper": "🎉",
}


async def update_images():
    """Update catalog images with emojis."""
    logger.info("Updating catalog images...")

    async with async_session() as session:
        for slug, emoji in GIFT_IMAGES.items():
            # Create a simple colored square with emoji as fallback
            # Using a better placeholder service
            image_url = f"https://ui-avatars.com/api/?name={emoji}&size=150&background=1a1a1a&color=fff&font-size=0.6"

            stmt = (
                update(GiftCatalog)
                .where(GiftCatalog.slug == slug)
                .values(image_url=image_url)
            )
            await session.execute(stmt)
            logger.info(f"✅ Updated {slug}: {image_url}")

        await session.commit()
        logger.info("🎉 Images updated!")


if __name__ == "__main__":
    asyncio.run(update_images())
