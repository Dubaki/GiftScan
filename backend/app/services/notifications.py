"""
Notification system for arbitrage opportunities.

Sends a summary table when 3+ new arbitrage deals are found.
Only sends NEW deals — duplicates from previous scans are skipped.
"""

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime
from typing import Optional, Dict

from app.services.telegram_notifier import telegram_notifier

logger = logging.getLogger(__name__)


@dataclass
class ArbitrageDeal:
    """Single arbitrage / undervalued-floor opportunity."""

    slug: str
    name: str
    buy_source: str
    buy_price: Decimal
    sell_source: str
    sell_price: Decimal
    spread_ton: Decimal
    net_profit: Decimal
    alert_type: str = "arbitrage"  # "arbitrage" | "undervalued" | "arbitrage_unconfirmed"
    undervalued_premium: Decimal = Decimal("0.0")
    premium_indicators_count: int = 0
    serial_number: Optional[int] = None
    attributes: Optional[dict] = None
    all_prices: Dict[str, Decimal] = field(default_factory=dict)
    # Fair value info (None on cold start)
    fair_value_median: Optional[Decimal] = None
    fair_value_sales_count: int = 0
    fair_value_recent_count: int = 0
    fair_value_last_days_ago: Optional[int] = None
    fair_value_confidence: float = 0.0


