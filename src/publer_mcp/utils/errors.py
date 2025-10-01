"""Error handling utilities for Publer MCP server."""

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class PublerMCPError(Exception):
    """Base exception for Publer MCP operations."""
    
    def __init__(self, message: str, code: str = "UNKNOWN_ERROR", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class AuthenticationError(PublerMCPError):
    """Authentication or authorization failures."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "AUTHENTICATION_FAILED", details)


class RateLimitError(PublerMCPError):
    """API rate limiting issues."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "RATE_LIMIT_EXCEEDED", details)


class NetworkError(PublerMCPError):
    """Network or connectivity issues."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "NETWORK_ERROR", details)


class ValidationError(PublerMCPError):
    """Input validation failures."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "VALIDATION_ERROR", details)


def format_error_response(
    error: Exception,
    tool_name: str,
    arguments: Optional[Dict[str, Any]] = None
) -> str:
    """Format error response for MCP tool calls.
    
    Args:
        error: The exception that occurred
        tool_name: Name of the tool that failed
        arguments: Tool arguments that caused the error
        
    Returns:
        Formatted error response as JSON string
    """
    if isinstance(error, PublerMCPError):
        error_data = {
            "error": {
                "code": error.code,
                "message": error.message,
                "details": error.details,
                "tool": tool_name,
                "arguments": arguments
            }
        }
        
        # Add specific resolution hints based on error type
        if isinstance(error, AuthenticationError):
            error_data["error"]["resolution"] = (
                "Please check your PUBLER_API_KEY and PUBLER_WORKSPACE_ID environment variables. "
                "Ensure your API key is valid and you have access to the specified workspace."
            )
        elif isinstance(error, RateLimitError):
            error_data["error"]["resolution"] = (
                "API rate limit exceeded. Please wait a moment before trying again. "
                "Consider reducing the frequency of your requests."
            )
        elif isinstance(error, NetworkError):
            error_data["error"]["resolution"] = (
                "Network connection issue. Please check your internet connection and try again. "
                "If the problem persists, Publer's API may be temporarily unavailable."
            )
        elif isinstance(error, ValidationError):
            error_data["error"]["resolution"] = (
                "Input validation failed. Please check your parameters and ensure they match "
                "the expected format and requirements."
            )
        else:
            error_data["error"]["resolution"] = (
                "An unexpected error occurred. Please check the error details and try again."
            )
    else:
        # Handle unexpected errors
        error_data = {
            "error": {
                "code": "UNEXPECTED_ERROR",
                "message": str(error),
                "details": {
                    "error_type": type(error).__name__
                },
                "tool": tool_name,
                "arguments": arguments,
                "resolution": (
                    "An unexpected error occurred. This might be a bug in the Publer MCP server. "
                    "Please report this issue with the error details."
                )
            }
        }
    
    # Log the error for debugging
    logger.error(
        f"Tool {tool_name} failed: {error_data['error']['message']}",
        extra={
            "tool_name": tool_name,
            "error_code": error_data["error"]["code"],
            "arguments": arguments,
            "error_details": error_data["error"]["details"]
        }
    )
    
    return json.dumps(error_data, indent=2)


def validate_required_params(params: Dict[str, Any], required: list[str]) -> None:
    """Validate that required parameters are present.
    
    Args:
        params: Parameter dictionary
        required: List of required parameter names
        
    Raises:
        ValidationError: If required parameters are missing
    """
    missing = [param for param in required if param not in params or params[param] is None]
    if missing:
        raise ValidationError(
            f"Missing required parameters: {', '.join(missing)}",
            details={"missing_parameters": missing, "provided_parameters": list(params.keys())}
        )


def validate_param_types(params: Dict[str, Any], type_specs: Dict[str, type]) -> None:
    """Validate parameter types.
    
    Args:
        params: Parameter dictionary
        type_specs: Dictionary mapping parameter names to expected types
        
    Raises:
        ValidationError: If parameter types don't match expectations
    """
    type_errors = []
    for param_name, expected_type in type_specs.items():
        if param_name in params and params[param_name] is not None:
            param_value = params[param_name]
            if not isinstance(param_value, expected_type):
                type_errors.append({
                    "parameter": param_name,
                    "expected_type": expected_type.__name__,
                    "actual_type": type(param_value).__name__,
                    "value": param_value
                })
    
    if type_errors:
        raise ValidationError(
            "Parameter type validation failed",
            details={"type_errors": type_errors}
        )


def safe_int_conversion(value: Any, param_name: str) -> int:
    """Safely convert value to integer.
    
    Args:
        value: Value to convert
        param_name: Parameter name for error reporting
        
    Returns:
        Integer value
        
    Raises:
        ValidationError: If conversion fails
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        raise ValidationError(
            f"Parameter '{param_name}' must be a valid integer",
            details={"parameter": param_name, "value": value, "type": type(value).__name__}
        )


def safe_datetime_parsing(value: str, param_name: str) -> Any:
    """Safely parse datetime string.
    
    Args:
        value: Datetime string to parse
        param_name: Parameter name for error reporting
        
    Returns:
        Parsed datetime object
        
    Raises:
        ValidationError: If parsing fails
    """
    from datetime import datetime
    
    try:
        # Try ISO format first
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        try:
            # Try common formats
            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y-%m-%dT%H:%M:%S']:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
        except ValueError:
            pass
        
        raise ValidationError(
            f"Parameter '{param_name}' must be a valid datetime string",
            details={
                "parameter": param_name,
                "value": value,
                "supported_formats": [
                    "ISO 8601 (2024-01-01T12:00:00)",
                    "YYYY-MM-DD HH:MM:SS",
                    "YYYY-MM-DD"
                ]
            }
        )