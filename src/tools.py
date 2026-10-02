"""Implementation of the 8 MCP task-management tools.

This module encapsulates validation and business logic for all tools exposed
by the MCP server.
"""

from typing import Any, Dict, List, Optional
from pathlib import Path
from src.database import (
    DatabaseError,
    ProjectNotFoundError,
    TaskNotFoundError,
    create_task as db_create_task,
    get_project_tasks as db_get_project_tasks,
    get_task as db_get_task,
    get_task_summary as db_get_task_summary,
    list_projects as db_list_projects,
    list_tasks as db_list_tasks,
    search_tasks as db_search_tasks,
    update_task_status as db_update_task_status,
)
from src.validation import (
    ValidationError,
    validate_description,
    validate_due_date,
    validate_id,
    validate_limit,
    validate_priority,
    validate_query,
    validate_status,
    validate_title,
)


def list_tasks_tool(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 20,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Retrieve tasks with optional status and priority filtering.

    Args:
        status: Optional filter by status ('pending', 'in_progress', 'completed').
        priority: Optional filter by priority ('low', 'medium', 'high', 'urgent').
        limit: Maximum number of tasks to return (1 to 100, default 20).
        db_path: Optional custom database path for testing.

    Returns:
        A dictionary containing the task list and result count.
    """
    valid_status = validate_status(status) if status is not None else None
    valid_priority = validate_priority(priority) if priority is not None else None
    valid_limit = validate_limit(limit, default=20)

    tasks = db_list_tasks(
        status=valid_status,
        priority=valid_priority,
        limit=valid_limit,
        database_path=db_path,
    )
    return {
        "count": len(tasks),
        "limit": valid_limit,
        "tasks": tasks,
    }


def get_task_tool(
    task_id: int,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Retrieve details for a specific task by ID.

    Args:
        task_id: The unique positive integer identifier of the task.
        db_path: Optional custom database path for testing.

    Returns:
        The task details including associated project.
    """
    valid_id = validate_id(task_id, field_name="task_id")
    task = db_get_task(task_id=valid_id, database_path=db_path)
    return {"task": task}


def search_tasks_tool(
    query: str,
    limit: int = 10,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Search tasks by keywords in their title or description.

    Args:
        query: Search text to match against title or description.
        limit: Maximum number of matching tasks to return (1 to 100, default 10).
        db_path: Optional custom database path for testing.

    Returns:
        A dictionary containing matching tasks and the search query.
    """
    valid_query = validate_query(query)
    valid_limit = validate_limit(limit, default=10)

    matches = db_search_tasks(
        query_text=valid_query,
        limit=valid_limit,
        database_path=db_path,
    )
    return {
        "query": valid_query,
        "count": len(matches),
        "limit": valid_limit,
        "tasks": matches,
    }


def list_projects_tool(
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """List all projects and their count of associated tasks.

    Args:
        db_path: Optional custom database path for testing.

    Returns:
        A dictionary containing the list of projects and total count.
    """
    projects = db_list_projects(database_path=db_path)
    return {
        "count": len(projects),
        "projects": projects,
    }


def get_project_tasks_tool(
    project_id: int,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Retrieve all tasks associated with a specific project.

    Args:
        project_id: The unique positive integer identifier of the project.
        db_path: Optional custom database path for testing.

    Returns:
        A dictionary containing the project ID and associated tasks.
    """
    valid_id = validate_id(project_id, field_name="project_id")
    tasks = db_get_project_tasks(project_id=valid_id, database_path=db_path)
    return {
        "project_id": valid_id,
        "count": len(tasks),
        "tasks": tasks,
    }


def create_task_tool(
    title: str,
    description: str = "",
    priority: str = "medium",
    due_date: Optional[str] = None,
    project_id: Optional[int] = None,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Create a new task with optional project assignment.

    Args:
        title: Title of the task (1-200 characters).
        description: Detailed task description (up to 2000 characters).
        priority: Priority level ('low', 'medium', 'high', 'urgent').
        due_date: Optional due date in YYYY-MM-DD or ISO 8601 format.
        project_id: Optional project identifier to associate with the task.
        db_path: Optional custom database path for testing.

    Returns:
        The newly created task record.
    """
    valid_title = validate_title(title)
    valid_description = validate_description(description)
    valid_priority = validate_priority(priority)
    valid_due_date = validate_due_date(due_date)
    valid_project_id = validate_id(project_id, field_name="project_id") if project_id is not None else None

    task = db_create_task(
        title=valid_title,
        description=valid_description,
        priority=valid_priority,
        due_date=valid_due_date,
        project_id=valid_project_id,
        database_path=db_path,
    )
    return {
        "message": "Task created successfully.",
        "task": task,
    }


def update_task_status_tool(
    task_id: int,
    status: str,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Update the status of an existing task.

    Args:
        task_id: Unique positive integer identifier of the task.
        status: New status ('pending', 'in_progress', 'completed').
        db_path: Optional custom database path for testing.

    Returns:
        The updated task record.
    """
    valid_id = validate_id(task_id, field_name="task_id")
    valid_status = validate_status(status)

    updated_task = db_update_task_status(
        task_id=valid_id,
        status=valid_status,
        database_path=db_path,
    )
    return {
        "message": f"Task {valid_id} status updated to '{valid_status}'.",
        "task": updated_task,
    }


def get_task_summary_tool(
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Retrieve aggregate statistics about tasks in the database.

    Includes total count, tasks by status, tasks by priority, and overdue count.

    Args:
        db_path: Optional custom database path for testing.

    Returns:
        Summary metrics dictionary.
    """
    summary = db_get_task_summary(database_path=db_path)
    return {"summary": summary}
