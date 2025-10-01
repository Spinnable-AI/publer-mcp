"""Tests for the main MCP server."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from publer_mcp.server import server, initialize_api_client
from publer_mcp.client.auth import PublerAuth
from publer_mcp.client.api import PublerAPIClient


class TestServerInitialization:
    """Test server initialization."""
    
    @patch('os.getenv')
    def test_initialize_api_client_success(self, mock_getenv):
        """Test successful API client initialization."""
        mock_getenv.side_effect = lambda key: {
            'PUBLER_API_KEY': 'test-api-key',
            'PUBLER_WORKSPACE_ID': 'test-workspace-id'
        }.get(key)
        
        client = initialize_api_client()
        
        assert client is not None
        assert isinstance(client, PublerAPIClient)
        assert isinstance(client.auth, PublerAuth)
    
    @patch('os.getenv')
    def test_initialize_api_client_missing_credentials(self, mock_getenv):
        """Test API client initialization with missing credentials."""
        mock_getenv.return_value = None
        
        client = initialize_api_client()
        
        assert client is None
    
    @pytest.mark.asyncio
    async def test_handle_list_tools(self):
        """Test listing available tools."""
        tools = await server.list_tools()
        
        assert len(tools) > 0
        
        tool_names = [tool.name for tool in tools]
        
        # Check that key tools are present
        assert 'publer_account_list' in tool_names
        assert 'publer_post_create' in tool_names
        assert 'publer_media_list' in tool_names
        assert 'publer_analytics_post' in tool_names


class TestToolExecution:
    """Test MCP tool execution."""
    
    @pytest.mark.asyncio
    async def test_handle_call_tool_no_client(self):
        """Test tool call without initialized client."""
        # This would require mocking the global api_client
        # Implementation depends on final server structure
        pass
    
    @pytest.mark.asyncio 
    async def test_handle_call_tool_unknown(self):
        """Test calling unknown tool."""
        # Mock API client
        mock_client = AsyncMock(spec=PublerAPIClient)
        
        with patch('publer_mcp.server.api_client', mock_client):
            result = await server.call_tool('unknown_tool', {})
            
            assert len(result) == 1
            assert 'error' in result[0].text.lower()