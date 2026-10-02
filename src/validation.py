"""Validation utilities for MCP SQLite server inputs."""

from datetime import datetime
from typing import Optional
from config import (
    VALID_STATUSES,
    VALID_PRIORITIES,
    MAX_TITLE_LENGTH,
    MAX_DESCRIPTION_LENGTH,
    MAX_QUERY_LENGTH,
    MAX_QUERY_LIMIT,
)


class ValidationError(ValueError):
    """Raised when user input fails domain validation."""
    pass


def validate_id(identifier: int, field_name: str = "id") -> int:
    """Validate that an ID is a positive integer."""
    if not isinstance(identifier, int) or identifier <= 0:
        raise ValidationError(f"{field_name} must be a positive integer greater than 0.")
    return identifier


def validate_status(status: str) -> str:
    """Validate task status value."""
    if not isinstance(status, str):
        raise ValidationError("Status must be a string.")
    normalized = status.strip().lower()
    if normalized not in VALID_STATUSES:
        allowed = ", ".join(sorted(VALID_STATUSES))
        raise ValidationError(f"Invalid status '{status}'. Allowed statuses are: {allowed}.")
    return normalized


def validate_priority(priority: str) -> str:
    """Validate task priority value."""
    if not isinstance(priority, str):
        raise ValidationError("Priority must be a string.")
    normalized = priority.strip().lower()
    if normalized not in VALID_PRIORITIES:
        allowed = ", ".join(sorted(VALID_PRIORITIES))
        raise ValidationError(f"Invalid priority '{priority}'. Allowed priorities are: {allowed}.")
    return normalized


def validate_title(title: str) -> str:
    """Validate task title."""
    if not isinstance(title, str):
        raise ValidationError("Title must be a string.")
    cleaned = title.strip()
    if not cleaned:
        raise ValidationError("Title cannot be empty or only whitespace.")
    if len(cleaned) > MAX_TITLE_LENGTH:
        raise ValidationError(f"Title exceeds maximum length of {MAX_TITLE_LENGTH} characters.")
    return cleaned


def validate_description(description: Optional[str]) -> str:
    """Validate task description."""
    if description is None:
        return ""
    if not isinstance(description, str):
        raise ValidationError("Description must be a string.")
    cleaned = description.strip()
    if len(cleaned) > MAX_DESCRIPTION_LENGTH:
        raise ValidationError(f"Description exceeds maximum length of {MAX_DESCRIPTION_LENGTH} characters.")
    return cleaned


def validate_query(query: str) -> str:
    """Validate search query."""
    if not isinstance(query, str):
        raise ValidationError("Search query must be a string.")
    cleaned = query.strip()
    if not cleaned:
        raise ValidationError("Search query cannot be empty or only whitespace.")
    if len(cleaned) > MAX_QUERY_LENGTH:
        raise ValidationError(f"Search query exceeds maximum length of {MAX_QUERY_LENGTH} characters.")
    return cleaned


def validate_due_date(due_date: Optional[str]) -> Optional[str]:
    """Validate due date format (YYYY-MM-DD or ISO 8601)."""
    if due_date is None or (isinstance(due_date, str) and not due_date.strip()):
        return None
    cleaned = due_date.strip()

    # Try common ISO date formats
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            parsed = datetime.strptime(cleaned, fmt)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Try general fromisoformat
    try:
        parsed = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
        return parsed.strftime("%Y-%m-%d")
    except ValueError:
        pass

    raise ValidationError(
        f"Invalid due date format '{due_date}'. Expected YYYY-MM-DD or ISO 8601 format."
    )


def validate_limit(limit: Optional[int], default: int = 20) -> int:
    """Validate result limit parameter."""
    if limit is None:
        return default
    if not isinstance(limit, int) or limit < 1:
        raise ValidationError("Limit must be an integer greater than or equal to 1.")
    if limit > MAX_QUERY_LIMIT:
        raise ValidationError(f"Limit exceeds maximum allowed value of {MAX_QUERY_LIMIT}.")
    return limit
