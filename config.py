"""Application configuration for SQLite MCP Server."""

import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Project Paths
PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_DB_PATH = DEFAULT_DATA_DIR / "tasks.db"

# Configure Database Path (can be overridden via DB_PATH environment variable)
_env_db_path = os.getenv("DB_PATH")
if _env_db_path:
    DB_PATH = Path(_env_db_path)
    if not DB_PATH.is_absolute():
        DB_PATH = PROJECT_ROOT / DB_PATH
else:
    DB_PATH = DEFAULT_DB_PATH

# Domain Constraints and Constants
VALID_STATUSES = frozenset({"pending", "in_progress", "completed"})
VALID_PRIORITIES = frozenset({"low", "medium", "high", "urgent"})

MAX_TITLE_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 2000
MAX_QUERY_LENGTH = 100
DEFAULT_QUERY_LIMIT = 20
MAX_QUERY_LIMIT = 100

# Logging Setup
# CRITICAL: For stdio-based MCP servers, logging MUST be directed to stderr
# because stdout is reserved exclusively for JSON-RPC protocol transport.
LOG_LEVEL_NAME = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_LEVEL = getattr(logging, LOG_LEVEL_NAME, logging.INFO)

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)

logger = logging.getLogger("mcp_sqlite_server")
