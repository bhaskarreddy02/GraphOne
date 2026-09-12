"""
Continuous Pipeline Scheduler Daemon
Runs recurring monitoring cycles across all 10 sources at a configurable interval (default: 30 minutes).
Tracks per-cycle metrics, survives mid-run interrupts, and supports graceful shutdown.
"""

import argparse
import asyncio
import logging
import os
import signal
import sys
from datetime import datetime, timezone, timedelta
from typing import Optional

from src.pipeline.monitor import ContinuousMonitoringPipeline
from src.pipeline.state_store import PipelineStateStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("SchedulerDaemon")


class PipelineScheduler:
    def __init__(self, interval_minutes: int = 30):
        self.interval_minutes = interval_minutes
        self.interval_seconds = interval_minutes * 60
        self.running = False
        self.pipeline = ContinuousMonitoringPipeline()
        self.current_task: Optional[asyncio.Task] = None

    async def start(self):
        """Starts the recurring scheduler loop."""
        self.running = True
        logger.info("=" * 70)
        logger.info("STARTING PIPELINE SCHEDULER DAEMON")
        logger.info(f"Execution Frequency: Every {self.interval_minutes} minutes ({self.interval_seconds}s)")
        logger.info("Press Ctrl+C to stop.")
        logger.info("=" * 70)

        cycle_count = 0
        while self.running:
            cycle_count += 1
            cycle_start = datetime.now(timezone.utc)
            next_run = cycle_start + timedelta(seconds=self.interval_seconds)

            logger.info(f"[Scheduler] Initiating Cycle #{cycle_count} at {cycle_start.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            try:
                summary = await self.pipeline.run_cycle()
                logger.info(f"[Scheduler] Cycle #{cycle_count} Status: {summary['status']} "
                            f"(Fresh: {summary['passed_freshness']}, Stale: {summary['discarded_stale']}, "
                            f"Skipped Seen: {summary['already_seen_skipped']})")
            except asyncio.CancelledError:
                logger.info("[Scheduler] Execution cancelled gracefully.")
                break
            except Exception as e:
                logger.error(f"[Scheduler] Unexpected cycle failure: {e}", exc_info=True)

            if not self.running:
                break

            sleep_seconds = self.interval_seconds
            logger.info(f"[Scheduler] Next cycle scheduled at {next_run.strftime('%Y-%m-%d %H:%M:%S UTC')} "
                        f"(sleeping {self.interval_minutes}m)...")

            try:
                # Sleep in increments to allow quick response to cancellation
                for _ in range(int(sleep_seconds)):
                    if not self.running:
                        break
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                break

        logger.info("[Scheduler] Scheduler loop exited successfully.")

    def stop(self):
        """Signals the scheduler to stop gracefully."""
        logger.info("[Scheduler] Stop signal received.")
        self.running = False


async def run_daemon(interval_minutes: int, run_once: bool = False):
    scheduler = PipelineScheduler(interval_minutes=interval_minutes)

    # Setup signal handlers where supported
    loop = asyncio.get_running_loop()
    for sig_name in ("SIGINT", "SIGTERM"):
        if hasattr(signal, sig_name):
            try:
                loop.add_signal_handler(getattr(signal, sig_name), lambda: scheduler.stop())
            except NotImplementedError:
                # Windows event loop doesn't always support add_signal_handler
                pass

    try:
        if run_once:
            logger.info("[Scheduler] Running in one-shot mode (--once)...")
            summary = await scheduler.pipeline.run_cycle()
            logger.info(f"[Scheduler] Single run completed: {summary['status']}")
            return summary
        else:
            await scheduler.start()
    finally:
        await scheduler.pipeline.close()



def main():
    parser = argparse.ArgumentParser(description="Continuous News & Jobs Monitoring Pipeline Scheduler")
    parser.add_argument(
        "--interval",
        type=int,
        default=int(os.getenv("PIPELINE_INTERVAL_MINUTES", "30")),
        help="Crawl cycle interval in minutes (default: 30)"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single cycle and exit immediately"
    )
    args = parser.parse_args()

    try:
        asyncio.run(run_daemon(interval_minutes=args.interval, run_once=args.once))
    except KeyboardInterrupt:
        logger.info("\n[Scheduler] Interrupted by user. Shutting down...")


if __name__ == "__main__":
    main()
