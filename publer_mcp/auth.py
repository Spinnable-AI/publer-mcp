"""
Authentication and credential extraction for Publer MCP.
"""

from typing import NamedTuple

from mcp.server.fastmcp import Context


class PublerCredentials(NamedTuple):
    """Container for Publer API credentials."""

    api_key: str | None
    workspace_id: str | None


def extract_publer_credentials(ctx: Context) -> PublerCredentials:
    """
    Extract Publer API credentials from MCP request headers.

    Priority order for API key:
    1. Authorization header (Bearer ...)
    2. x-api-key header

    Workspace ID:
    - x-workspace-id header

    Args:
        ctx: MCP request context containing headers

    Returns:
        PublerCredentials with api_key and workspace_id (both can be None)
    """
    if not ctx.request_context or not ctx.request_context.request or not ctx.request_context.request.headers:
        return PublerCredentials(api_key=None, workspace_id=None)

    headers = ctx.request_context.request.headers

    # Extract API key with fallback priority
    api_key = None

    # Check Authorization header first (Bearer token)
    auth = headers.get("authorization")
    if auth and auth.startswith("Bearer "):
        api_key = auth[len("Bearer ") :]

    # Fallback to x-api-key header
    if not api_key:
        api_key = headers.get("x-api-key")

    # Extract workspace ID
    workspace_id = headers.get("x-workspace-id")

    return PublerCredentials(api_key=api_key, workspace_id=workspace_id)


def validate_api_key(credentials: PublerCredentials) -> tuple[bool, str | None]:
    """
    Validate that API key is present.

    Args:
        credentials: PublerCredentials to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not credentials.api_key:
        return False, "Missing API key. Please provide x-api-key header or Authorization: Bearer <key>"
    return True, None


def validate_workspace_access(credentials: PublerCredentials) -> tuple[bool, str | None]:
    """
    Validate that both API key and workspace ID are present for workspace-scoped operations.

    Args:
        credentials: PublerCredentials to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    # First check API key
    api_valid, api_error = validate_api_key(credentials)
    if not api_valid:
        return False, api_error

    # Then check workspace ID
    if not credentials.workspace_id:
        return False, "Missing workspace ID. Please provide x-workspace-id header for workspace operations."

    return True, None


def create_api_headers(credentials: PublerCredentials, include_workspace: bool = True) -> dict[str, str]:
    """
    Create headers dictionary for API client calls following Publer API requirements.

    This function creates the properly formatted headers that the thin HTTP client
    will forward to the Publer API. It handles the Publer-specific authentication
    format: "Bearer-API" instead of just "Bearer".

    Args:
        credentials: PublerCredentials containing API key and workspace ID
        include_workspace: Whether to include Publer-Workspace-Id header

    Returns:
        Dictionary of headers ready to be forwarded by the HTTP client
    """
    headers = {}

    # Create Publer-specific Authorization header: "Bearer-API" instead of "Bearer"
    if credentials.api_key:
        headers["Authorization"] = f"Bearer-API {credentials.api_key}"

    # Add workspace ID header for workspace-scoped operations
    if include_workspace and credentials.workspace_id:
        headers["Publer-Workspace-Id"] = credentials.workspace_id

    return headers
