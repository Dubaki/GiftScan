"""
Seed gifts_catalog from TonAPI NFT collection.

This script fetches all unique gift types from the NFT collection
and populates the gifts_catalog table.
"""

import asyncio
import logging
from sqlalchemy import select
from app.core.database import async_session
from app.models.gift import GiftCatalog
from app.services.parsers.tonapi_enhanced import TonAPIEnhancedParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def seed_gifts_catalog():
    """Populate gifts_catalog from TonAPI NFT collection."""
    logger.info("Starting catalog seed from TonAPI...")

    # Fetch all NFT listings
    parser = TonAPIEnhancedParser()
    listings = await parser._fetch_nft_listings()

    if not listings:
        logger.error("No listings found from TonAPI")
        return

    logger.info(f"Found {len(listings)} NFT listings")

    # Group by slug to get unique gifts
    unique_gifts = {}
    for listing in listings:
        slug = listing.gift_slug
        if slug not in unique_gifts:
            unique_gifts[slug] = {
                "name": listing.gift_name,
                "slug": slug,
                # TonAPI doesn't provide image URLs in basic listing,
                # we'll use a placeholder or fetch later
                "image_url": f"https://via.placeholder.com/150?text={listing.gift_name.replace(' ', '+')}",
                "total_supply": None,  # Can be updated later
            }

    logger.info(f"Found {len(unique_gifts)} unique gift types")

    # Insert into database
    async with async_session() as session:
        # Check existing gifts
        result = await session.execute(select(GiftCatalog.slug))
        existing_slugs = set(result.scalars().all())

        added = 0
        for slug, data in unique_gifts.items():
            if slug not in existing_slugs:
                gift = GiftCatalog(
                    slug=data["slug"],
                    name=data["name"],
                    image_url=data["image_url"],
                    total_supply=data["total_supply"],
                )
                session.add(gift)
                added += 1
                logger.info(f"Added: {data['name']} ({slug})")

        if added > 0:
            await session.commit()
            logger.info(f"✅ Catalog seeded: {added} new gifts added")
        else:
            logger.info("✅ Catalog already populated")


if __name__ == "__main__":
    asyncio.run(seed_gifts_catalog())
