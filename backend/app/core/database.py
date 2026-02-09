from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(settings.database_url, echo=settings.DEBUG)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Alias for compatibility with continuous_scanner
AsyncSessionLocal = async_session


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
