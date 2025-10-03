"""
Tests for workspace_id parameter migration from header to parameter.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from publer_mcp.auth import (
    PublerCredentials,
    create_api_headers,
    extract_publer_credentials,
    validate_api_key,
    validate_workspace_id,
)


class TestPublerCredentials:
    """Test PublerCredentials NamedTuple structure."""

    def test_credentials_only_has_api_key(self):
        """Verify PublerCredentials only contains api_key field."""
        creds = PublerCredentials(api_key="test_key")
        
        assert hasattr(creds, "api_key")
        assert creds.api_key == "test_key"
        
        # Verify workspace_id field no longer exists
        assert not hasattr(creds, "workspace_id")

    def test_credentials_with_none(self):
        """Test credentials with None API key."""
        creds = PublerCredentials(api_key=None)
        
        assert creds.api_key is None


class TestExtractPublerCredentials:
    """Test extract_publer_credentials function."""

    def test_extract_from_authorization_header(self):
        """Test API key extraction from Authorization Bearer header."""
        mock_ctx = MagicMock()
        mock_ctx.request_context.request.headers = {
            "authorization": "Bearer test_api_key_123"
        }
        
        credentials = extract_publer_credentials(mock_ctx)
        
        assert credentials.api_key == "test_api_key_123"
        assert not hasattr(credentials, "workspace_id")

    def test_extract_from_x_api_key_header(self):
        """Test API key extraction from x-api-key header."""
        mock_ctx = MagicMock()
        mock_ctx.request_context.request.headers = {
            "x-api-key": "test_api_key_456"
        }
        
        credentials = extract_publer_credentials(mock_ctx)
        
        assert credentials.api_key == "test_api_key_456"

    def test_no_workspace_id_extraction(self):
        """Verify workspace_id is NOT extracted from headers anymore."""
        mock_ctx = MagicMock()
        mock_ctx.request_context.request.headers = {
            "authorization": "Bearer test_key",
            "x-workspace-id": "workspace_123"  # This should be ignored
        }
        
        credentials = extract_publer_credentials(mock_ctx)
        
        assert credentials.api_key == "test_key"
        # Verify workspace_id is not in credentials
        assert not hasattr(credentials, "workspace_id")

    def test_no_headers(self):
        """Test extraction when no headers are present."""
        mock_ctx = MagicMock()
        mock_ctx.request_context = None
        
        credentials = extract_publer_credentials(mock_ctx)
        
        assert credentials.api_key is None


class TestValidateWorkspaceId:
    """Test validate_workspace_id function."""

    def test_valid_workspace_id(self):
        """Test validation with valid workspace_id."""
        is_valid, error = validate_workspace_id("workspace_123")
        
        assert is_valid is True
        assert error is None

    def test_none_workspace_id(self):
        """Test validation with None workspace_id."""
        is_valid, error = validate_workspace_id(None)
        
        assert is_valid is False
        assert "Missing workspace_id parameter" in error

    def test_empty_workspace_id(self):
        """Test validation with empty string workspace_id."""
        is_valid, error = validate_workspace_id("")
        
        assert is_valid is False
        assert "Invalid workspace_id parameter" in error

    def test_whitespace_only_workspace_id(self):
        """Test validation with whitespace-only workspace_id."""
        is_valid, error = validate_workspace_id("   ")
        
        assert is_valid is False
        assert "Invalid workspace_id parameter" in error

    def test_non_string_workspace_id(self):
        """Test validation with non-string workspace_id."""
        is_valid, error = validate_workspace_id(123)  # Integer instead of string
        
        assert is_valid is False
        assert "Invalid workspace_id parameter" in error


class TestCreateApiHeaders:
    """Test create_api_headers function."""

    def test_headers_with_api_key_only(self):
        """Test header creation with only API key (no workspace_id)."""
        credentials = PublerCredentials(api_key="test_key")
        
        headers = create_api_headers(credentials)
        
        assert headers["Authorization"] == "Bearer-API test_key"
        assert "Publer-Workspace-Id" not in headers

    def test_headers_with_api_key_and_workspace_id(self):
        """Test header creation with both API key and workspace_id parameter."""
        credentials = PublerCredentials(api_key="test_key")
        
        headers = create_api_headers(credentials, workspace_id="workspace_123")
        
        assert headers["Authorization"] == "Bearer-API test_key"
        assert headers["Publer-Workspace-Id"] == "workspace_123"

    def test_headers_with_none_workspace_id(self):
        """Test that None workspace_id doesn't add header."""
        credentials = PublerCredentials(api_key="test_key")
        
        headers = create_api_headers(credentials, workspace_id=None)
        
        assert headers["Authorization"] == "Bearer-API test_key"
        assert "Publer-Workspace-Id" not in headers

    def test_headers_with_no_api_key(self):
        """Test header creation when API key is None."""
        credentials = PublerCredentials(api_key=None)
        
        headers = create_api_headers(credentials, workspace_id="workspace_123")
        
        assert "Authorization" not in headers
        assert headers["Publer-Workspace-Id"] == "workspace_123"


