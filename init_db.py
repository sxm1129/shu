from __future__ import annotations

import argparse
import os
from pathlib import Path

from urllib.parse import quote_plus

from sqlalchemy import create_engine

from src.models import Base


def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    with env_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def build_db_url() -> str:
    user = os.environ.get("DB_USER", "root")
    password = os.environ.get("DB_PASSWORD", "")
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "3306")
    name = os.environ.get("DB_NAME", "tts_library")
    encoded_password = quote_plus(password)
    return f"mysql+pymysql://{user}:{encoded_password}@{host}:{port}/{name}?charset=utf8mb4"


def init_database(db_url: str) -> None:
    engine = create_engine(db_url, future=True)
    Base.metadata.create_all(engine)
    engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize MySQL schema for TTS system")
    parser.add_argument("--env", default=".env", help="Path to .env file (default: .env)")
    parser.add_argument("--url", default=None, help="Optional SQLAlchemy DB URL override")
    args = parser.parse_args()

    load_env_file(Path(args.env))

    db_url = args.url or build_db_url()
    print(f"Using database URL: {db_url}")
    init_database(db_url)
    print("Database schema initialized successfully.")


if __name__ == "__main__":
    main()
