from __future__ import annotations

import argparse
import logging
from pathlib import Path

from dotenv import load_dotenv

from src.ingest.importer import Importer


def discover_txt_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.txt") if p.is_file())


def main() -> None:
    parser = argparse.ArgumentParser(description="Bulk import TXT books into MySQL")
    parser.add_argument("root", nargs="?", default="books", help="Root directory containing TXT files")
    parser.add_argument("--limit", type=int, default=None, help="Optional maximum number of files to import")
    parser.add_argument("--log-level", default="INFO", help="Logging level (default: INFO)")
    parser.add_argument("--env", default=".env", help="Path to .env file")
    args = parser.parse_args()

    load_dotenv(args.env)
    logging.basicConfig(level=args.log_level.upper(), format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")

    root_path = Path(args.root)
    if not root_path.exists():
        raise FileNotFoundError(root_path)

    files = discover_txt_files(root_path)
    if args.limit is not None:
        files = files[: args.limit]
    logging.info("Discovered %s TXT files under %s", len(files), root_path)

    importer = Importer()
    for idx, file_path in enumerate(files, start=1):
        logging.info("[%s/%s] Importing %s", idx, len(files), file_path)
        try:
            importer.import_file(str(file_path))
        except Exception as exc:  # pylint: disable=broad-except
            logging.exception("Failed to import %s: %s", file_path, exc)


if __name__ == "__main__":
    main()
