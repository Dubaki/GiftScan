"""
Telegram bot notifier for arbitrage opportunities.

Sends formatted messages when profitable deals are detected.
Uses aiogram for async Telegram bot API.
"""

import logging
from decimal import Decimal
from typing import Optional, Dict
from dataclasses import field, dataclass

import aiohttp

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ArbitrageDeal:
    """Single arbitrage opportunity."""
    slug: str
    name: str
    buy_source: str
    buy_price: Decimal
    sell_source: str
    sell_price: Decimal
    spread_ton: Decimal
    net_profit: Decimal
    undervalued_premium: Decimal = Decimal('0.0')
    premium_indicators_count: int = 0
    serial_number: Optional[int] = None
    attributes: Optional[dict] = None
    all_prices: Dict[str, Decimal] = field(default_factory=dict) # New field


class TelegramNotifier:
    """
    Sends Telegram notifications for arbitrage opportunities.

    Message format (from 123.md):
        🏷 Тип: {Gift Name} #{Number}
        💰 Цена покупки: {Price} TON (нашел через TonAPI)
        📈 Цена на Fragment: {Price} TON
        💸 Чистый профит: {Profit} TON
        🔗 Ссылка на покупку: {Link}
    """

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        """
        Args:
            bot_token: Telegram bot token (default from settings.BOT_TOKEN)
            chat_id: Target chat ID (default from settings.TELEGRAM_CHAT_ID)
        """
        self.bot_token = bot_token or settings.BOT_TOKEN
        self.chat_id = chat_id or getattr(settings, "TELEGRAM_CHAT_ID", None)
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    async def send_arbitrage_alert(
        self,
        gift_name: str,
        serial_number: Optional[int],
        buy_price_ton: Decimal,
        buy_marketplace: str,
        fragment_price_ton: Decimal,  # Legacy name, actually sell_price
        net_profit_ton: Decimal,
        buy_link: str,
        sell_marketplace: str = "Fragment",  # Actual sell marketplace
        sell_link: str = "",  # NEW: Link to sell marketplace
        undervalued_premium: Decimal = Decimal('0.0'),
        premium_indicators_count: int = 0,
        all_prices: Dict[str, Decimal] = field(default_factory=dict),
        attributes: Optional[dict] = None, # New parameter
    ):
        """
        Send arbitrage opportunity notification to Telegram.

        Args:
            gift_name: Name of the gift (e.g., "Milk Coffee")
            serial_number: NFT serial number (e.g., 1234)
            buy_price_ton: Purchase price in TON
            buy_marketplace: Source marketplace (GetGems, Portals, etc.)
            fragment_price_ton: Fragment reference price
            net_profit_ton: Net profit after fees
            buy_link: Direct purchase link
        """
        if not self.bot_token:
            logger.warning("BOT_TOKEN not configured — skipping Telegram notification")
            return

        if not self.chat_id:
            logger.warning("TELEGRAM_CHAT_ID not configured — skipping notification")
            return

        # Format message
        serial_str = f" #{serial_number}" if serial_number else ""
        message = self._format_message(
            gift_name=gift_name,
            serial=serial_str,
            buy_price=buy_price_ton,
            buy_marketplace=buy_marketplace,
            sell_price=fragment_price_ton,
            sell_marketplace=sell_marketplace,
            profit=net_profit_ton,
            buy_link=buy_link,
            sell_link=sell_link,
            undervalued_premium=undervalued_premium,
            premium_indicators_count=premium_indicators_count,
            all_prices=all_prices,
            deal_attributes=attributes,
        )

        # Send to Telegram
        try:
            await self._send_message(message)
            logger.info(
                "Telegram alert sent: %s%s (profit: %.2f TON)",
                gift_name,
                serial_str,
                net_profit_ton,
            )
        except Exception as e:
            logger.error("Failed to send Telegram notification: %s", e)

    async def send_special_find_notification(
        self,
        gift_name: str,
        serial_number: Optional[int],
        price_ton: Decimal,
        marketplace: str,
        buy_link: str,
        attributes: Optional[dict] = None,
    ):
        """
        Send a notification for a special find, like a black background gift at floor price.
        """
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram not configured — skipping special find notification")
            return

        serial_str = f" #{serial_number}" if serial_number else ""
        
        attribute_str = ""
        if attributes and attributes.get("Backdrop") == "Black":
            attribute_str = "✨ **ЧЕРНЫЙ ФОН!**"

        message = (
            f"{attribute_str} НАЙДЕН РЕДКИЙ ПРЕДМЕТ!\n\n"
            f"🏷 <b>Тип:</b> {gift_name}{serial_str}\n"
            f"💰 <b>Цена:</b> {price_ton:.2f} TON (на {marketplace})\n"
            f"🔗 <b>Ссылка:</b> {buy_link}\n\n"
            f"⚡️ <i>GiftScan Valuation Bot</i>"
        )

        try:
            await self._send_message(message)
            logger.info(f"Sent special find notification for {gift_name}{serial_str}")
        except Exception as e:
            logger.error(f"Failed to send special find notification: {e}")

    def _format_message(
        self,
        gift_name: str,
        serial: str,
        buy_price: Decimal,
        buy_marketplace: str,
        sell_price: Decimal,
        sell_marketplace: str,
        profit: Decimal,
        buy_link: str,
        sell_link: str,
        undervalued_premium: Decimal,
        premium_indicators_count: int,
        all_prices: Dict[str, Decimal],
        deal_attributes: Optional[dict] = None, # New parameter
    ) -> str:
        """Format arbitrage alert message."""
        sell_link_section = f"\n🔗 <b>Ссылка на продажу ({sell_marketplace}):</b>\n{sell_link}\n" if sell_link else ""

        # Highlighting logic based on undervalued_premium and premium_indicators_count
        highlight_prefix = ""
        # Check for Black Background first (highest priority)
        if deal_attributes and deal_attributes.get("Background") == "Black":
            highlight_prefix = "✨ **ЧЕРНЫЙ ФОН!** "
        elif premium_indicators_count >= 2:
            highlight_prefix = "🔥 **ВЫГОДНАЯ СДЕЛКА!** "
        elif undervalued_premium > buy_price * Decimal('0.20'): # Example: highlight if premium is >20% of buy price
            highlight_prefix = "⭐ **ЦЕННОЕ ПРЕДЛОЖЕНИЕ!** "


        message_lines = [
            f"🚨 <b>АРБИТРАЖ!</b> 🚨",
            f"{highlight_prefix}🏷 <b>Тип:</b> {gift_name}{serial}",
            f"💰 <b>Цена покупки:</b> {buy_price:.2f} TON",
            f"   └ через {buy_marketplace}",
            f"📈 <b>Цена продажи:</b> {sell_price:.2f} TON",
            f"   └ на {sell_marketplace}",
            f"💸 <b>Чистый профит:</b> <b>{profit:.2f} TON</b> ({self._calc_roi(profit, buy_price):.1f}%)",
        ]

        if undervalued_premium > 0:
            message_lines.append(f"🎁 <b>Премия за атрибуты:</b> +{undervalued_premium:.2f} TON")

        # Add all available prices for context
        if all_prices:
            message_lines.append("\n📊 <b>Цены по площадкам:</b>")
            for source, price in sorted(all_prices.items(), key=lambda item: item[1]):
                message_lines.append(f"   - {source}: <b>{price:.2f}</b> TON")

        message_lines.append(f"\n🔗 <b>Ссылка на покупку ({buy_marketplace}):</b>")
        message_lines.append(buy_link)
        if sell_link:
            message_lines.append(sell_link_section)
        
        message_lines.append(f"⚡️ <i>GiftScan Arbitrage Bot</i>")

        return "\n".join(message_lines)

    @staticmethod
    def _calc_roi(profit: Decimal, buy_price: Decimal) -> float:
        """Calculate ROI percentage."""
        if buy_price > 0:
            return float((profit / buy_price) * 100)
        return 0.0

    async def _send_message(self, text: str):
        """Send message via Telegram Bot API."""
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                resp.raise_for_status()
                result = await resp.json()

                if not result.get("ok"):
                    raise Exception(f"Telegram API error: {result}")

    async def send_raw_message(self, text: str):
        """Send a pre-formatted HTML message to Telegram."""
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram not configured — skipping message")
            return
        await self._send_message(text)

    async def test_connection(self) -> bool:
        """Test Telegram bot connection."""
        if not self.bot_token:
            logger.error("BOT_TOKEN not configured")
            return False

        try:
            url = f"{self.base_url}/getMe"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    resp.raise_for_status()
                    result = await resp.json()

                    if result.get("ok"):
                        bot_name = result.get("result", {}).get("username")
                        logger.info("Telegram bot connected: @%s", bot_name)
                        return True
        except Exception as e:
            logger.error("Telegram connection test failed: %s", e)

        return False


