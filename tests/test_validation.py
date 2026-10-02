"""Unit tests for input validation layer."""

import pytest
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


class TestValidation:
    """Test suite for input validation functions."""

    def test_validate_id_valid(self):
        assert validate_id(1) == 1
        assert validate_id(999) == 999

    def test_validate_id_invalid(self):
        with pytest.raises(ValidationError, match="must be a positive integer"):
            validate_id(0)
        with pytest.raises(ValidationError, match="must be a positive integer"):
            validate_id(-5)
        with pytest.raises(ValidationError, match="must be a positive integer"):
            validate_id("1")  # type: ignore

    def test_validate_status_valid(self):
        assert validate_status("pending") == "pending"
        assert validate_status("IN_PROGRESS") == "in_progress"
        assert validate_status(" completed ") == "completed"

    def test_validate_status_invalid(self):
        with pytest.raises(ValidationError, match="Invalid status 'unknown'"):
            validate_status("unknown")
        with pytest.raises(ValidationError, match="Status must be a string"):
            validate_status(123)  # type: ignore

    def test_validate_priority_valid(self):
        assert validate_priority("low") == "low"
        assert validate_priority("MEDIUM") == "medium"
        assert validate_priority("high") == "high"
        assert validate_priority("urgent") == "urgent"

    def test_validate_priority_invalid(self):
        with pytest.raises(ValidationError, match="Invalid priority 'critical'"):
            validate_priority("critical")
        with pytest.raises(ValidationError, match="Priority must be a string"):
            validate_priority(None)  # type: ignore

    def test_validate_title_valid(self):
        assert validate_title("Valid Title") == "Valid Title"
        assert validate_title("   Trimmed Title   ") == "Trimmed Title"

    def test_validate_title_empty_or_whitespace(self):
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_title("")
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_title("    ")

    def test_validate_title_max_length(self):
        long_title = "a" * 201
        with pytest.raises(ValidationError, match="exceeds maximum length"):
            validate_title(long_title)

    def test_validate_description_valid(self):
        assert validate_description("Some desc") == "Some desc"
        assert validate_description(None) == ""
        assert validate_description("   ") == ""

    def test_validate_description_max_length(self):
        long_desc = "x" * 2001
        with pytest.raises(ValidationError, match="exceeds maximum length"):
            validate_description(long_desc)

    def test_validate_query_valid(self):
        assert validate_query("kubernetes") == "kubernetes"
        assert validate_query("  database migration  ") == "database migration"

    def test_validate_query_invalid(self):
        with pytest.raises(ValidationError, match="Search query cannot be empty"):
            validate_query("")
        with pytest.raises(ValidationError, match="Search query cannot be empty"):
            validate_query("   ")
        with pytest.raises(ValidationError, match="exceeds maximum length"):
            validate_query("a" * 101)

    def test_validate_due_date_valid(self):
        assert validate_due_date("2026-12-31") == "2026-12-31"
        assert validate_due_date("2026-12-31 15:30:00") == "2026-12-31"
        assert validate_due_date("2026-12-31T15:30:00Z") == "2026-12-31"
        assert validate_due_date(None) is None
        assert validate_due_date("") is None

    def test_validate_due_date_invalid(self):
        with pytest.raises(ValidationError, match="Invalid due date format"):
            validate_due_date("not-a-date")
        with pytest.raises(ValidationError, match="Invalid due date format"):
            validate_due_date("31/12/2026")

    def test_validate_limit_valid(self):
        assert validate_limit(None, default=20) == 20
        assert validate_limit(10) == 10
        assert validate_limit(100) == 100

    def test_validate_limit_invalid(self):
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            validate_limit(0)
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            validate_limit(-10)
        with pytest.raises(ValidationError, match="exceeds maximum allowed value"):
            validate_limit(101)
