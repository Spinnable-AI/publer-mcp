"""MCP tools for Publer account management."""

import json
import logging
from typing import Any, Dict, List

from mcp.types import Tool

from ..client.api import PublerAPIClient
from ..client.models import Platform
from ..utils.errors import validate_required_params, safe_int_conversion

logger = logging.getLogger(__name__)


def get_account_tools() -> List[Tool]:
    """Get all account management MCP tools.
    
    Returns:
        List of account management tools
    """
    return [
        Tool(
            name="publer_account_list",
            description="List all connected social media accounts in the workspace",
            inputSchema={
                "type": "object",
                "properties": {
                    "platform": {
                        "type": "string",
                        "description": "Filter by specific platform",
                        "enum": [platform.value for platform in Platform]
                    }
                },
                "additionalProperties": False
            }
        ),
        Tool(
            name="publer_account_get",
            description="Get detailed information for a specific social media account",
            inputSchema={
                "type": "object",
                "properties": {
                    "account_id": {
                        "type": "integer",
                        "description": "The ID of the account to retrieve"
                    }
                },
                "required": ["account_id"],
                "additionalProperties": False
            }
        )
    ]


async def handle_account_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    api_client: PublerAPIClient
) -> str:
    """Handle account management tool calls.
    
    Args:
        tool_name: Name of the tool to execute
        arguments: Tool arguments
        api_client: Publer API client
        
    Returns:
        JSON string with tool results
    """
    logger.info(f"Executing account tool: {tool_name}")
    
    try:
        if tool_name == "publer_account_list":
            return await _handle_list_accounts(arguments, api_client)
        elif tool_name == "publer_account_get":
            return await _handle_get_account(arguments, api_client)
        else:
            return json.dumps({
                "error": f"Unknown account tool: {tool_name}"
            })
    
    except Exception as e:
        logger.error(f"Error in account tool {tool_name}: {e}")
        raise


async def _handle_list_accounts(
    arguments: Dict[str, Any],
    api_client: PublerAPIClient
) -> str:
    """Handle publer_account_list tool call.
    
    Args:
        arguments: Tool arguments
        api_client: Publer API client
        
    Returns:
        JSON string with account list
    """
    platform = None
    if "platform" in arguments:
        try:
            platform = Platform(arguments["platform"])
        except ValueError:
            return json.dumps({
                "error": f"Invalid platform: {arguments['platform']}",
                "valid_platforms": [p.value for p in Platform]
            })
    
    accounts = await api_client.list_accounts(platform=platform)
    
    # Convert accounts to JSON-serializable format
    accounts_data = []
    for account in accounts:
        account_data = {
            "id": account.id,
            "platform": account.platform.value,
            "username": account.username,
            "display_name": account.display_name,
            "profile_picture": account.profile_picture,
            "is_active": account.is_active,
            "created_at": account.created_at.isoformat() if account.created_at else None,
            "updated_at": account.updated_at.isoformat() if account.updated_at else None
        }
        accounts_data.append(account_data)
    
    result = {
        "success": True,
        "data": {
            "accounts": accounts_data,
            "count": len(accounts_data),
            "filter": {
                "platform": platform.value if platform else None
            }
        },
        "message": f"Retrieved {len(accounts_data)} connected accounts"
    }
    
    if platform:
        result["message"] += f" for platform: {platform.value}"
    
    return json.dumps(result, indent=2)


async def _handle_get_account(
    arguments: Dict[str, Any],
    api_client: PublerAPIClient
) -> str:
    """Handle publer_account_get tool call.
    
    Args:
        arguments: Tool arguments  
        api_client: Publer API client
        
    Returns:
        JSON string with account details
    """
    validate_required_params(arguments, ["account_id"])
    
    account_id = safe_int_conversion(arguments["account_id"], "account_id")
    
    account = await api_client.get_account(account_id)
    
    # Convert account to JSON-serializable format
    account_data = {
        "id": account.id,
        "platform": account.platform.value,
        "username": account.username,
        "display_name": account.display_name,
        "profile_picture": account.profile_picture,
        "is_active": account.is_active,
        "created_at": account.created_at.isoformat() if account.created_at else None,
        "updated_at": account.updated_at.isoformat() if account.updated_at else None
    }
    
    result = {
        "success": True,
        "data": {
            "account": account_data
        },
        "message": f"Retrieved account details for {account.username} on {account.platform.value}"
    }
    
    return json.dumps(result, indent=2)