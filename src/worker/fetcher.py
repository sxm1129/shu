from __future__ import annotations

import random
import time
from typing import Optional

from sqlalchemy import text

from src.infra.database import get_session_factory
from src.models import ChapterTask

FETCH_SQL = text(
    """
    SELECT task_id FROM fct_chapter_tasks
    WHERE status = 'PENDING' AND next_retry_at <= NOW(6)
    ORDER BY priority DESC, next_retry_at ASC
    LIMIT 1
    FOR UPDATE SKIP LOCKED
    """
)

UPDATE_SQL = text(
    """
    UPDATE fct_chapter_tasks
    SET status = 'PROCESSING', locked_by = :worker_id, locked_at = NOW(6), last_heartbeat = NOW(6)
    WHERE task_id = :task_id
    """
)


class TaskFetcher:
    def __init__(self):
        self._session_factory = get_session_factory()

    def fetch_one_task(self, worker_id: str) -> Optional[ChapterTask]:
        task_id = self._attempt_lock(worker_id)
        if task_id is None:
            return None
        with self._session_factory() as session:
            return session.get(ChapterTask, task_id)

    def _attempt_lock(self, worker_id: str) -> Optional[int]:
        session = self._session_factory()
        try:
            with session.begin():
                row = session.execute(FETCH_SQL).first()
                if not row:
                    return None
                task_id = row.task_id
                session.execute(UPDATE_SQL, {"task_id": task_id, "worker_id": worker_id})
                return task_id
        finally:
            session.close()

    @staticmethod
    def idle():
        time.sleep(random.uniform(0.5, 2.0))
