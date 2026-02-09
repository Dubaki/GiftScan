"""
Add new gift types discovered from TonAPI to the catalog.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from app.core.database import async_session
from app.models.gift import GiftCatalog


# New gifts discovered from TonAPI (13 types)
NEW_GIFTS = [
    {"slug": "westsidesign", "name": "Westside Sign", "image_url": "https://cache.tonapi.io/imgproxy/...", "total_supply": None},
    {"slug": "toybear", "name": "Toy Bear", "image_url": "https://cache.tonapi.io/imgproxy/...", "total_supply": None},
    {"slug": "genielamp", "name": "Genie Lamp", "image_url": "https://cache.tonapi.io/imgproxy/...", "total_supply": None},
    {"slug": "blingbinky", "name": "Bling Binky", "image_url": "https://cache.tonapi.io/imgproxy/...", "total_supply": None},
    {"slug": "heroichelmet", "name": "Heroic Helmet", "image_url": "https://cache.tonapi.io/imgproxy/...", "total_supply": None},
    {"slug": "astralshard", "name": "Astral Shard", "image_url": "https://cache.tonapi.io/imgproxy/...", "total_supply": None},
    {"slug": "perfumebottle", "name": "Perfume Bottle", "image_url": "https://cache.tonapi.io/imgproxy/...", "total_supply": None},
    {"slug": "mightyarm", "name": "Mighty Arm", "image_url": "https://cache.tonapi.io/imgproxy/...", "total_supply": None},
    {"slug": "swisswatch", "name": "Swiss Watch", "image_url": "https://cache.tonapi.io/imgproxy/...", "total_supply": None},
    {"slug": "signetring", "name": "Signet Ring", "image_url": "https://cache.tonapi.io/imgproxy/...", "total_supply": None},
    {"slug": "vintagecigar", "name": "Vintage Cigar", "image_url": "https://cache.tonapi.io/imgproxy/...", "total_supply": None},
    {"slug": "scaredcat", "name": "Scared Cat", "image_url": "https://cache.tonapi.io/imgproxy/...", "total_supply": None},
    {"slug": "voodoodoll", "name": "Voodoo Doll", "image_url": "https://cache.tonapi.io/imgproxy/...", "total_supply": None},
]


async def main():
    print("\n" + "=" * 80)
    print("ADDING NEW GIFT TYPES TO CATALOG")
    print("=" * 80 + "\n")

    async with async_session() as session:
        # Check which ones already exist
        result = await session.execute(select(GiftCatalog.slug))
        existing_slugs = {row.slug for row in result}

        added = 0
        skipped = 0

        for gift in NEW_GIFTS:
            slug = gift["slug"]

            if slug in existing_slugs:
                print(f"  SKIP: {gift['name']:30} (already exists)")
                skipped += 1
                continue

            # Add to catalog
            new_gift = GiftCatalog(
                slug=slug,
                name=gift["name"],
                image_url=gift.get("image_url"),
                total_supply=gift.get("total_supply"),
            )
            session.add(new_gift)
            print(f"  ADD:  {gift['name']:30} (slug: {slug})")
            added += 1

        # Commit changes
        if added > 0:
            await session.commit()
            print(f"\n✅ Added {added} new gift types to catalog")
        else:
            print(f"\n✅ All gifts already in catalog")

        if skipped > 0:
            print(f"⏭️  Skipped {skipped} existing gifts")

    print("\n" + "=" * 80)
    print("DONE! Restart scanner to start tracking new gifts.")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
