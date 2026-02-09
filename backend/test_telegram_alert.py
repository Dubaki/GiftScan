"""Test Telegram arbitrage alert."""

import asyncio
from decimal import Decimal
from app.services.telegram_notifier import telegram_notifier


async def main():
    """Send test arbitrage alert."""
    print("Testing Telegram arbitrage notification...")
    print(f"Bot token configured: {bool(telegram_notifier.bot_token)}")
    print(f"Chat ID: {telegram_notifier.chat_id}\n")

    # Test connection
    connected = await telegram_notifier.test_connection()
    if not connected:
        print("ERROR: Telegram bot connection failed!")
        return

    print("SUCCESS: Bot connected! Sending test alert...\n")

    # Send test alert for Loot Bag arbitrage with UPDATED link
    await telegram_notifier.send_arbitrage_alert(
        gift_name="Loot Bag",
        serial_number=None,
        buy_price_ton=Decimal("146.99"),
        buy_marketplace="GetGems",
        fragment_price_ton=Decimal("160"),
        net_profit_ton=Decimal("11.71"),  # After 10% fees
        buy_link="https://getgems.io/search?query=Loot%20Bag",
    )

    print("SUCCESS: Test alert sent! Check your Telegram.")


if __name__ == "__main__":
    asyncio.run(main())
