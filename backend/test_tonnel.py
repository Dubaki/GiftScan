"""Quick test for Tonnel 3-phase parser."""
import asyncio
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s %(name)s: %(message)s",
)
# Only show our parser logs at DEBUG, silence others
logging.getLogger("curl_cffi").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)

from app.services.parsers.tonnel_direct import TonnelDirectParser


async def main():
    parser = TonnelDirectParser()
    prices = await parser.fetch_all_prices()

    print(f"\n{'='*60}")
    print(f"Total gifts found: {len(prices)}")
    print(f"{'='*60}")
    for slug, gp in sorted(prices.items(), key=lambda x: x[1].price):
        print(f"  {slug:25s} {gp.price:>10.2f} TON  (raw: {gp.raw_name})")


asyncio.run(main())
