"""
Fast catalog sync - only items that are on sale.
"""

import asyncio
import logging
from sqlalchemy import select
from app.core.database import async_session
from app.models.gift import GiftCatalog
from app.services.parsers.tonapi_enhanced import TonAPIEnhancedParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def sync_catalog_fast():
    """Sync catalog with gifts that are currently on sale (faster!)."""
    logger.info("Fast sync: Loading only gifts on sale...")

    # Fetch NFTs that are on sale
    parser = TonAPIEnhancedParser()
    listings = await parser._fetch_nft_listings()  # Already filtered to on-sale items

    logger.info(f"Found {len(listings)} items on sale")

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

    logger.info(f"\nFound {len(unique_gifts)} unique gift types on sale\n")

    # Show top 20
    sorted_gifts = sorted(unique_gifts.items(), key=lambda x: x[1]["count"], reverse=True)
    logger.info("Top 20 most listed gifts:")
    for slug, data in sorted_gifts[:20]:
        logger.info(f"  - {data['name']} ({slug}): {data['count']} on sale")

    # Update database
    async with async_session() as session:
        result = await session.execute(select(GiftCatalog.slug))
        existing = set(result.scalars().all())

        added = 0
        updated = 0

        for slug, data in unique_gifts.items():
            if slug in existing:
                stmt = select(GiftCatalog).where(GiftCatalog.slug == slug)
                result = await session.execute(stmt)
                gift = result.scalar_one_or_none()
                if gift and gift.name != data["name"]:
                    gift.name = data["name"]
                    updated += 1
            else:
                gift = GiftCatalog(
                    slug=slug,
                    name=data["name"],
                    image_url=f"https://ui-avatars.com/api/?name={data['name'][0]}&size=150&background=1a1a1a&color=fff&font-size=0.6",
                    total_supply=None,
                )
                session.add(gift)
                added += 1

        if added > 0 or updated > 0:
            await session.commit()
            logger.info(f"\n✅ Fast sync complete: {added} added, {updated} updated")
            logger.info(f"Total gifts in catalog: {len(existing) + added}")
        else:
            logger.info(f"\n✅ Catalog already up to date ({len(existing)} gifts)")


if __name__ == "__main__":
    asyncio.run(sync_catalog_fast())
