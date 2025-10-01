"""Tests for MCP tools."""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock

from publer_mcp.tools.accounts import get_account_tools, handle_account_tool
from publer_mcp.tools.posts import get_post_tools, handle_post_tool
from publer_mcp.client.api import PublerAPIClient
from publer_mcp.client.models import Account, Platform, Post, PostStatus, PostContent
from publer_mcp.utils.errors import ValidationError


class TestAccountTools:
    """Test account management tools."""
    
    def test_get_account_tools(self):
        """Test account tools registration."""
        tools = get_account_tools()
        
        assert len(tools) == 2
        tool_names = [tool.name for tool in tools]
        assert 'publer_account_list' in tool_names
        assert 'publer_account_get' in tool_names
    
    @pytest.mark.asyncio
    async def test_handle_account_list(self):
        """Test account list tool execution."""
        # Mock API client
        mock_client = AsyncMock(spec=PublerAPIClient)
        mock_account = Account(
            id=1,
            platform=Platform.FACEBOOK,
            username='test_user',
            display_name='Test User',
            is_active=True
        )
        mock_client.list_accounts.return_value = [mock_account]
        
        # Execute tool
        result = await handle_account_tool(
            'publer_account_list',
            {},
            mock_client
        )
        
        # Parse and verify result
        result_data = json.loads(result)
        assert result_data['success'] is True
        assert len(result_data['data']['accounts']) == 1
        assert result_data['data']['accounts'][0]['id'] == 1
        assert result_data['data']['accounts'][0]['platform'] == 'facebook'
    
    @pytest.mark.asyncio
    async def test_handle_account_get_missing_id(self):
        """Test account get tool with missing ID."""
        mock_client = AsyncMock(spec=PublerAPIClient)
        
        with pytest.raises(ValidationError):
            await handle_account_tool(
                'publer_account_get',
                {},  # Missing account_id
                mock_client
            )


class TestPostTools:
    """Test post management tools."""
    
    def test_get_post_tools(self):
        """Test post tools registration."""
        tools = get_post_tools()
        
        assert len(tools) == 4
        tool_names = [tool.name for tool in tools]
        assert 'publer_post_create' in tool_names
        assert 'publer_post_list' in tool_names
        assert 'publer_post_get' in tool_names
        assert 'publer_post_delete' in tool_names
    
    @pytest.mark.asyncio
    async def test_handle_post_create(self):
        """Test post creation tool execution."""
        # Mock API client
        mock_client = AsyncMock(spec=PublerAPIClient)
        mock_post = Post(
            id=123,
            status=PostStatus.DRAFT,
            content=PostContent(text='Test post', media=[], link=None),
            platforms=[Platform.FACEBOOK],
            accounts=[1],
            created_at='2024-01-01T00:00:00Z',
            updated_at='2024-01-01T00:00:00Z'
        )
        mock_client.create_post.return_value = mock_post
        
        # Execute tool
        result = await handle_post_tool(
            'publer_post_create',
            {
                'content': 'Test post content',
                'account_ids': [1, 2]
            },
            mock_client
        )
        
        # Parse and verify result
        result_data = json.loads(result)
        assert result_data['success'] is True
        assert result_data['data']['post_id'] == 123
        assert result_data['data']['status'] == 'draft'
    
    @pytest.mark.asyncio
    async def test_handle_post_create_missing_params(self):
        """Test post creation with missing parameters."""
        mock_client = AsyncMock(spec=PublerAPIClient)
        
        with pytest.raises(ValidationError):
            await handle_post_tool(
                'publer_post_create',
                {'content': 'Test post'},  # Missing account_ids
                mock_client
            )
    
    @pytest.mark.asyncio
    async def test_handle_unknown_tool(self):
        """Test handling unknown tool."""
        mock_client = AsyncMock(spec=PublerAPIClient)
        
        result = await handle_post_tool(
            'unknown_tool',
            {},
            mock_client
        )
        
        result_data = json.loads(result)
        assert 'error' in result_data