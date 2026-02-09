"""
Telegram bot notifier for arbitrage opportunities.

Sends formatted messages when profitable deals are detected.
Uses aiogram for async Telegram bot API.
"""

import logging
from decimal import Decimal
from typing import Optional

import aiohttp

from app.core.config import settings

logger = logging.getLogger(__name__)


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
    ) -> str:
        """Format arbitrage alert message."""
        sell_link_section = f"\n🔗 <b>Ссылка на продажу ({sell_marketplace}):</b>\n{sell_link}\n" if sell_link else ""

        return f"""🚨 <b>АРБИТРАЖ!</b> 🚨

🏷 <b>Тип:</b> {gift_name}{serial}

💰 <b>Цена покупки:</b> {buy_price:.2f} TON
   └ через {buy_marketplace}

📈 <b>Цена продажи:</b> {sell_price:.2f} TON
   └ на {sell_marketplace}

💸 <b>Чистый профит:</b> <b>{profit:.2f} TON</b> ({self._calc_roi(profit, buy_price):.1f}%)

🔗 <b>Ссылка на покупку ({buy_marketplace}):</b>
{buy_link}
{sell_link_section}
⚡️ <i>GiftScan Arbitrage Bot</i>"""

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
    )
