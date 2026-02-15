"""
Curates and re-seeds the gift catalog based on cross-marketplace availability.

- Fetches all gifts from Fragment, GetGems, Portals, MRKT, and Tonnel.
- Determines the set of gifts that are available on ALL of these marketplaces.
- Wipes the existing gift catalog.
- Re-seeds the catalog with only the verified, cross-marketplace gifts, using metadata
  from the TonAPI listings.
"""

import asyncio
import logging
from typing import Set

from sqlalchemy import delete
from sqlalchemy.future import select

from app.core.database import async_session
from app.models.gift import GiftCatalog
from app.services.parsers.fragment import FragmentParser
from app.services.parsers.tonapi_marketplace_parsers import (
    GetGemsParser,
    PortalsParser,
    MRKTParser,
    TonnelParser,
)
from app.services.parsers.tonapi_enhanced import TonAPIEnhancedParser, NFTListing

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def get_slugs_from_tonapi_parsers() -> Set[str]:
    """
    Fetches slugs from all TonAPI-based marketplaces and returns the intersection.
    """
    parsers = [GetGemsParser(), PortalsParser(), MRKTParser(), TonnelParser()]
    tasks = [parser.fetch_all_prices() for parser in parsers]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    slug_sets = []
    for i, result in enumerate(results):
        parser_name = parsers[i].source_name
        if isinstance(result, Exception):
            logger.error(f"Parser {parser_name} failed: {result}")
            # If a parser fails, we cannot guarantee presence on all marketplaces,
            # so we return an empty set.
            return set()
        
        slugs = set(result.keys())
        logger.info(f"Found {len(slugs)} slugs on {parser_name}")
        slug_sets.append(slugs)

    if not slug_sets:
        return set()

    # Start with the slugs from the first marketplace
    intersection = slug_sets[0]
    # Intersect with the rest
    for slugs in slug_sets[1:]:
        intersection.intersection_update(slugs)
    
    logger.info(f"Found {len(intersection)} slugs common to all TonAPI marketplaces.")
    return intersection


async def verify_slugs_with_fragment(slugs: Set[str]) -> Set[str]:
    """
    Verifies a set of slugs against Fragment.com.

    Returns the subset of slugs that are also found on Fragment.
    """
    parser = FragmentParser()
    tasks = [parser.fetch_gift_price(slug) for slug in slugs]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    verified_slugs = set()
    for i, result in enumerate(results):
        slug = list(slugs)[i]
        if isinstance(result, Exception):
            logger.warning(f"Fragment check for '{slug}' failed: {result}")
        elif result and result.price > 0:
            verified_slugs.add(slug)
    
    logger.info(f"Verified {len(verified_slugs)} slugs against Fragment.")
    return verified_slugs


async def get_all_gift_data_from_tonapi() -> dict[str, NFTListing]:
    """
    Fetches all listings from TonAPI to get canonical gift metadata.
    """
    parser = TonAPIEnhancedParser()
    listings = await parser._fetch_nft_listings()
    
    # Return a dict mapping slug to the first listing found for that slug
    # This is to get canonical name, image_url etc.
    gift_data = {listing.gift_slug: listing for listing in reversed(listings)}
    return gift_data


async def main():
    """Main curation and seeding process."""
    logger.info("="*50)
    logger.info("Starting gift catalog curation process")
    logger.info("="*50)

    # 1. Get slugs from TonAPI parsers and find intersection
    tonapi_slugs = await get_slugs_from_tonapi_parsers()
    if not tonapi_slugs:
        logger.error("Could not get common slugs from TonAPI marketplaces. Aborting.")
        return

    # 2. Verify the intersection with Fragment
    verified_slugs = await verify_slugs_with_fragment(tonapi_slugs)
    if not verified_slugs:
        logger.error("No slugs were found across all 5 marketplaces. Aborting.")
        return

    logger.info(f"Found {len(verified_slugs)} slugs present on ALL 5 marketplaces.")

    # 3. Get all gift data from TonAPI to use as the source of truth for metadata
    all_tonapi_data = await get_all_gift_data_from_tonapi()

    # 4. Filter the gift data and prepare the new catalog
    new_catalog_items = []
    seen_slugs = set()
    for slug in verified_slugs:
        if slug in all_tonapi_data and slug not in seen_slugs:
            listing = all_tonapi_data[slug]
            new_catalog_items.append(
                GiftCatalog(
                    name=listing.gift_name,
                    slug=listing.gift_slug,
                    image_url=listing.image_url,
                )
            )
            seen_slugs.add(slug)

    logger.info(f"Prepared {len(new_catalog_items)} gifts for the new catalog.")

    # 5. Wipe and re-seed the database
    async with async_session() as session:
        logger.warning("Wiping the existing 'gifts_catalog' table...")
        await session.execute(delete(GiftCatalog))
        
        logger.info(f"Adding {len(new_catalog_items)} verified gifts to the catalog...")
        session.add_all(new_catalog_items)
        
        await session.commit()
        logger.info("✅ Catalog re-seeding complete!")

    logger.info("="*50)
    logger.info("Curation process finished.")
    logger.info("="*50)


if __name__ == "__main__":
    # This is to ensure the script can be run from the `backend` directory
    # and import from the `app` module.
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    
    asyncio.run(main())
