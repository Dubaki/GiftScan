"""
Notification system for arbitrage opportunities.

Alerts when profitable spreads are detected (> 1.5 TON as per 123.md).
"""

import asyncio
import logging
from decimal import Decimal
from datetime import datetime
from typing import Optional

from app.services.telegram_notifier import telegram_notifier

logger = logging.getLogger(__name__)

# ANSI color codes for console alerts
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class ArbitrageNotifier:
    """
    Sends alerts when profitable arbitrage opportunities are detected.

    As per 123.md requirement: Alert when (Price_Fragment - Price_Portals) > 1.5 TON
    """

    def __init__(self, min_spread_ton: Decimal = Decimal("1.5")):
        """
        Args:
            min_spread_ton: Minimum spread to trigger alert (default: 1.5 TON)
        """
        self.min_spread_ton = min_spread_ton
        self.alert_count = 0
        # Track recent alerts to avoid duplicates
        # Format: {slug: (buy_price, sell_price, timestamp)}
        self._recent_alerts: dict[str, tuple[Decimal, Decimal, datetime]] = {}

    async def alert_opportunity(
        self,
        slug: str,
        name: str,
        buy_source: str,
        buy_price: Decimal,
        sell_source: str,
        sell_price: Decimal,
        spread_ton: Decimal,
        net_profit: Optional[Decimal] = None,
        serial: Optional[int] = None,
    ):
        """
        Send alert about arbitrage opportunity.

        Args:
            slug: Gift slug
            name: Gift name
            buy_source: Where to buy
            buy_price: Buy price in TON
            sell_source: Where to sell
            sell_price: Sell price in TON
            spread_ton: Price spread in TON
            net_profit: Net profit after fees (optional)
            serial: NFT serial number (optional, for deep arbitrage)
        """
        if spread_ton < self.min_spread_ton:
            return  # Below threshold

        # Check if we already sent this alert recently (24 hour cooldown)
        if slug in self._recent_alerts:
            prev_buy, prev_sell, prev_time = self._recent_alerts[slug]
            time_since_last = (datetime.now() - prev_time).total_seconds()
            hours_since_last = time_since_last / 3600

            # Skip if alerted within last 24 hours
            if time_since_last < 86400:  # 24 hours = 86400 seconds
                logger.debug(
                    "Skipping alert for %s (already sent %.1f hours ago, next alert in %.1f hours)",
                    slug, hours_since_last, 24 - hours_since_last
                )
                return
            else:
                logger.info(
                    "Re-alerting %s (24h cooldown expired, last alert %.1f hours ago)",
                    slug, hours_since_last
                )

        self.alert_count += 1
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Build alert message
        separator = "=" * 80
        serial_info = f" #{serial}" if serial else ""

        alert_msg = f"""
{Colors.BOLD}{Colors.OKGREEN}{separator}{Colors.ENDC}
{Colors.BOLD}🚨 ARBITRAGE OPPORTUNITY #{self.alert_count}{Colors.ENDC}
{Colors.BOLD}{separator}{Colors.ENDC}

{Colors.OKCYAN}Gift:{Colors.ENDC} {Colors.BOLD}{name}{Colors.ENDC} ({slug}){serial_info}
{Colors.OKCYAN}Time:{Colors.ENDC} {timestamp}

{Colors.WARNING}💰 BUY:{Colors.ENDC}  {Colors.BOLD}{buy_price:.2f} TON{Colors.ENDC} on {Colors.UNDERLINE}{buy_source}{Colors.ENDC}
{Colors.OKGREEN}💸 SELL:{Colors.ENDC} {Colors.BOLD}{sell_price:.2f} TON{Colors.ENDC} on {Colors.UNDERLINE}{sell_source}{Colors.ENDC}

{Colors.BOLD}📊 SPREAD:{Colors.ENDC} {Colors.BOLD}{Colors.OKGREEN}{spread_ton:.2f} TON{Colors.ENDC} ({(spread_ton / buy_price * 100):.1f}%)
"""

        if net_profit is not None:
            alert_msg += f"{Colors.BOLD}💎 NET PROFIT (after fees):{Colors.ENDC} {Colors.BOLD}{Colors.OKGREEN}{net_profit:.2f} TON{Colors.ENDC}\n"

        alert_msg += f"\n{Colors.BOLD}{Colors.OKGREEN}{separator}{Colors.ENDC}\n"

        # Print to console
        print(alert_msg)

        # Log to file
        logger.warning(
            "ARBITRAGE ALERT #%d: %s%s | BUY: %.2f TON @ %s | SELL: %.2f TON @ %s | SPREAD: %.2f TON",
            self.alert_count,
            name,
            f" #{serial}" if serial else "",
            buy_price,
            buy_source,
            sell_price,
            sell_source,
            spread_ton,
        )

        # Send Telegram notification
        # Calculate net profit if not provided (use 10% fee estimate)
        calc_net_profit = net_profit if net_profit is not None else (spread_ton * Decimal("0.9"))

        # Generate buy link and sell link (only for non-TMA marketplaces)
        buy_link = self._generate_buy_link(slug, buy_source, serial, name)
        # Only include sell link for marketplaces with direct deep links (not TMA apps)
        if sell_source in ["Fragment", "GetGems", "Tonnel"]:
            sell_link = self._generate_buy_link(slug, sell_source, serial, name)
        else:
            sell_link = ""  # Skip link for MRKT/Portals (TMA apps without deep links)

        try:
            await telegram_notifier.send_arbitrage_alert(
                gift_name=name,
                serial_number=serial,
                buy_price_ton=buy_price,
                buy_marketplace=buy_source,
                fragment_price_ton=sell_price,  # Legacy parameter name
                sell_marketplace=sell_source,  # NEW: actual sell marketplace
                net_profit_ton=calc_net_profit,
                buy_link=buy_link,
                sell_link=sell_link,
            )
            # Track this alert to avoid duplicates
            self._recent_alerts[slug] = (buy_price, sell_price, datetime.now())
        except Exception as e:
            logger.error("Failed to send Telegram alert: %s", e)

    def _generate_buy_link(self, slug: str, marketplace: str, serial: Optional[int] = None, gift_name: str = "") -> str:
        """
        Generate purchase link based on marketplace.

        IMPORTANT: Uses collection addresses for GetGems to ensure correct NFTs are shown.
        For unmapped gifts, uses search.
        """
        # Map slugs to GetGems collection addresses
        # These are the NFT collection addresses from TonAPI
        slug_to_collection = {
            # Loot Bags collection
            "lootbag": "EQCE80Aln8YfldnQLwWMvOfloLGgmPY0eGDJz9ufG3gRui3D",
            # Jingle Bells collection
            "jinglebells": "EQCehrkZtKDtVe0qyvBAsrHx3hW-hroQyDrS_MZOOVYth2DG",
            # Heart Lockets collection
            "heartlocket": "EQC4XEulxb05Le5gF6esMtDWT5XZ6tlzlMBQGNsqffxpdC5U",
            # Original TON Gifts collection (all others)
            "icecream": "EQBpMhoMDsN0DjQZXFFBup7l5gbt-UtMzTHN5qaqQtc90CLD",
            "milkcoffee": "EQBpMhoMDsN0DjQZXFFBup7l5gbt-UtMzTHN5qaqQtc90CLD",
            "bluestar": "EQBpMhoMDsN0DjQZXFFBup7l5gbt-UtMzTHN5qaqQtc90CLD",
            "deliciouscake": "EQBpMhoMDsN0DjQZXFFBup7l5gbt-UtMzTHN5qaqQtc90CLD",
            "greencircle": "EQBpMhoMDsN0DjQZXFFBup7l5gbt-UtMzTHN5qaqQtc90CLD",
            "redball": "EQBpMhoMDsN0DjQZXFFBup7l5gbt-UtMzTHN5qaqQtc90CLD",
            "lollipop": "EQBpMhoMDsN0DjQZXFFBup7l5gbt-UtMzTHN5qaqQtc90CLD",
            "pizza": "EQBpMhoMDsN0DjQZXFFBup7l5gbt-UtMzTHN5qaqQtc90CLD",
            "champagne": "EQBpMhoMDsN0DjQZXFFBup7l5gbt-UtMzTHN5qaqQtc90CLD",
            "partypopper": "EQBpMhoMDsN0DjQZXFFBup7l5gbt-UtMzTHN5qaqQtc90CLD",
            "blackrabbit": "EQBpMhoMDsN0DjQZXFFBup7l5gbt-UtMzTHN5qaqQtc90CLD",
            "christmastree": "EQBpMhoMDsN0DjQZXFFBup7l5gbt-UtMzTHN5qaqQtc90CLD",
            "snowman": "EQBpMhoMDsN0DjQZXFFBup7l5gbt-UtMzTHN5qaqQtc90CLD",
            "envelope": "EQBpMhoMDsN0DjQZXFFBup7l5gbt-UtMzTHN5qaqQtc90CLD",
            "dancingheart": "EQBpMhoMDsN0DjQZXFFBup7l5gbt-UtMzTHN5qaqQtc90CLD",
            "chocolatebox": "EQBpMhoMDsN0DjQZXFFBup7l5gbt-UtMzTHN5qaqQtc90CLD",
            "teddybear": "EQBpMhoMDsN0DjQZXFFBup7l5gbt-UtMzTHN5qaqQtc90CLD",
            "flowers": "EQBpMhoMDsN0DjQZXFFBup7l5gbt-UtMzTHN5qaqQtc90CLD",
            "dragon": "EQBpMhoMDsN0DjQZXFFBup7l5gbt-UtMzTHN5qaqQtc90CLD",
        }

        if marketplace == "GetGems":
            # GetGems: Use collection link if known, otherwise use search
            if slug in slug_to_collection:
                # Direct collection link (faster, sorted by price)
                collection_addr = slug_to_collection[slug]
                return f"https://getgems.io/collection/{collection_addr}?sortBy=priceAsc"
            else:
                # Search link for new/unmapped gifts
                # Use gift name for better search results
                search_query = gift_name.replace(" ", "%20") if gift_name else slug
                return f"https://getgems.io/search?query={search_query}"

        elif marketplace == "Portals":
            # Portals gifts page (TMA app)
            return f"https://t.me/portals_ton_bot/app?startapp=gifts"

        elif marketplace == "Tonnel":
            # Tonnel marketplace
            return f"https://tonnel.network"

        elif marketplace == "MRKT":
            # MRKT marketplace (TMA app - open directly)
            return f"https://t.me/marketapp_bot/app"

        elif marketplace == "Fragment":
            # Fragment direct gift page with price sorting
            return f"https://fragment.com/gifts/{slug}?sort=price_asc&filter=sale"

        else:
            # Fallback to Fragment
            return f"https://fragment.com/gifts/{slug}?sort=price_asc&filter=sale"

    async def alert_deep_arbitrage(
        self,
        slug: str,
        name: str,
        serial: int,
        buy_source: str,
        buy_price: Decimal,
        sell_source: str,
        sell_price: Decimal,
        spread_ton: Decimal,
        net_profit: Optional[Decimal] = None,
    ):
        """
        Alert for deep arbitrage (same NFT #number on different marketplaces).

        This is a priority signal as per 123.md requirements.
        """
        await self.alert_opportunity(
            slug=slug,
            name=name,
            buy_source=buy_source,
            buy_price=buy_price,
            sell_source=sell_source,
            sell_price=sell_price,
            spread_ton=spread_ton,
            net_profit=net_profit,
            serial=serial,
        )

        # Additional log for deep arbitrage
        logger.critical(
            "🎯 DEEP ARBITRAGE (Priority): Same NFT %s #%d found at different prices! "
            "Buy @ %s (%.2f TON), Sell @ %s (%.2f TON), Spread: %.2f TON",
            name,
            serial,
            buy_source,
            buy_price,
            sell_source,
            sell_price,
            spread_ton,
        )

    def get_stats(self) -> dict:
        """Get notification statistics."""
        return {
            "total_alerts": self.alert_count,
            "min_spread_threshold_ton": float(self.min_spread_ton),
        }


# Global notifier instance (3 TON threshold for testing)
arbitrage_notifier = ArbitrageNotifier(min_spread_ton=Decimal("3.0"))
