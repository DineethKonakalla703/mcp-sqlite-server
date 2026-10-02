"""Natural Language SQLite MCP Server.

Provides Model Context Protocol (MCP) tools for an AI client to manage tasks
and projects stored in a local SQLite database.
"""

import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Supported MCP SDK imports across v1 and v2
try:
    from mcp.server.mcpserver import MCPServer
except ImportError:
    from mcp.server.fastmcp import FastMCP as MCPServer

from config import DB_PATH, logger
from src.database import (
    DatabaseError,
    ProjectNotFoundError,
    TaskNotFoundError,
    init_db,
)
from src.tools import (
    create_task_tool,
    get_project_tasks_tool,
    get_task_summary_tool,
    get_task_tool,
    list_projects_tool,
    list_tasks_tool,
    search_tasks_tool,
    update_task_status_tool,
)
from src.validation import ValidationError


def create_server(database_path: Optional[Path] = None) -> MCPServer:
    """Create and configure the MCP server instance with all tools registered."""
    target_db = database_path or DB_PATH

    server = MCPServer(
        name="mcp-sqlite-server",
        instructions="MCP server providing structured tools to query and manage tasks and projects in a local SQLite database.",
    )

    @server.tool(
        name="list_tasks",
        description=(
            "List tasks from the database with optional filtering by status and priority. "
            "Returns task IDs, titles, descriptions, statuses, priorities, due dates, and associated projects."
        ),
    )
    def list_tasks(
        status: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """List tasks with optional status and priority filtering.

        Args:
            status: Filter by status ('pending', 'in_progress', 'completed').
            priority: Filter by priority ('low', 'medium', 'high', 'urgent').
            limit: Maximum tasks to return (1-100, default 20).
        """
        try:
            return list_tasks_tool(
                status=status,
                priority=priority,
                limit=limit,
                db_path=target_db,
            )
        except ValidationError as exc:
            return {"success": False, "error": str(exc)}
        except DatabaseError as exc:
            logger.error(f"Database error in list_tasks: {exc}")
            return {"success": False, "error": "Database error retrieving tasks."}
        except Exception as exc:
            logger.exception(f"Unexpected error in list_tasks: {exc}")
            return {"success": False, "error": "An unexpected error occurred."}

    @server.tool(
        name="get_task",
        description="Retrieve complete details for a specific task using its unique integer ID.",
    )
    def get_task(task_id: int) -> Dict[str, Any]:
        """Get task by ID.

        Args:
            task_id: The positive integer ID of the task.
        """
        try:
            return get_task_tool(task_id=task_id, db_path=target_db)
        except (ValidationError, TaskNotFoundError) as exc:
            return {"success": False, "error": str(exc)}
        except DatabaseError as exc:
            logger.error(f"Database error in get_task: {exc}")
            return {"success": False, "error": "Database error retrieving task."}
        except Exception as exc:
            logger.exception(f"Unexpected error in get_task: {exc}")
            return {"success": False, "error": "An unexpected error occurred."}

    @server.tool(
        name="search_tasks",
        description=(
            "Search for tasks by matching text against titles and descriptions using parameterized queries. "
            "Safe against SQL injection."
        ),
    )
    def search_tasks(query: str, limit: int = 10) -> Dict[str, Any]:
        """Search tasks by title and description.

        Args:
            query: Non-empty search string (1-100 characters).
            limit: Maximum results to return (1-100, default 10).
        """
        try:
            return search_tasks_tool(query=query, limit=limit, db_path=target_db)
        except ValidationError as exc:
            return {"success": False, "error": str(exc)}
        except DatabaseError as exc:
            logger.error(f"Database error in search_tasks: {exc}")
            return {"success": False, "error": "Database error searching tasks."}
        except Exception as exc:
            logger.exception(f"Unexpected error in search_tasks: {exc}")
            return {"success": False, "error": "An unexpected error occurred."}

    @server.tool(
        name="list_projects",
        description="List all available projects along with their description, creation date, and number of associated tasks.",
    )
    def list_projects() -> Dict[str, Any]:
        """List all projects with task counts."""
        try:
            return list_projects_tool(db_path=target_db)
        except DatabaseError as exc:
            logger.error(f"Database error in list_projects: {exc}")
            return {"success": False, "error": "Database error retrieving projects."}
        except Exception as exc:
            logger.exception(f"Unexpected error in list_projects: {exc}")
            return {"success": False, "error": "An unexpected error occurred."}

    @server.tool(
        name="get_project_tasks",
        description="Retrieve all tasks assigned to a specific project by project ID.",
    )
    def get_project_tasks(project_id: int) -> Dict[str, Any]:
        """Get tasks for a specific project.

        Args:
            project_id: Positive integer ID of the project.
        """
        try:
            return get_project_tasks_tool(project_id=project_id, db_path=target_db)
        except (ValidationError, ProjectNotFoundError) as exc:
            return {"success": False, "error": str(exc)}
        except DatabaseError as exc:
            logger.error(f"Database error in get_project_tasks: {exc}")
            return {"success": False, "error": "Database error retrieving project tasks."}
        except Exception as exc:
            logger.exception(f"Unexpected error in get_project_tasks: {exc}")
            return {"success": False, "error": "An unexpected error occurred."}

    @server.tool(
        name="create_task",
        description=(
            "Create a new task in the database with title, optional description, priority, optional due date, "
            "and optional project assignment. Executed within an ACID transaction."
        ),
    )
    def create_task(
        title: str,
        description: str = "",
        priority: str = "medium",
        due_date: Optional[str] = None,
        project_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create a new task.

        Args:
            title: Title of the task (1-200 characters).
            description: Detailed description (up to 2000 characters).
            priority: Priority level ('low', 'medium', 'high', 'urgent'). Default is 'medium'.
            due_date: Optional due date in YYYY-MM-DD or ISO 8601 format.
            project_id: Optional project ID to link to this task.
        """
        try:
            return create_task_tool(
                title=title,
                description=description,
                priority=priority,
                due_date=due_date,
                project_id=project_id,
                db_path=target_db,
            )
        except (ValidationError, ProjectNotFoundError) as exc:
            return {"success": False, "error": str(exc)}
        except DatabaseError as exc:
            logger.error(f"Database error in create_task: {exc}")
            return {"success": False, "error": "Database error creating task."}
        except Exception as exc:
            logger.exception(f"Unexpected error in create_task: {exc}")
            return {"success": False, "error": "An unexpected error occurred."}

    @server.tool(
        name="update_task_status",
        description="Update the status of an existing task to 'pending', 'in_progress', or 'completed'.",
    )
    def update_task_status(task_id: int, status: str) -> Dict[str, Any]:
        """Update a task's status.

        Args:
            task_id: Positive integer ID of the task.
            status: New status ('pending', 'in_progress', 'completed').
        """
        try:
            return update_task_status_tool(
                task_id=task_id,
                status=status,
                db_path=target_db,
            )
        except (ValidationError, TaskNotFoundError) as exc:
            return {"success": False, "error": str(exc)}
        except DatabaseError as exc:
            logger.error(f"Database error in update_task_status: {exc}")
            return {"success": False, "error": "Database error updating task status."}
        except Exception as exc:
            logger.exception(f"Unexpected error in update_task_status: {exc}")
            return {"success": False, "error": "An unexpected error occurred."}

    @server.tool(
        name="get_task_summary",
        description=(
            "Calculate aggregate task metrics from the database including total tasks, "
            "breakdown by status, breakdown by priority, and overdue task count."
        ),
    )
    def get_task_summary() -> Dict[str, Any]:
        """Retrieve task summary metrics."""
        try:
            return get_task_summary_tool(db_path=target_db)
        except DatabaseError as exc:
            logger.error(f"Database error in get_task_summary: {exc}")
            return {"success": False, "error": "Database error computing task summary."}
        except Exception as exc:
            logger.exception(f"Unexpected error in get_task_summary: {exc}")
            return {"success": False, "error": "An unexpected error occurred."}

    return server


# Global server instance for direct execution / entrypoint
server = create_server()


def main() -> None:
    """Initialize database and start MCP server using stdio transport."""
    logger.info("Initializing SQLite database if not present...")
    init_db(DB_PATH)
    logger.info(f"Starting MCP SQLite Server over stdio (Database: {DB_PATH})")
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
