from __future__ import annotations

from typing import List

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
    Index,
)
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class DimBook(Base):
    __tablename__ = "dim_books"
    __allow_unmapped__ = True

    book_id = Column(BigInteger, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False, unique=True, index=True)
    author = Column(String(100))
    total_chapters = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    chapters: List["ChapterTask"] = relationship("ChapterTask", back_populates="book", cascade="all, delete-orphan")


class ChapterTask(Base):
    __tablename__ = "fct_chapter_tasks"
    __table_args__ = (
        Index("idx_fetch_task", "status", "priority", "next_retry_at"),
        Index("uq_chapter", "book_id", "chapter_index", unique=True),
    )
    __allow_unmapped__ = True

    task_id = Column(BigInteger, primary_key=True, autoincrement=True)
    book_id = Column(BigInteger, ForeignKey("dim_books.book_id", ondelete="CASCADE"), nullable=False)
    chapter_index = Column(Integer, nullable=False)
    chapter_title = Column(String(512), nullable=False)
    content_text = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"), nullable=False)
    status = Column(
        Enum("PENDING", "PROCESSING", "COMPLETED", "FAILED", name="task_status"),
        nullable=False,
        server_default="PENDING",
    )
    priority = Column(SmallInteger, nullable=False, server_default="10")
    retry_count = Column(Integer, nullable=False, server_default="0")
    next_retry_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    locked_by = Column(String(128))
    locked_at = Column(DateTime(timezone=True))
    last_heartbeat = Column(DateTime(timezone=True))
    audio_url = Column(String(512))
    audio_duration = Column(Integer)
    error_log = Column(Text)

    book: DimBook = relationship("DimBook", back_populates="chapters")


__all__ = ["Base", "DimBook", "ChapterTask"]
