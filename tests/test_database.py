"""Tests for the SQLite database access layer."""

import pytest
from pathlib import Path
from scripts.seed_db import seed_db
from src.database import (
    ProjectNotFoundError,
    TaskNotFoundError,
    create_task,
    get_db_connection,
    get_project_tasks,
    get_task,
    get_task_summary,
    init_db,
    list_projects,
    list_tasks,
    search_tasks,
    update_task_status,
)


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    """Fixture providing a fresh initialized temporary database."""
    db_file = tmp_path / "test_tasks.db"
    init_db(db_file)
    return db_file


@pytest.fixture
def seeded_db(temp_db: Path) -> Path:
    """Fixture providing a seeded temporary database."""
    seed_db(temp_db)
    return temp_db


class TestDatabase:
    """Test suite for database layer operations."""

    def test_schema_initialization(self, temp_db: Path):
        """Test that schema creates tables, indexes, and enables foreign keys."""
        with get_db_connection(temp_db) as conn:
            # Check tables exist
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            assert "tasks" in tables
            assert "projects" in tables
            assert "task_projects" in tables

            # Verify foreign keys are enabled
            fk_status = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
            assert fk_status == 1

    def test_seeding_and_duplicate_prevention(self, temp_db: Path):
        """Test that seeding inserts data and second execution causes no duplicates."""
        seed_db(temp_db)
        with get_db_connection(temp_db) as conn:
            initial_task_count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            initial_project_count = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
            assert initial_task_count > 0
            assert initial_project_count > 0

        # Run seed again to ensure idempotency
        seed_db(temp_db)
        with get_db_connection(temp_db) as conn:
            recheck_task_count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            recheck_project_count = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
            assert recheck_task_count == initial_task_count
            assert recheck_project_count == initial_project_count

    def test_list_tasks_and_filtering(self, seeded_db: Path):
        """Test listing tasks and filtering by status and priority."""
        all_tasks = list_tasks(database_path=seeded_db)
        assert len(all_tasks) > 0

        pending_tasks = list_tasks(status="pending", database_path=seeded_db)
        assert all(t["status"] == "pending" for t in pending_tasks)

        high_tasks = list_tasks(priority="high", database_path=seeded_db)
        assert all(t["priority"] == "high" for t in high_tasks)

        pending_high = list_tasks(status="pending", priority="high", database_path=seeded_db)
        assert all(t["status"] == "pending" and t["priority"] == "high" for t in pending_high)

    def test_get_task_success_and_not_found(self, seeded_db: Path):
        """Test fetching a task by ID and handling nonexistent ID."""
        task = get_task(task_id=1, database_path=seeded_db)
        assert task["id"] == 1
        assert "title" in task
        assert "status" in task

        with pytest.raises(TaskNotFoundError, match="Task with ID 99999 not found"):
            get_task(task_id=99999, database_path=seeded_db)

    def test_search_tasks(self, seeded_db: Path):
        """Test searching task titles and descriptions."""
        results = search_tasks(query_text="Kubernetes", database_path=seeded_db)
        assert len(results) >= 1
        assert any("Kubernetes" in t["title"] or "Kubernetes" in t["description"] for t in results)

        no_match = search_tasks(query_text="NonExistentKeywordXYZ123", database_path=seeded_db)
        assert len(no_match) == 0

    def test_sql_injection_protection(self, seeded_db: Path):
        """Test that malicious SQL strings cannot execute arbitrary commands or leak data."""
        injection_queries = [
            "' OR '1'='1",
            "'; DROP TABLE tasks; --",
            "test%' UNION SELECT id, name, '', '', '', '', '', 1, '' FROM projects --",
        ]
        for malicious_input in injection_queries:
            results = search_tasks(query_text=malicious_input, database_path=seeded_db)
            assert isinstance(results, list)

        # Confirm tasks table still exists and data is intact
        tasks = list_tasks(database_path=seeded_db)
        assert len(tasks) > 0

    def test_list_projects(self, seeded_db: Path):
        """Test listing projects with task counts."""
        projects = list_projects(database_path=seeded_db)
        assert len(projects) >= 3
        # Check task count is present
        assert all("task_count" in p for p in projects)
        assert any(p["task_count"] > 0 for p in projects)

    def test_get_project_tasks(self, seeded_db: Path):
        """Test retrieving tasks for a project and handling nonexistent project."""
        tasks = get_project_tasks(project_id=1, database_path=seeded_db)
        assert len(tasks) > 0
        assert all(t["project_id"] == 1 for t in tasks)

        with pytest.raises(ProjectNotFoundError, match="Project with ID 99999 not found"):
            get_project_tasks(project_id=99999, database_path=seeded_db)

    def test_create_task_with_and_without_project(self, seeded_db: Path):
        """Test creating a task with and without project assignment."""
        # Unassigned task
        task1 = create_task(
            title="Write architecture document",
            description="Detail the MCP system design",
            priority="high",
            due_date="2026-11-01",
            project_id=None,
            database_path=seeded_db,
        )
        assert task1["title"] == "Write architecture document"
        assert task1["project_id"] is None
        assert task1["status"] == "pending"

        # Assigned task
        task2 = create_task(
            title="Conduct pen test",
            description="Security penetration assessment",
            priority="urgent",
            due_date="2026-12-01",
            project_id=1,
            database_path=seeded_db,
        )
        assert task2["title"] == "Conduct pen test"
        assert task2["project_id"] == 1

    def test_create_task_invalid_project_rolls_back(self, seeded_db: Path):
        """Test that referencing a nonexistent project rolls back the task insert."""
        with pytest.raises(ProjectNotFoundError):
            create_task(
                title="Orphan task",
                project_id=99999,
                database_path=seeded_db,
            )

        # Verify task was not created
        search_res = search_tasks(query_text="Orphan task", database_path=seeded_db)
        assert len(search_res) == 0

    def test_update_task_status(self, seeded_db: Path):
        """Test updating task status and handling nonexistent task."""
        updated = update_task_status(
            task_id=1,
            status="completed",
            database_path=seeded_db,
        )
        assert updated["id"] == 1
        assert updated["status"] == "completed"

        with pytest.raises(TaskNotFoundError):
            update_task_status(
                task_id=88888,
                status="completed",
                database_path=seeded_db,
            )

    def test_get_task_summary(self, seeded_db: Path):
        """Test calculation of task statistics from actual records."""
        summary = get_task_summary(database_path=seeded_db)
        assert summary["total_tasks"] > 0
        assert "by_status" in summary
        assert "by_priority" in summary
        assert "overdue_tasks" in summary

        assert sum(summary["by_status"].values()) == summary["total_tasks"]
        assert sum(summary["by_priority"].values()) == summary["total_tasks"]
        assert summary["overdue_tasks"] >= 1  # Our sample data contains overdue tasks
