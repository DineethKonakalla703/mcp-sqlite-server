"""Database initialization script.

Creates the SQLite schema (tables, foreign keys, and indexes) if they do not already exist.
Preserves existing data.
"""

import sys
from pathlib import Path

# Add project root to sys.path so imports work seamlessly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import DB_PATH, logger
from src.database import init_db


def main() -> None:
    """Initialize the SQLite database schema."""
    logger.info(f"Initializing database at: {DB_PATH}")
    try:
        init_db(DB_PATH)
        print(f"Database successfully initialized at: {DB_PATH}")
    except Exception as exc:
        print(f"Error initializing database: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