class ArbitrageNotifier:
    """
    Collects opportunities during a scan, then sends
    a single summary table to Telegram if there are new deals.
    """

    def __init__(self, min_spread_ton: Decimal = Decimal("10.0")):
        self.min_spread_ton = min_spread_ton
        self.alert_count = 0

        # Key: "slug:buy_source:sell_source" → (buy_price, sell_price)
        self._sent_deals: dict[str, tuple[Decimal, Decimal]] = {}

        # Collected during current scan (reset each scan)
        self._current_deals: list[ArbitrageDeal] = []

    def collect_opportunity(
        self,
        slug: str,
        name: str,
        buy_source: str,
        buy_price: Decimal,
        sell_source: str,
        sell_price: Decimal,
        spread_ton: Decimal,
        serial_number: Optional[int] = None,
        attributes: Optional[dict] = None,
        undervalued_premium: Decimal = Decimal("0.0"),
        premium_indicators_count: int = 0,
        all_prices: Optional[Dict[str, Decimal]] = None,
        fair_value=None,  # FairValue dataclass or None
        alert_type: str = "arbitrage",
    ):
        """Collect an opportunity found during the scan."""
        if spread_ton < self.min_spread_ton:
            return

        if all_prices is None:
            all_prices = {}

        net_profit = spread_ton * Decimal("0.9")  # 10% fee estimate

        fv_median = fair_value.median_price if fair_value else None
        fv_count = fair_value.sales_count if fair_value else 0
        fv_recent = fair_value.recent_count if fair_value else 0
        fv_days = fair_value.last_sale_days_ago if fair_value else None
        fv_conf = fair_value.confidence if fair_value else 0.0

        self._current_deals.append(
            ArbitrageDeal(
                slug=slug,
                name=name,
                buy_source=buy_source,
                buy_price=buy_price,
                sell_source=sell_source,
                sell_price=sell_price,
                spread_ton=spread_ton,
                net_profit=net_profit,
                alert_type=alert_type,
                serial_number=serial_number,
                attributes=attributes,
                undervalued_premium=undervalued_premium,
                premium_indicators_count=premium_indicators_count,
                all_prices=all_prices,
                fair_value_median=fv_median,
                fair_value_sales_count=fv_count,
                fair_value_recent_count=fv_recent,
                fair_value_last_days_ago=fv_days,
                fair_value_confidence=fv_conf,
            )
        )

    async def send_scan_results(self):
        """
        After a scan, send summary of NEW deals to Telegram.
        Only sends if there are 3+ new deals.
        Resets current deals list after sending.
        """
        if not self._current_deals:
            logger.info("No opportunities found this scan")
            self._current_deals = []
            return

        # Filter out already-sent deals (same slug + sources + same prices)
        new_deals: list[ArbitrageDeal] = []
        for deal in self._current_deals:
            key = f"{deal.slug}:{deal.buy_source}:{deal.sell_source}"
            prev = self._sent_deals.get(key)
            if prev and prev[0] == deal.buy_price and prev[1] == deal.sell_price:
                logger.debug("Skipping duplicate deal: %s", key)
                continue
            new_deals.append(deal)

        # Sort: undervalued first, then by spread descending
        new_deals.sort(
            key=lambda d: (0 if d.alert_type == "undervalued" else 1, -d.spread_ton)
        )

        # Log all deals
        for deal in new_deals:
            logger.warning(
                "OPPORTUNITY [%s]: %s | BUY: %.2f TON @ %s | SELL: %.2f TON @ %s | SPREAD: %.2f TON",
                deal.alert_type,
                deal.name,
                deal.buy_price,
                deal.buy_source,
                deal.sell_price,
                deal.sell_source,
                deal.spread_ton,
            )

        if len(new_deals) < 3:
            logger.info(
                "Only %d new deals (need 3+), skipping Telegram summary",
                len(new_deals),
            )
            self._current_deals = []
            return

        try:
            message = self._format_summary_table(new_deals)
            await telegram_notifier.send_raw_message(message)
            logger.info("Sent Telegram summary with %d deals", len(new_deals))

            for deal in new_deals:
                key = f"{deal.slug}:{deal.buy_source}:{deal.sell_source}"
                self._sent_deals[key] = (deal.buy_price, deal.sell_price)

            self.alert_count += len(new_deals)

        except Exception as e:
            logger.error("Failed to send Telegram summary: %s", e)

        self._current_deals = []

    def _is_noteworthy(self, deal: ArbitrageDeal) -> bool:
        """Check if deal has rare serial or attributes."""
        if not deal.serial_number:
            return False
        if deal.serial_number < 1000:
            return True
        sn_str = str(deal.serial_number)
        if sn_str in {"777", "420", "1234", "5555", "6969", "8888"}:
            return True
        if len(set(sn_str)) == 1:
            return True
        if deal.attributes and deal.attributes.get("Backdrop") == "Black":
            return True
        return False

    def _format_summary_table(self, deals: list[ArbitrageDeal]) -> str:
        """Format deals as a Telegram-friendly summary table."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        total_profit = sum(d.net_profit for d in deals)

        lines = [
            f"<b>GIFTSCAN REPORT</b>  |  {len(deals)} deals  |  {timestamp}",
            "",
        ]

        for i, deal in enumerate(deals, 1):
            roi = (deal.spread_ton / deal.buy_price * 100) if deal.buy_price > 0 else 0

            # Title line
            if deal.alert_type == "undervalued":
                icon = "🔥"
                label = "UNDERVALUED"
            elif deal.alert_type == "arbitrage_unconfirmed":
                icon = "⚠️"
                label = "ARBITRAGE (no sales data)"
            else:
                icon = "💰"
                label = "ARBITRAGE"

            deal_info = f"{icon} <b>{i}. [{label}] {deal.name}"
            if deal.serial_number:
                deal_info += f" #{deal.serial_number}"
            deal_info += "</b>\n"

            deal_info += f"   BUY  <b>{deal.buy_price:.1f}</b> TON @ {deal.buy_source}\n"

            if deal.alert_type == "undervalued":
                deal_info += f"   FAIR VALUE  <b>{deal.sell_price:.1f}</b> TON (market avg)\n"
            else:
                deal_info += f"   SELL <b>{deal.sell_price:.1f}</b> TON @ {deal.sell_source}\n"

            deal_info += f"   Profit: <b>{deal.net_profit:.1f} TON</b> ({roi:.0f}%)"

            # Sales history info
            if deal.fair_value_median is not None:
                conf_pct = int(deal.fair_value_confidence * 100)
                deal_info += (
                    f"\n   📊 Sales data: <b>{deal.fair_value_sales_count}</b> sales"
                )
                if deal.fair_value_recent_count > 0:
                    deal_info += f" ({deal.fair_value_recent_count} in last 7d)"
                if deal.fair_value_last_days_ago is not None:
                    deal_info += f", last {deal.fair_value_last_days_ago}d ago"
                deal_info += f" | confidence {conf_pct}%"
            else:
                deal_info += "\n   ⚠️ No sales history — price unconfirmed"

            if deal.undervalued_premium > 0:
                deal_info += f"\n   💎 Premium: <b>+{deal.undervalued_premium:.1f} TON</b>"

            # Show attributes only for noteworthy NFTs
            if self._is_noteworthy(deal) and deal.attributes:
                deal_info += "\n   ⭐ Rare attributes:"
                for attr_key, attr_value in deal.attributes.items():
                    deal_info += f"\n     • {attr_key}: {attr_value}"

            lines.append(deal_info)

        lines.append("")
        lines.append(f"Total potential profit: <b>{total_profit:.1f} TON</b>")
        lines.append(f"\n<i>GiftScan  |  min spread {self.min_spread_ton} TON</i>")

        return "\n".join(lines)

    def reset_sent_deals(self):
        """Clear sent deals tracker (e.g., daily reset)."""
        self._sent_deals.clear()
        logger.info("Sent deals tracker cleared")

    def get_stats(self) -> dict:
        """Get notification statistics."""
        return {
            "total_alerts": self.alert_count,
            "min_spread_threshold_ton": float(self.min_spread_ton),
            "tracked_deals": len(self._sent_deals),
        }


# Global notifier instance (10 TON threshold — minimum profitable margin)
arbitrage_notifier = ArbitrageNotifier(min_spread_ton=Decimal("10.0"))
