from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "GiftScan API"
    DEBUG: bool = True

    # PostgreSQL
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "giftscan"
    POSTGRES_PASSWORD: str = "giftscan_secret"
    POSTGRES_DB: str = "giftscan"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # Telegram
    BOT_TOKEN: str = ""
    WEBAPP_URL: str = ""
    TELEGRAM_CHAT_ID: str = ""  # Chat ID for arbitrage notifications

    # TON
    SERVICE_WALLET_ADDRESS: str = ""
    SERVICE_WALLET_MNEMONIC: str = ""

    # Escrow
    ESCROW_FEE_PERCENT: float = 2.0

    # Marketplace API Keys
    PORTALS_AUTH_TOKEN: str = ""  # Portals authorization token (tma query_id=...)
    TONAPI_KEY: str = ""  # TonAPI authentication key

    # Telegram Client (for internal market access)
    TELEGRAM_API_ID: str = ""
    TELEGRAM_API_HASH: str = ""
    TELEGRAM_PHONE: str = ""  # Phone number for Telethon session

    # Arbitrage settings
    MARKETPLACE_FEE_PERCENT: float = 5.0  # Combined marketplace + royalty
    GAS_FEE_TON: float = 0.1  # Estimated gas cost in TON
    SCAN_INTERVAL_SEC: int = 30  # Continuous scanner interval (15-30s recommended)
    MIN_PROFIT_TON: float = 2.0  # Minimum profit threshold for Telegram alerts

    # Rate limiting
    TONAPI_RATE_LIMIT: int = 10  # Requests per second
    PORTALS_RATE_LIMIT: int = 5  # Requests per second
    GETGEMS_RATE_LIMIT: int = 3  # Requests per second

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