class TestValidateApiKey:
    """Test validate_api_key function."""

    def test_valid_api_key(self):
        """Test validation with valid API key."""
        credentials = PublerCredentials(api_key="test_key")
        
        is_valid, error = validate_api_key(credentials)
        
        assert is_valid is True
        assert error is None

    def test_none_api_key(self):
        """Test validation with None API key."""
        credentials = PublerCredentials(api_key=None)
        
        is_valid, error = validate_api_key(credentials)
        
        assert is_valid is False
        assert "Missing API key" in error


class TestBackwardsCompatibility:
    """Test that old validate_workspace_access function no longer exists."""

    def test_validate_workspace_access_removed(self):
        """Verify validate_workspace_access function has been removed."""
        from publer_mcp import auth
        
        assert not hasattr(auth, "validate_workspace_access")

    def test_include_workspace_parameter_removed(self):
        """Verify create_api_headers no longer accepts include_workspace parameter."""
        credentials = PublerCredentials(api_key="test_key")
        
        # This should raise TypeError since include_workspace parameter is removed
        with pytest.raises(TypeError):
            create_api_headers(credentials, include_workspace=True)


# Integration-style tests
class TestHeaderFlowIntegration:
    """Integration tests for complete header flow."""

    def test_user_scoped_endpoint_flow(self):
        """Simulate flow for user-scoped endpoint (no workspace_id needed)."""
        # 1. Extract credentials
        mock_ctx = MagicMock()
        mock_ctx.request_context.request.headers = {
            "authorization": "Bearer user_api_key"
        }
        credentials = extract_publer_credentials(mock_ctx)
        
        # 2. Validate API key only
        api_valid, api_error = validate_api_key(credentials)
        assert api_valid is True
        
        # 3. Create headers without workspace_id
        headers = create_api_headers(credentials)
        
        assert headers == {"Authorization": "Bearer-API user_api_key"}

    def test_workspace_scoped_endpoint_flow(self):
        """Simulate flow for workspace-scoped endpoint (workspace_id required)."""
        # 1. Extract credentials
        mock_ctx = MagicMock()
        mock_ctx.request_context.request.headers = {
            "x-api-key": "workspace_api_key"
        }
        credentials = extract_publer_credentials(mock_ctx)
        
        # 2. Validate API key
        api_valid, api_error = validate_api_key(credentials)
        assert api_valid is True
        
        # 3. Validate workspace_id parameter (passed by tool)
        workspace_id = "ws_123"
        workspace_valid, workspace_error = validate_workspace_id(workspace_id)
        assert workspace_valid is True
        
        # 4. Create headers with workspace_id parameter
        headers = create_api_headers(credentials, workspace_id=workspace_id)
        
        assert headers == {
            "Authorization": "Bearer-API workspace_api_key",
            "Publer-Workspace-Id": "ws_123"
        }

    def test_missing_workspace_id_for_workspace_endpoint(self):
        """Simulate failure when workspace_id is missing for workspace-scoped endpoint."""
        # 1. Extract credentials
        mock_ctx = MagicMock()
        mock_ctx.request_context.request.headers = {
            "authorization": "Bearer api_key"
        }
        credentials = extract_publer_credentials(mock_ctx)
        
        # 2. Validate API key
        api_valid, _ = validate_api_key(credentials)
        assert api_valid is True
        
        # 3. Try to validate None workspace_id (tool didn't provide it)
        workspace_valid, workspace_error = validate_workspace_id(None)
        
        assert workspace_valid is False
        assert "Missing workspace_id parameter" in workspace_error