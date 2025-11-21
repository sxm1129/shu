from __future__ import annotations

from typing import Iterable, Sequence

import logging

from sqlalchemy import func, select
from sqlalchemy.dialects.mysql import insert as mysql_insert

from src.infra.database import get_session_factory
from src.ingest.parser import BookMetadata, BookParser, Chapter
from src.models import ChapterTask, DimBook

BATCH_SIZE = 200
logger = logging.getLogger(__name__)


class Importer:
    def __init__(self):
        self._session_factory = get_session_factory()

    def import_file(self, file_path: str) -> int:
        logger.info("Parsing book file: %s", file_path)
        parser = BookParser(file_path)
        metadata = parser.parse()
        logger.info(
            "Parsed book '%s' with %s chapters",
            metadata.title,
            len(metadata.chapters),
        )
        book_id = self.upsert_book(metadata)
        self.bulk_insert_chapters(book_id, metadata.chapters)
        logger.info("Import completed for '%s' (book_id=%s)", metadata.title, book_id)
        return book_id

    def upsert_book(self, metadata: BookMetadata) -> int:
        stmt = mysql_insert(DimBook).values(
            title=metadata.title,
            author=metadata.author,
            total_chapters=len(metadata.chapters),
        )
        upsert_stmt = stmt.on_duplicate_key_update(
            author=stmt.inserted.author,
            total_chapters=stmt.inserted.total_chapters,
        )
        with self._session_factory() as session:
            result = session.execute(upsert_stmt)
            session.commit()
            if result.lastrowid:
                logger.info("Inserted new book '%s' with id %s", metadata.title, result.lastrowid)
                return result.lastrowid
            book_id = session.execute(select(DimBook.book_id).where(DimBook.title == metadata.title)).scalar_one()
            logger.info("Book '%s' already exists with id %s; updating metadata", metadata.title, book_id)
            return book_id

    def bulk_insert_chapters(self, book_id: int, chapters: Sequence[Chapter]) -> None:
        if not chapters:
            return
        total = 0
        with self._session_factory() as session:
            for chunk in _chunk(chapters, BATCH_SIZE):
                values = [
                    {
                        "book_id": book_id,
                        "chapter_index": chapter.index,
                        "chapter_title": chapter.title,
                        "content_text": chapter.content,
                        "priority": 10,
                    }
                    for chapter in chunk
                ]
                stmt = mysql_insert(ChapterTask).values(values)
                update_stmt = stmt.on_duplicate_key_update(
                    chapter_title=stmt.inserted.chapter_title,
                    content_text=stmt.inserted.content_text,
                    status="PENDING",
                    priority=func.least(ChapterTask.priority, stmt.inserted.priority),
                    retry_count=0,
                    next_retry_at=func.now(),
                    locked_by=None,
                    locked_at=None,
                    last_heartbeat=None,
                    audio_url=None,
                    audio_duration=None,
                    error_log=None,
                )
                session.execute(update_stmt)
                total += len(values)
                logger.debug("Upserted %s chapters for book_id=%s (running total=%s)", len(values), book_id, total)
            session.commit()
        logger.info("Completed chapter upsert for book_id=%s, total chapters processed=%s", book_id, total)


def _chunk(items: Sequence, size: int) -> Iterable[Sequence]:
    for idx in range(0, len(items), size):
        yield items[idx : idx + size]


__all__ = ["Importer"]
