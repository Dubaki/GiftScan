"""
Continuous price scanner with round-robin marketplace polling.

Replaces the old 600-second batch scanner with a more responsive
15-30 second interval scanner that cycles through marketplaces.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.services.scanner import GiftScanner
from app.services.cache import CacheService

logger = logging.getLogger(__name__)


class ContinuousScanner:
    """
    Continuous scanner that polls marketplaces in round-robin fashion.

    Features:
    - Configurable scan interval (default 30s)
    - Round-robin marketplace rotation
    - Automatic cache invalidation
    - Error recovery and retry
    - Statistics tracking
    """

    def __init__(self, scan_interval: int = None):
        """
        Args:
            scan_interval: Seconds between scans (default from settings)
        """
        self.scan_interval = scan_interval or settings.SCAN_INTERVAL_SEC
        self.scanner = GiftScanner()
        self._is_running = False
        self._task: Optional[asyncio.Task] = None

        # Statistics
        self.total_scans = 0
        self.total_snapshots = 0
        self.last_scan_time: Optional[datetime] = None
        self.last_scan_duration: float = 0

    async def start(self):
        """Start the continuous scanning loop."""
        if self._is_running:
            logger.warning("ContinuousScanner already running")
            return

        self._is_running = True
        self._task = asyncio.create_task(self._scan_loop())
        logger.info(
            "ContinuousScanner started with %ds interval",
            self.scan_interval,
        )

    async def stop(self):
        """Stop the scanning loop gracefully."""
        if not self._is_running:
            return

        logger.info("Stopping ContinuousScanner...")
        self._is_running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("ContinuousScanner stopped")

    async def _scan_loop(self):
        """Main scanning loop."""
        logger.info("ContinuousScanner loop started")

        while self._is_running:
            try:
                await self._run_scan_cycle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "ContinuousScanner error in scan cycle: %s",
                    e,
                    exc_info=True,
                )

            # Wait for next interval
            if self._is_running:
                await asyncio.sleep(self.scan_interval)

    async def _run_scan_cycle(self):
        """Execute a single scan cycle."""
        scan_start = datetime.utcnow()

        logger.info(
            "Starting scan cycle #%d at %s",
            self.total_scans + 1,
            scan_start.isoformat(),
        )

        async with AsyncSessionLocal() as session:
            try:
                # Run full scan
                result = await self.scanner.run_full_scan(session)

                # Update statistics
                self.total_scans += 1
                self.total_snapshots += result["saved"]
                self.last_scan_time = scan_start
                self.last_scan_duration = result["duration_sec"]

                # Invalidate cache
                try:
                    await CacheService.invalidate()
                    logger.debug("Cache invalidated after scan")
                except Exception as e:
                    logger.warning("Failed to invalidate cache: %s", e)

                # Log summary
                logger.info(
                    "Scan cycle #%d complete: %d snapshots saved in %.1fs | Sources: %s",
                    self.total_scans,
                    result["saved"],
                    result["duration_sec"],
                    result.get("sources", {}),
                )

            except Exception as e:
                logger.error(
                    "Scan cycle failed: %s",
                    e,
                    exc_info=True,
                )

    def get_stats(self) -> dict:
        """Get scanner statistics."""
        return {
            "is_running": self._is_running,
            "total_scans": self.total_scans,
            "total_snapshots": self.total_snapshots,
            "last_scan_time": self.last_scan_time.isoformat() if self.last_scan_time else None,
            "last_scan_duration_sec": self.last_scan_duration,
            "scan_interval_sec": self.scan_interval,
            "parsers_active": len(self.scanner.parsers),
        }


# Global scanner instance
_continuous_scanner: Optional[ContinuousScanner] = None


def get_continuous_scanner() -> ContinuousScanner:
    """Get or create the global continuous scanner instance."""
    global _continuous_scanner
    if _continuous_scanner is None:
        _continuous_scanner = ContinuousScanner()
    return _continuous_scanner


async def start_continuous_scanner():
    """Start the global continuous scanner."""
    scanner = get_continuous_scanner()
    await scanner.start()


async def stop_continuous_scanner():
    """Stop the global continuous scanner."""
    scanner = get_continuous_scanner()
    await scanner.stop()
