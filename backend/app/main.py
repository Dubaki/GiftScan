import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.database import async_session
from app.api.routes.deals import router as deals_router
from app.api.routes.gifts import router as gifts_router
from app.workers.price_updater import price_update_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: launch the background price scanner
    task = asyncio.create_task(price_update_loop())
    yield
    # Shutdown: cancel the background task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title=settings.PROJECT_NAME, debug=settings.DEBUG, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(deals_router, prefix="/api/v1")
app.include_router(gifts_router, prefix="/api/v1")


@app.get("/health")
async def health():
    try:
        async with async_session() as session:
            result = await session.execute(text("SELECT 1"))
            result.scalar()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {e}"

    return {
        "status": "ok" if db_status == "connected" else "degraded",
        "db": db_status,
    }
