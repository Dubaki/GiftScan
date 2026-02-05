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

    # TON
    SERVICE_WALLET_ADDRESS: str = ""
    SERVICE_WALLET_MNEMONIC: str = ""

    # Escrow
    ESCROW_FEE_PERCENT: float = 2.0

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
