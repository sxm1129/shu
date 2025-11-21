from __future__ import annotations

import logging
import os
import signal
import socket

from src.infra.database import init_engine
from src.worker.fetcher import TaskFetcher
from src.worker.processor import TaskProcessor

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


def main() -> None:
    worker_id = os.environ.get("WORKER_ID") or f"worker-{socket.gethostname()}"
    init_engine()
    fetcher = TaskFetcher()
    processor = TaskProcessor(worker_id=worker_id)

    running = True

    def _shutdown(signum, frame):  # noqa: ARG001 - required signature
        nonlocal running
        logger.info("Received signal %s, shutting down...", signum)
        running = False

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    while running:
        try:
            task = fetcher.fetch_one_task(worker_id)
            if not task:
                TaskFetcher.idle()
                continue
            processor.process_task(task)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Worker loop error: %s", exc)
            TaskFetcher.idle()


if __name__ == "__main__":
    main()
