from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta

from sqlalchemy import text

from src.infra.database import get_session_factory, init_engine

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

RESET_SQL = text(
    """
    UPDATE fct_chapter_tasks
    SET status = 'PENDING',
        retry_count = retry_count + 1,
        locked_by = NULL,
        locked_at = NULL,
        last_heartbeat = NULL,
        next_retry_at = NOW(6),
        error_log = CONCAT(IFNULL(error_log, ''), :log_suffix)
    WHERE status = 'PROCESSING' AND last_heartbeat < :cutoff
    """
)


def run_watchdog() -> None:
    threshold_minutes = int(os.environ.get("WATCHDOG_THRESHOLD_MINUTES", "5"))
    interval_seconds = int(os.environ.get("WATCHDOG_INTERVAL_SECONDS", "60"))
    init_engine()
    session_factory = get_session_factory()

    while True:
        cutoff = datetime.utcnow() - timedelta(minutes=threshold_minutes)
        log_suffix = f"\nReset by Watchdog at {datetime.utcnow().isoformat()}"
        with session_factory() as session:
            result = session.execute(RESET_SQL, {"cutoff": cutoff, "log_suffix": log_suffix})
            session.commit()
            if result.rowcount:
                logger.warning("Watchdog reset %s tasks", result.rowcount)
            else:
                logger.debug("No stale tasks detected")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    run_watchdog()
