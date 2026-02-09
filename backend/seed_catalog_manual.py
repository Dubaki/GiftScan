"""
Manually seed gifts_catalog with known TON gift types.

Based on popular gifts from Fragment.com
"""

import asyncio
import logging
from sqlalchemy import select
from app.core.database import async_session
from app.models.gift import GiftCatalog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Known TON NFT Gifts (from Fragment.com)
KNOWN_GIFTS = [
    {"slug": "deliciouscake", "name": "Delicious Cake"},
    {"slug": "greencircle", "name": "Green Circle"},
    {"slug": "milkcoffee", "name": "Milk Coffee"},
    {"slug": "bluestar", "name": "Blue Star"},
    {"slug": "redball", "name": "Red Ball"},
    {"slug": "lollipop", "name": "Lollipop"},
    {"slug": "pizza", "name": "Pizza"},
    {"slug": "icecream", "name": "Ice Cream"},
    {"slug": "champagne", "name": "Champagne"},
    {"slug": "partypopper", "name": "Party Popper"},
]


async def seed_catalog():
    """Seed catalog with known gifts."""
    logger.info("Seeding catalog with known gifts...")

    async with async_session() as session:
        # Check existing
        result = await session.execute(select(GiftCatalog.slug))
        existing = set(result.scalars().all())

        added = 0
        for gift_data in KNOWN_GIFTS:
            if gift_data["slug"] not in existing:
                gift = GiftCatalog(
                    slug=gift_data["slug"],
                    name=gift_data["name"],
                    image_url=f"https://via.placeholder.com/150?text={gift_data['name'].replace(' ', '+')}",
                    total_supply=None,
                )
                session.add(gift)
                added += 1
                logger.info(f"✅ Added: {gift_data['name']}")
            else:
                logger.info(f"⏭ Skipped: {gift_data['name']} (already exists)")

        if added > 0:
            await session.commit()
            logger.info(f"\n🎉 Catalog seeded: {added} new gifts added!")
        else:
            logger.info(f"\n✅ Catalog already complete ({len(existing)} gifts)")


if __name__ == "__main__":
    asyncio.run(seed_catalog())
