"""
Sync catalog with actual gifts from TON Gifts NFT collection via TonAPI.
"""

import asyncio
import logging
from sqlalchemy import select
from app.core.database import async_session
from app.models.gift import GiftCatalog
from app.services.parsers.tonapi_enhanced import TonAPIEnhancedParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def sync_catalog():
    """Sync catalog with actual gifts from TonAPI."""
    logger.info("Syncing catalog from TonAPI TON Gifts collection...")

    # Fetch all NFTs from collection
    parser = TonAPIEnhancedParser()
    listings = await parser._fetch_nft_listings()

    if not listings:
        logger.error("No listings found from TonAPI")
        return

    logger.info(f"Found {len(listings)} NFT listings")

    # Group by unique gift types
    unique_gifts = {}
    for listing in listings:
        slug = listing.gift_slug
        if slug not in unique_gifts:
            unique_gifts[slug] = {
                "name": listing.gift_name,
                "slug": slug,
                "count": 0,
            }
        unique_gifts[slug]["count"] += 1

    logger.info(f"Found {len(unique_gifts)} unique gift types:\n")
    for slug, data in sorted(unique_gifts.items()):
        logger.info(f"  - {data['name']} ({slug}): {data['count']} items")

    # Update database
    async with async_session() as session:
        # Get existing slugs
        result = await session.execute(select(GiftCatalog.slug))
        existing = set(result.scalars().all())

        added = 0
        updated = 0

        for slug, data in unique_gifts.items():
            if slug in existing:
                # Update existing
                stmt = select(GiftCatalog).where(GiftCatalog.slug == slug)
                result = await session.execute(stmt)
                gift = result.scalar_one()
                if gift.name != data["name"]:
                    gift.name = data["name"]
                    updated += 1
                    logger.info(f"✏️ Updated: {data['name']} ({slug})")
            else:
                # Add new
                gift = GiftCatalog(
                    slug=slug,
                    name=data["name"],
                    image_url=f"https://ui-avatars.com/api/?name={data['name'][0]}&size=150&background=1a1a1a&color=fff&font-size=0.6",
                    total_supply=None,
                )
                session.add(gift)
                added += 1
                logger.info(f"➕ Added: {data['name']} ({slug})")

        if added > 0 or updated > 0:
            await session.commit()
            logger.info(f"\n✅ Catalog synced: {added} added, {updated} updated")
        else:
            logger.info("✅ Catalog already up to date")


if __name__ == "__main__":
    asyncio.run(sync_catalog())
