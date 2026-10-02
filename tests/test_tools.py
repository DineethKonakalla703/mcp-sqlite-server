"""Tests for MCP tools and protocol registration."""

import pytest
import json
from pathlib import Path
from scripts.seed_db import seed_db
from server import create_server
from src.database import init_db
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


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    """Fixture providing an isolated seeded database for tool tests."""
    db_file = tmp_path / "test_tool_tasks.db"
    init_db(db_file)
    seed_db(db_file)
    return db_file


@pytest.fixture
def mcp_server(temp_db: Path):
    """Fixture providing an MCP server instance wired to the temporary database."""
    return create_server(database_path=temp_db)


class TestDirectTools:
    """Test suite for direct tool functions."""

    def test_list_tasks_tool_filtering(self, temp_db: Path):
        res = list_tasks_tool(status="in_progress", db_path=temp_db)
        assert res["count"] > 0
        assert all(t["status"] == "in_progress" for t in res["tasks"])

    def test_list_tasks_tool_invalid_status(self, temp_db: Path):
        with pytest.raises(ValidationError):
            list_tasks_tool(status="bogus_status", db_path=temp_db)

    def test_get_task_tool_valid(self, temp_db: Path):
        res = get_task_tool(task_id=1, db_path=temp_db)
        assert res["task"]["id"] == 1

    def test_get_task_tool_invalid_id(self, temp_db: Path):
        with pytest.raises(ValidationError):
            get_task_tool(task_id=-1, db_path=temp_db)

    def test_search_tasks_tool(self, temp_db: Path):
        res = search_tasks_tool(query="Kubernetes", db_path=temp_db)
        assert res["count"] >= 1
        assert res["query"] == "Kubernetes"

    def test_search_tasks_tool_empty_query(self, temp_db: Path):
        with pytest.raises(ValidationError):
            search_tasks_tool(query="", db_path=temp_db)

    def test_list_projects_tool(self, temp_db: Path):
        res = list_projects_tool(db_path=temp_db)
        assert res["count"] >= 3
        assert len(res["projects"]) == res["count"]

    def test_get_project_tasks_tool(self, temp_db: Path):
        res = get_project_tasks_tool(project_id=1, db_path=temp_db)
        assert res["project_id"] == 1
        assert res["count"] > 0

    def test_create_task_tool(self, temp_db: Path):
        res = create_task_tool(
            title="Configure CI/CD runner",
            description="Set up GitHub Actions self-hosted runner",
            priority="high",
            due_date="2026-11-15",
            project_id=1,
            db_path=temp_db,
        )
        assert res["task"]["title"] == "Configure CI/CD runner"
        assert res["task"]["priority"] == "high"
        assert res["task"]["project_id"] == 1

    def test_create_task_tool_invalid_priority(self, temp_db: Path):
        with pytest.raises(ValidationError):
            create_task_tool(title="Valid title", priority="critical", db_path=temp_db)

    def test_update_task_status_tool(self, temp_db: Path):
        res = update_task_status_tool(task_id=2, status="completed", db_path=temp_db)
        assert res["task"]["id"] == 2
        assert res["task"]["status"] == "completed"

    def test_get_task_summary_tool(self, temp_db: Path):
        res = get_task_summary_tool(db_path=temp_db)
        summary = res["summary"]
        assert summary["total_tasks"] > 0
        assert "pending" in summary["by_status"]
        assert "urgent" in summary["by_priority"]


class TestMCPProtocolIntegration:
    """Test suite for MCP server protocol-level registration and execution."""

    @pytest.mark.asyncio
    async def test_tool_discovery(self, mcp_server):
        """Verify all 8 tools are registered and discovered via MCP protocol."""
        tools = await mcp_server.list_tools()
        tool_names = {t.name for t in tools}
        expected_tools = {
            "list_tasks",
            "get_task",
            "search_tasks",
            "list_projects",
            "get_project_tasks",
            "create_task",
            "update_task_status",
            "get_task_summary",
        }
        assert expected_tools.issubset(tool_names)
        assert len(tools) == 8

        # Verify descriptions and parameter schemas exist
        for t in tools:
            assert t.description is not None
            assert len(t.description) > 10

    @pytest.mark.asyncio
    async def test_protocol_call_list_tasks(self, mcp_server):
        """Invoke list_tasks through MCP call_tool interface."""
        result = await mcp_server.call_tool("list_tasks", {"status": "pending"})
        assert not result.is_error
        data = json.loads(result.content[0].text)
        assert "tasks" in data
        assert all(t["status"] == "pending" for t in data["tasks"])

    @pytest.mark.asyncio
    async def test_protocol_call_get_task(self, mcp_server):
        """Invoke get_task through MCP call_tool interface."""
        result = await mcp_server.call_tool("get_task", {"task_id": 1})
        assert not result.is_error
        data = json.loads(result.content[0].text)
        assert "task" in data
        assert data["task"]["id"] == 1

    @pytest.mark.asyncio
    async def test_protocol_call_get_task_not_found(self, mcp_server):
        """Invoke get_task with nonexistent ID and verify graceful error response."""
        result = await mcp_server.call_tool("get_task", {"task_id": 99999})
        assert not result.is_error
        data = json.loads(result.content[0].text)
        assert data["success"] is False
        assert "not found" in data["error"].lower()

    @pytest.mark.asyncio
    async def test_protocol_call_search_tasks(self, mcp_server):
        """Invoke search_tasks through MCP call_tool interface."""
        result = await mcp_server.call_tool("search_tasks", {"query": "Kubernetes"})
        assert not result.is_error
        data = json.loads(result.content[0].text)
        assert "tasks" in data
        assert len(data["tasks"]) >= 1

    @pytest.mark.asyncio
    async def test_protocol_call_create_task(self, mcp_server):
        """Invoke create_task through MCP call_tool interface."""
        result = await mcp_server.call_tool(
            "create_task",
            {
                "title": "Protocol Created Task",
                "description": "Created via MCP JSON-RPC",
                "priority": "urgent",
                "due_date": "2026-11-30",
            },
        )
        assert not result.is_error
        data = json.loads(result.content[0].text)
        assert "task" in data
        assert data["task"]["title"] == "Protocol Created Task"
        assert data["task"]["priority"] == "urgent"

    @pytest.mark.asyncio
    async def test_protocol_call_create_task_invalid_input(self, mcp_server):
        """Invoke create_task with invalid priority and verify error."""
        result = await mcp_server.call_tool(
            "create_task",
            {
                "title": "Bad Task",
                "priority": "super-critical",
            },
        )
        assert not result.is_error
        data = json.loads(result.content[0].text)
        assert data["success"] is False
        assert "invalid priority" in data["error"].lower()

    @pytest.mark.asyncio
    async def test_protocol_call_update_task_status(self, mcp_server):
        """Invoke update_task_status through MCP call_tool interface."""
        result = await mcp_server.call_tool(
            "update_task_status",
            {"task_id": 1, "status": "in_progress"},
        )
        assert not result.is_error
        data = json.loads(result.content[0].text)
        assert data["task"]["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_protocol_call_summary(self, mcp_server):
        """Invoke get_task_summary through MCP call_tool interface."""
        result = await mcp_server.call_tool("get_task_summary", {})
        assert not result.is_error
        data = json.loads(result.content[0].text)
        assert "summary" in data
        assert data["summary"]["total_tasks"] > 0
