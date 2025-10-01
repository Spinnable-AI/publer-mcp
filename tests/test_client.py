"""Tests for Publer API client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from publer_mcp.client.auth import PublerAuth
from publer_mcp.client.api import PublerAPIClient
from publer_mcp.client.models import Account, Platform, PostStatus
from publer_mcp.utils.errors import AuthenticationError, RateLimitError


class TestPublerAuth:
    """Test Publer authentication."""
    
    def test_init_success(self):
        """Test successful authentication initialization."""
        auth = PublerAuth('test-api-key', 'test-workspace-id')
        
        assert auth.api_key == 'test-api-key'
        assert auth.workspace_id == 'test-workspace-id'
    
    def test_init_empty_credentials(self):
        """Test authentication with empty credentials."""
        with pytest.raises(ValueError):
            PublerAuth('', 'workspace-id')
        
        with pytest.raises(ValueError):
            PublerAuth('api-key', '')
    
    def test_get_headers(self):
        """Test authentication header generation."""
        auth = PublerAuth('test-api-key', 'test-workspace-id')
        headers = auth.get_headers()
        
        assert headers['Authorization'] == 'Bearer-API test-api-key'
        assert headers['Publer-Workspace-Id'] == 'test-workspace-id'
        assert headers['Content-Type'] == 'application/json'
    
    def test_validate_credentials(self):
        """Test credential validation."""
        # Valid credentials
        auth = PublerAuth('test-api-key-12345', 'workspace-123')
        assert auth.validate_credentials() is True
        
        # Invalid credentials
        auth_invalid = PublerAuth('short', 'ws')
        assert auth_invalid.validate_credentials() is False


class TestPublerAPIClient:
    """Test Publer API client."""
    
    def test_init(self):
        """Test API client initialization."""
        auth = PublerAuth('test-api-key', 'test-workspace-id')
        client = PublerAPIClient(auth)
        
        assert client.auth == auth
        assert client.timeout == 30
        assert client.BASE_URL == 'https://app.publer.io/api/v1'
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager functionality."""
        auth = PublerAuth('test-api-key', 'test-workspace-id')
        
        async with PublerAPIClient(auth) as client:
            assert client._client is not None
        
        # Should be closed after context
        assert client._client is None or client._client.is_closed
    
    @pytest.mark.asyncio
    async def test_make_request_auth_error(self):
        """Test API request with authentication error."""
        auth = PublerAuth('invalid-key', 'invalid-workspace')
        client = PublerAPIClient(auth)
        
        with patch.object(client, 'client') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.headers = {}
            mock_client.request = AsyncMock(return_value=mock_response)
            
            with pytest.raises(AuthenticationError):
                await client._make_request('GET', '/accounts')
    
    @pytest.mark.asyncio
    async def test_make_request_rate_limit(self):
        """Test API request with rate limiting."""
        auth = PublerAuth('test-key', 'test-workspace')
        client = PublerAPIClient(auth)
        
        with patch.object(client, 'client') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.headers = {}
            mock_client.request = AsyncMock(return_value=mock_response)
            
            with pytest.raises(RateLimitError):
                await client._make_request('GET', '/accounts')
    
    @pytest.mark.asyncio
    async def test_list_accounts_success(self):
        """Test successful account listing."""
        auth = PublerAuth('test-key', 'test-workspace')
        client = PublerAPIClient(auth)
        
        mock_response_data = {
            'data': [{
                'id': 1,
                'platform': 'facebook',
                'username': 'test_user',
                'display_name': 'Test User',
                'profile_picture': None,
                'is_active': True,
                'created_at': '2024-01-01T00:00:00Z',
                'updated_at': '2024-01-01T00:00:00Z'
            }]
        }
        
        with patch.object(client, '_make_request') as mock_request:
            mock_request.return_value = mock_response_data
            
            accounts = await client.list_accounts()
            
            assert len(accounts) == 1
            assert isinstance(accounts[0], Account)
            assert accounts[0].id == 1
            assert accounts[0].platform == Platform.FACEBOOK
            assert accounts[0].username == 'test_user'