# Singleton instance
telegram_notifier = TelegramNotifier()


async def send_arbitrage_notification(
    gift_name: str,
    serial_number: Optional[int],
    buy_price_ton: Decimal,
    buy_marketplace: str,
    fragment_price_ton: Decimal,
    net_profit_ton: Decimal,
    buy_link: str,
    sell_marketplace: str = "Fragment",
    sell_link: str = "",
    undervalued_premium: Decimal = Decimal('0.0'),
    premium_indicators_count: int = 0,
    all_prices: Dict[str, Decimal] = field(default_factory=dict),
):
    """
    Convenience function to send arbitrage notification.

    Args:
        gift_name: Gift name
        serial_number: NFT serial number
        buy_price_ton: Buy price in TON
        buy_marketplace: Source marketplace
        fragment_price_ton: Sell price in TON
        net_profit_ton: Net profit
        buy_link: Purchase link
        sell_marketplace: Sell marketplace
        sell_link: Sell marketplace link
    """
    await telegram_notifier.send_arbitrage_alert(
        gift_name=gift_name,
        serial_number=serial_number,
        buy_price_ton=buy_price_ton,
        buy_marketplace=buy_marketplace,
        fragment_price_ton=fragment_price_ton,
        net_profit_ton=net_profit_ton,
        buy_link=buy_link,
        sell_marketplace=sell_marketplace,
        sell_link=sell_link,
        undervalued_premium=undervalued_premium,
        premium_indicators_count=premium_indicators_count,
        all_prices=all_prices,
    )