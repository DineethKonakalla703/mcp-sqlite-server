"""SQLite database connection, schema management, and query execution layer."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple, Union

from config import DB_PATH, logger


class DatabaseError(Exception):
    """Base exception for database operations."""
    pass


class TaskNotFoundError(DatabaseError):
    """Raised when a specified task does not exist."""
    pass


class ProjectNotFoundError(DatabaseError):
    """Raised when a specified project does not exist."""
    pass


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP)
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'in_progress', 'completed')),
    priority TEXT NOT NULL DEFAULT 'medium' CHECK(priority IN ('low', 'medium', 'high', 'urgent')),
    due_date TEXT,
    created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP)
);

CREATE TABLE IF NOT EXISTS task_projects (
    task_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    PRIMARY KEY (task_id, project_id),
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_task_projects_project ON task_projects(project_id);
"""


def escape_like_pattern(text: str) -> str:
    """Escape special characters in SQL LIKE patterns."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@contextmanager
def get_db_connection(
    database_path: Optional[Union[str, Path]] = None
) -> Generator[sqlite3.Connection, None, None]:
    """Provide a transactional SQLite database connection with row factory."""
    target_path = Path(database_path) if database_path else DB_PATH
    # Ensure directory exists if not an in-memory database
    if str(target_path) != ":memory:":
        target_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(
        str(target_path),
        timeout=10.0,
        detect_types=sqlite3.PARSE_DECLTYPES,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
    except Exception as exc:
        conn.rollback()
        logger.error(f"Database error during transaction: {exc}")
        raise
    finally:
        conn.close()


def init_db(database_path: Optional[Union[str, Path]] = None) -> None:
    """Initialize database tables and indexes safely."""
    try:
        with get_db_connection(database_path) as conn:
            with conn:
                conn.executescript(SCHEMA_SQL)
        logger.info(f"Database schema initialized successfully at {database_path or DB_PATH}")
    except sqlite3.Error as exc:
        logger.error(f"Failed to initialize database: {exc}")
        raise DatabaseError(f"Database initialization failed: {exc}") from exc


def get_task(task_id: int, database_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """Retrieve a single task by ID including its associated project."""
    query = """
        SELECT
            t.id, t.title, t.description, t.status, t.priority, t.due_date, t.created_at,
            tp.project_id, p.name AS project_name
        FROM tasks t
        LEFT JOIN task_projects tp ON t.id = tp.task_id
        LEFT JOIN projects p ON tp.project_id = p.id
        WHERE t.id = ?
    """
    try:
        with get_db_connection(database_path) as conn:
            row = conn.execute(query, (task_id,)).fetchone()
            if not row:
                raise TaskNotFoundError(f"Task with ID {task_id} not found.")
            return dict(row)
    except TaskNotFoundError:
        raise
    except sqlite3.Error as exc:
        logger.error(f"Error retrieving task {task_id}: {exc}")
        raise DatabaseError("Error retrieving task from database.") from exc


def list_tasks(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 20,
    database_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """List tasks with optional status and priority filtering."""
    query = """
        SELECT
            t.id, t.title, t.description, t.status, t.priority, t.due_date, t.created_at,
            tp.project_id, p.name AS project_name
        FROM tasks t
        LEFT JOIN task_projects tp ON t.id = tp.task_id
        LEFT JOIN projects p ON tp.project_id = p.id
    """
    conditions: List[str] = []
    params: List[Any] = []

    if status:
        conditions.append("t.status = ?")
        params.append(status)

    if priority:
        conditions.append("t.priority = ?")
        params.append(priority)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY t.id ASC LIMIT ?"
    params.append(limit)

    try:
        with get_db_connection(database_path) as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error as exc:
        logger.error(f"Error listing tasks: {exc}")
        raise DatabaseError("Error retrieving tasks from database.") from exc


def search_tasks(
    query_text: str,
    limit: int = 10,
    database_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Search task titles and descriptions using parameterized LIKE queries."""
    escaped_query = f"%{escape_like_pattern(query_text)}%"
    sql = """
        SELECT
            t.id, t.title, t.description, t.status, t.priority, t.due_date, t.created_at,
            tp.project_id, p.name AS project_name
        FROM tasks t
        LEFT JOIN task_projects tp ON t.id = tp.task_id
        LEFT JOIN projects p ON tp.project_id = p.id
        WHERE t.title LIKE ? ESCAPE '\\' OR t.description LIKE ? ESCAPE '\\'
        ORDER BY t.id ASC
        LIMIT ?
    """
    try:
        with get_db_connection(database_path) as conn:
            rows = conn.execute(sql, (escaped_query, escaped_query, limit)).fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error as exc:
        logger.error(f"Error searching tasks: {exc}")
        raise DatabaseError("Error searching tasks in database.") from exc


