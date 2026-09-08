"""Production Background Worker & Task Scheduler for AI Job Assistant.

Responsibilities:
1. Application Queue Processing (leasing, policy evaluation, submission attempts)
2. Worker Lease Recovery (reclaiming orphaned tasks from crashed worker instances)
3. Dead Letter Queue Monitoring
4. Scheduled Maintenance & Periodic Connector Health Checks
5. Graceful Shutdown & Signal Handling (SIGINT, SIGTERM)
"""

import asyncio
import logging
import signal
import sys
import time
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.session import AsyncSessionLocal, init_db
from app.modules.applications.queue import ApplicationQueueService
from app.modules.applications.service import ApplicationService
from app.modules.connectors.registry import connector_registry
from app.modules.connectors.health import connector_health_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [WORKER] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("app.worker")


class ProductionWorker:
    """Production-grade asynchronous background worker daemon."""

    def __init__(self, poll_interval: int = 10, batch_size: int = 5):
        self.poll_interval = poll_interval
        self.batch_size = batch_size
        self.is_running = False
        self.cycle_count = 0
        self.total_processed = 0
        self.total_recovered = 0
        self._stop_event = asyncio.Event()

    def handle_signal(self, signum, frame):
        """Signal handler for graceful shutdown."""
        sig_name = signal.Signals(signum).name if hasattr(signal, "Signals") else str(signum)
        logger.info(f"Received termination signal: {sig_name}. Initiating graceful shutdown...")
        self.is_running = False
        self._stop_event.set()

    def register_signals(self):
        """Registers OS signal handlers across Linux/macOS/Windows."""
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                signal.signal(sig, self.handle_signal)
            except Exception as err:
                logger.debug(f"Could not register signal {sig}: {err}")

        # Windows-specific SIGBREAK if available
        if hasattr(signal, "SIGBREAK"):
            try:
                signal.signal(signal.SIGBREAK, self.handle_signal)
            except Exception:
                pass

    async def run_cycle(self) -> dict:
        """Executes a single processing cycle (recovers leases, processes queue, checks health)."""
        self.cycle_count += 1
        cycle_stats = {
            "cycle": self.cycle_count,
            "leases_recovered": 0,
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "retried": 0,
            "timestamp": time.time(),
        }

        async with AsyncSessionLocal() as session:
            try:
                # 1. Recover expired leases from crashed workers
                queue_service = ApplicationQueueService(session)
                recovered = await queue_service.recover_expired_leases(
                    lease_timeout_seconds=settings.WORKER_LEASE_SECONDS
                )
                if recovered > 0:
                    logger.warning(f"Crash recovery: reclaimed {recovered} orphaned queue leases.")
                    self.total_recovered += recovered
                    cycle_stats["leases_recovered"] = recovered
                    await session.commit()

                # 2. Process due items from the application queue
                app_service = ApplicationService(session)
                result = await app_service.process_queue(limit=self.batch_size)
                cycle_stats["processed"] = result.processed_count
                cycle_stats["successful"] = result.successful_count
                cycle_stats["failed"] = result.failed_count
                cycle_stats["retried"] = result.retried_count
                self.total_processed += result.processed_count

                if result.processed_count > 0:
                    logger.info(
                        f"Queue cycle complete: {result.processed_count} processed, "
                        f"{result.successful_count} success, {result.retried_count} retried, "
                        f"{result.failed_count} failed."
                    )
                    await session.commit()

                # 3. Daily Auto-Apply Scheduler (10:00 AM IST)
                await self._check_and_trigger_daily_routine(session)

                # 4. Periodic Connector Health Check (every 10 cycles)
                if self.cycle_count % 10 == 0:
                    connectors = connector_registry.get_all_capabilities()
                    healthy_count = sum(1 for c in connectors if c.status.value == "HEALTHY")
                    logger.info(f"Connector health check: {healthy_count}/{len(connectors)} connectors healthy.")

            except Exception as exc:
                logger.error(f"Error during worker cycle {self.cycle_count}: {exc}", exc_info=True)
                await session.rollback()

        return cycle_stats

    async def _check_and_trigger_daily_routine(self, session: AsyncSession, now_kolkata: Optional[datetime] = None):
        """Checks if 10:00 AM Asia/Kolkata (IST) has arrived today and triggers the routine once per calendar day."""
        from zoneinfo import ZoneInfo
        from app.database.models.application import AutoApplyDailyRun
        from app.modules.applications.daily_routine import AutoApplyDailyRoutineService

        if now_kolkata is None:
            kolkata_tz = ZoneInfo("Asia/Kolkata")
            now_kolkata = datetime.now(timezone.utc).astimezone(kolkata_tz)

        # Check if the time is at or past 10:00 AM IST today
        if now_kolkata.hour >= 10:
            today_str = now_kolkata.strftime("%Y-%m-%d")
            if getattr(self, "_last_daily_routine_date", None) != today_str:
                # Also check database to ensure no other worker or process ran today's scheduled run
                today_start_utc = now_kolkata.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
                stmt_today = select(AutoApplyDailyRun).where(AutoApplyDailyRun.started_at >= today_start_utc)
                existing = (await session.execute(stmt_today)).scalars().first()

                if not existing:
                    logger.info(f"10:00 AM IST reached ({now_kolkata.strftime('%Y-%m-%d %H:%M:%S %Z')}). Disagreeing with idle; triggering Daily Auto-Apply routine.")
                    routine_svc = AutoApplyDailyRoutineService(session)
                    runs = await routine_svc.execute_daily_routine_for_all_active_users(
                        scheduled_time=now_kolkata.replace(hour=10, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
                    )
                    logger.info(f"Daily Auto-Apply routine completed for {len(runs)} users.")

                self._last_daily_routine_date = today_str

    async def start(self):
        """Starts the worker processing loop."""
        self.is_running = True
        self.register_signals()
        logger.info(
            f"Production Worker started. Environment: {settings.ENVIRONMENT}. "
            f"Poll Interval: {self.poll_interval}s, Batch Size: {self.batch_size}, "
            f"Lease Timeout: {settings.WORKER_LEASE_SECONDS}s"
        )

        # Ensure database tables exist
        await init_db()

        while self.is_running and not self._stop_event.is_set():
            start_time = time.time()
            try:
                await self.run_cycle()
            except Exception as exc:
                logger.error(f"Unhandled exception in worker loop: {exc}", exc_info=True)

            elapsed = time.time() - start_time
            sleep_time = max(0.5, self.poll_interval - elapsed)

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=sleep_time)
            except asyncio.TimeoutError:
                pass

        logger.info(
            f"Worker stopped gracefully. Total cycles: {self.cycle_count}, "
            f"Total items processed: {self.total_processed}, "
            f"Total leases recovered: {self.total_recovered}"
        )

    def stop(self):
        """Stops the worker loop."""
        self.is_running = False
        self._stop_event.set()


async def main():
    worker = ProductionWorker(
        poll_interval=int(getattr(settings, "WORKER_HEARTBEAT_SECONDS", 10)),
        batch_size=5
    )
    await worker.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Worker process terminated by user or OS.")
        sys.exit(0)
