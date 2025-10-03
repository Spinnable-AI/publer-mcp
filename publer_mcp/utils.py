"""Utility functions and helpers for Publer MCP.

Common validation, parsing, and formatting utilities.
"""

from typing import Any, Dict


def format_error_message(error: Exception) -> str:
    """Format an exception into a user-friendly error message.

    Args:
        error: The exception to format.

    Returns:
        A clear, actionable error message.
    """
    error_type = type(error).__name__
    error_msg = str(error)
    return f"{error_type}: {error_msg}"


def validate_required_fields(data: Dict[str, Any], required_fields: list[str]) -> None:
    """Validate that all required fields are present in data.

    Args:
        data: Dictionary to validate.
        required_fields: List of required field names.

    Raises:
        ValueError: If any required field is missing.
    """
    missing = [field for field in required_fields if field not in data]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")
