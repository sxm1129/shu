from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator, Optional

from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

try:  # optional dependency
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - best effort load
    pass

_ENGINE: Optional[Engine] = None
_SESSION_FACTORY: Optional[sessionmaker] = None


def _build_db_url() -> str:
    if url := os.environ.get("DATABASE_URL"):
        return url
    user = os.environ.get("DB_USER", "root")
    password = os.environ.get("DB_PASSWORD", "")
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "3306")
    name = os.environ.get("DB_NAME", "tts_library")
    encoded_password = quote_plus(password)
    return f"mysql+pymysql://{user}:{encoded_password}@{host}:{port}/{name}?charset=utf8mb4"


def init_engine(db_url: Optional[str] = None) -> Engine:
    global _ENGINE, _SESSION_FACTORY
    if _ENGINE is not None:
        return _ENGINE
    url = db_url or _build_db_url()
    _ENGINE = create_engine(
        url,
        future=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,
        pool_pre_ping=True,
    )
    _SESSION_FACTORY = sessionmaker(bind=_ENGINE, expire_on_commit=False, future=True)
    return _ENGINE


def get_engine() -> Engine:
    if _ENGINE is None:
        return init_engine()
    return _ENGINE


def get_session_factory() -> sessionmaker:
    if _SESSION_FACTORY is None:
        init_engine()
    assert _SESSION_FACTORY is not None
    return _SESSION_FACTORY


@contextmanager
def get_db_session() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
