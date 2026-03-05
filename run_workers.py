"""
FormNest — Worker Runner Entry Point

Usage:
    uv run run_workers.py                    # All workers
    uv run run_workers.py --workers submission,email  # Specific workers
"""

import argparse
import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-30s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger("formnest.workers")

AVAILABLE_WORKERS = {
    "submission": "server.workers.submission:run_submission_worker",
    "email": "server.workers.email:run_email_worker",
    "webhook": "server.workers.webhook:run_webhook_worker",
}


async def run_workers(worker_names: list[str]) -> None:
    """Run selected workers concurrently."""
    from server.core.redis import init_redis

    await init_redis()

    tasks = []
    for name in worker_names:
        if name not in AVAILABLE_WORKERS:
            logger.error(f"Unknown worker: {name}. Available: {list(AVAILABLE_WORKERS.keys())}")
            continue

        module_path, func_name = AVAILABLE_WORKERS[name].rsplit(":", 1)
        module = __import__(module_path, fromlist=[func_name])
        worker_func = getattr(module, func_name)

        tasks.append(asyncio.create_task(worker_func()))
        logger.info(f"Started worker: {name}")

    if not tasks:
        logger.error("No workers started")
        return

    logger.info(f"🚀 {len(tasks)} worker(s) running")

    # Wait for all workers (they run forever until interrupted)
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        logger.info("Workers cancelled")


def main():
    parser = argparse.ArgumentParser(description="FormNest Worker Runner")
    parser.add_argument(
        "--workers",
        default=",".join(AVAILABLE_WORKERS.keys()),
        help=f"Comma-separated worker names. Available: {', '.join(AVAILABLE_WORKERS.keys())}",
    )
    args = parser.parse_args()

    worker_names = [w.strip() for w in args.workers.split(",")]
    logger.info(f"🏗️  Starting FormNest Workers: {worker_names}")

    try:
        asyncio.run(run_workers(worker_names))
    except KeyboardInterrupt:
        logger.info("Workers stopped")
        sys.exit(0)


if __name__ == "__main__":
    main()