def list_projects(
    database_path: Optional[Union[str, Path]] = None
) -> List[Dict[str, Any]]:
    """List all projects with the count of associated tasks."""
    query = """
        SELECT
            p.id, p.name, p.description, p.created_at,
            COUNT(tp.task_id) AS task_count
        FROM projects p
        LEFT JOIN task_projects tp ON p.id = tp.project_id
        GROUP BY p.id
        ORDER BY p.id ASC
    """
    try:
        with get_db_connection(database_path) as conn:
            rows = conn.execute(query).fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error as exc:
        logger.error(f"Error listing projects: {exc}")
        raise DatabaseError("Error retrieving projects from database.") from exc


def get_project_tasks(
    project_id: int,
    database_path: Optional[Union[str, Path]] = None
) -> List[Dict[str, Any]]:
    """Retrieve all tasks associated with a given project."""
    # First verify project existence
    project_check_sql = "SELECT id, name FROM projects WHERE id = ?"
    tasks_sql = """
        SELECT
            t.id, t.title, t.description, t.status, t.priority, t.due_date, t.created_at,
            tp.project_id, p.name AS project_name
        FROM tasks t
        JOIN task_projects tp ON t.id = tp.task_id
        JOIN projects p ON tp.project_id = p.id
        WHERE tp.project_id = ?
        ORDER BY t.id ASC
    """
    try:
        with get_db_connection(database_path) as conn:
            project_row = conn.execute(project_check_sql, (project_id,)).fetchone()
            if not project_row:
                raise ProjectNotFoundError(f"Project with ID {project_id} not found.")

            rows = conn.execute(tasks_sql, (project_id,)).fetchall()
            return [dict(row) for row in rows]
    except ProjectNotFoundError:
        raise
    except sqlite3.Error as exc:
        logger.error(f"Error fetching tasks for project {project_id}: {exc}")
        raise DatabaseError("Error retrieving project tasks from database.") from exc


def create_task(
    title: str,
    description: str = "",
    priority: str = "medium",
    due_date: Optional[str] = None,
    project_id: Optional[int] = None,
    database_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Create a new task and optionally link it to a project inside a transaction."""
    try:
        with get_db_connection(database_path) as conn:
            with conn:
                # If project_id is given, verify it exists first
                if project_id is not None:
                    p_check = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
                    if not p_check:
                        raise ProjectNotFoundError(f"Project with ID {project_id} not found.")

                cursor = conn.execute(
                    """
                    INSERT INTO tasks (title, description, status, priority, due_date)
                    VALUES (?, ?, 'pending', ?, ?)
                    """,
                    (title, description, priority, due_date),
                )
                new_task_id = cursor.lastrowid

                if project_id is not None:
                    conn.execute(
                        "INSERT INTO task_projects (task_id, project_id) VALUES (?, ?)",
                        (new_task_id, project_id),
                    )

        # Retrieve and return created task
        return get_task(new_task_id, database_path=database_path)
    except (ProjectNotFoundError, TaskNotFoundError):
        raise
    except sqlite3.Error as exc:
        logger.error(f"Error creating task: {exc}")
        raise DatabaseError("Failed to create task in database.") from exc


def update_task_status(
    task_id: int,
    status: str,
    database_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Update task status."""
    try:
        with get_db_connection(database_path) as conn:
            with conn:
                # Verify existence
                check = conn.execute("SELECT id FROM tasks WHERE id = ?", (task_id,)).fetchone()
                if not check:
                    raise TaskNotFoundError(f"Task with ID {task_id} not found.")

                conn.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))

        return get_task(task_id, database_path=database_path)
    except TaskNotFoundError:
        raise
    except sqlite3.Error as exc:
        logger.error(f"Error updating task {task_id} status: {exc}")
        raise DatabaseError("Failed to update task status in database.") from exc


def get_task_summary(
    database_path: Optional[Union[str, Path]] = None
) -> Dict[str, Any]:
    """Calculate aggregate task statistics from the database."""
    try:
        with get_db_connection(database_path) as conn:
            # Total tasks
            total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]

            # Grouped by status
            status_rows = conn.execute(
                "SELECT status, COUNT(*) AS cnt FROM tasks GROUP BY status"
            ).fetchall()
            by_status = {s: 0 for s in ("pending", "in_progress", "completed")}
            for r in status_rows:
                by_status[r["status"]] = r["cnt"]

            # Grouped by priority
            priority_rows = conn.execute(
                "SELECT priority, COUNT(*) AS cnt FROM tasks GROUP BY priority"
            ).fetchall()
            by_priority = {p: 0 for p in ("low", "medium", "high", "urgent")}
            for r in priority_rows:
                by_priority[r["priority"]] = r["cnt"]

            # Overdue tasks: due_date < current date and status != 'completed'
            overdue_row = conn.execute(
                """
                SELECT COUNT(*) FROM tasks
                WHERE due_date IS NOT NULL
                  AND date(due_date) < date('now')
                  AND status != 'completed'
                """
            ).fetchone()
            overdue = overdue_row[0] if overdue_row else 0

            return {
                "total_tasks": total,
                "by_status": by_status,
                "by_priority": by_priority,
                "overdue_tasks": overdue,
            }
    except sqlite3.Error as exc:
        logger.error(f"Error computing task summary: {exc}")
        raise DatabaseError("Failed to calculate task summary.") from exc
