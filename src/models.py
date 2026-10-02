"""Data models for SQLite MCP Server."""

from typing import Optional, Dict
from pydantic import BaseModel, Field


class Task(BaseModel):
    """Task model representing a record in the tasks table."""

    id: int
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    due_date: Optional[str] = None
    created_at: str
    project_id: Optional[int] = None
    project_name: Optional[str] = None


class Project(BaseModel):
    """Project model representing a record in the projects table."""

    id: int
    name: str
    description: Optional[str] = None
    created_at: str
    task_count: int = 0


class TaskSummary(BaseModel):
    """Task summary statistics."""

    total_tasks: int
    by_status: Dict[str, int]
    by_priority: Dict[str, int]
    overdue_tasks: int


class TaskCreateInput(BaseModel):
    """Validated input model for task creation."""

    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default="", max_length=2000)
    priority: str = Field(default="medium")
    due_date: Optional[str] = None
    project_id: Optional[int] = None


class TaskStatusUpdateInput(BaseModel):
    """Validated input model for task status update."""

    task_id: int = Field(..., gt=0)
    status: str


class TaskFilterInput(BaseModel):
    """Validated input model for listing tasks."""

    status: Optional[str] = None
    priority: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=100)


class TaskSearchInput(BaseModel):
    """Validated input model for searching tasks."""

    query: str = Field(..., min_length=1, max_length=100)
    limit: int = Field(default=10, ge=1, le=100)
