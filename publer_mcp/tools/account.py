"""
Account and workspace management tools for Publer MCP.
"""

from typing import Any, Dict, List
from mcp.server.fastmcp import Context

from ..auth import extract_publer_credentials, validate_api_key, validate_workspace_access, create_api_headers
from ..client import create_client, PublerAPIError


async def publer_check_account_status(ctx: Context) -> Dict[str, Any]:
    """
    Check your Publer account status and available workspaces to verify 
    your integration is working correctly.
    
    This tool validates your authentication and provides an overview of your 
    Publer account information and available workspaces. It focuses on account
    status rather than workspace validation.
    
    Returns:
        Dict containing account info, available workspaces, and integration status
    """
    try:
        credentials = extract_publer_credentials(ctx)
        
        # Only validate API key (workspace_id is optional for account status)
        api_valid, api_error = validate_api_key(credentials)
        if not api_valid:
            return {
                "status": "authentication_failed",
                "error": api_error,
                "integration_status": {
                    "authentication": "failed",
                    "api_connectivity": "failed"
                }
            }
        
        client = create_client()
        
        # Get user information (only needs API key)
        user_headers = create_api_headers(credentials, include_workspace=False)
        user_info = await client.get("users/me", user_headers)
        
        # Get available workspaces (only needs API key)
        workspaces_response = await client.get("workspaces", user_headers)
        workspaces = workspaces_response.get('data', [])
        
        await client.close()
        
        return {
            "status": "connected",
            "account": {
                "user_id": user_info.get("id"),
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "account_type": user_info.get("account_type", "unknown")
            },
            "workspaces": {
                "available_workspaces": len(workspaces),
                "workspace_list": [
                    {
                        "id": ws.get("id"),
                        "name": ws.get("name"),
                        "role": ws.get("role", "unknown")
                    }
                    for ws in workspaces
                ],
                "provided_workspace_id": credentials.workspace_id  # Optional info
            },
            "integration_status": {
                "authentication": "success",
                "api_connectivity": "operational"
            }
        }
        
    except PublerAPIError as e:
        if "Invalid API key" in str(e) or "401" in str(e):
            return {
                "status": "authentication_failed",
                "error": "Invalid API key. Please check your Publer API credentials.",
                "integration_status": {
                    "authentication": "failed",
                    "api_connectivity": "failed"
                }
            }
        elif "Permission denied" in str(e) or "403" in str(e):
            return {
                "status": "permission_denied", 
                "error": "Permission denied. Your API key may lack required scopes.",
                "integration_status": {
                    "authentication": "success",
                    "api_connectivity": "limited"
                }
            }
        elif "Rate limit" in str(e):
            return {
                "status": "rate_limited",
                "error": "Rate limit exceeded. Please wait before trying again.",
                "integration_status": {
                    "authentication": "unknown",
                    "api_connectivity": "throttled"
                }
            }
        else:
            return {
                "status": "api_error",
                "error": f"Publer API error: {str(e)}",
                "integration_status": {
                    "authentication": "unknown",
                    "api_connectivity": "error"
                }
            }
    
    except Exception as e:
        return {
            "status": "connection_error",
            "error": f"Connection error: {str(e)}",
            "integration_status": {
                "authentication": "unknown",
                "api_connectivity": "failed"
            }
        }


async def publer_list_connected_platforms(ctx: Context) -> Dict[str, Any]:
    """
    List all your connected social media platforms with their posting 
    capabilities and current status.
    
    This tool shows which social media accounts are connected to your workspace
    and available for content publishing, along with their current status and
    supported content types.
    
    Returns:
        Dict containing connected platforms, their capabilities, and status
    """
    try:
        # Extract credentials using centralized auth logic
        credentials = extract_publer_credentials(ctx)
        
        # Validate both API key AND workspace ID (required for accounts endpoint)
        workspace_valid, workspace_error = validate_workspace_access(credentials)
        if not workspace_valid:
            return {
                "status": "authentication_failed" if "API key" in workspace_error else "workspace_required",
                "error": workspace_error,
                "platforms": []
            }
        
        client = create_client()
        
        # Get accounts (requires both API key and workspace-id)
        accounts_headers = create_api_headers(credentials, include_workspace=True)
        accounts_response = await client.get("accounts", accounts_headers)
        accounts = accounts_response.get('data', [])
        
        await client.close()
        
        if not accounts:
            return {
                "status": "no_platforms_connected",
                "message": "No social media platforms are currently connected to your workspace.",
                "platforms": [],
                "summary": {
                    "total_platforms": 0,
                    "active_platforms": 0,
                    "platforms_by_type": {}
                }
            }
        
        # Process accounts into organized platform information
        platforms = []
        platforms_by_type = {}
        active_count = 0
        
        for account in accounts:
            platform_type = account.get('type', 'unknown')
            account_name = account.get('name', 'Unnamed Account')
            account_id = account.get('id')
            status = account.get('status', 'unknown')
            
            # Determine posting capabilities based on platform type
            posting_capabilities = _get_platform_capabilities(platform_type)
            
            platform_info = {
                "account_id": account_id,
                "platform": platform_type,
                "account_name": account_name,
                "status": status,
                "is_active": status == 'active',
                "posting_capabilities": posting_capabilities,
                "profile_info": {
                    "username": account.get('username'),
                    "profile_picture": account.get('profile_picture'),
                    "follower_count": account.get('follower_count')
                }
            }
            
            platforms.append(platform_info)
            
            # Update summary counters
            if status == 'active':
                active_count += 1
            
            platforms_by_type[platform_type] = platforms_by_type.get(platform_type, 0) + 1
        
        return {
            "status": "success",
            "platforms": platforms,
            "summary": {
                "total_platforms": len(accounts),
                "active_platforms": active_count,
                "inactive_platforms": len(accounts) - active_count,
                "platforms_by_type": platforms_by_type,
                "supported_content_types": _get_all_supported_content_types(platforms)
            }
        }
        
    except PublerAPIError as e:
        if "Invalid API key" in str(e) or "401" in str(e):
            return {
                "status": "authentication_failed",
                "error": "Invalid API key. Please check your Publer API credentials.",
                "platforms": []
            }
        elif "Permission denied" in str(e) or "403" in str(e):
            return {
                "status": "permission_denied",
                "error": "Permission denied. Your API key may lack workspace access or required scopes.",
                "platforms": []
            }
        else:
            return {
                "status": "api_error", 
                "error": f"Publer API error: {str(e)}",
                "platforms": []
            }
    
    except Exception as e:
        return {
            "status": "connection_error",
            "error": f"Connection error: {str(e)}",
            "platforms": []
        }


def _get_platform_capabilities(platform_type: str) -> List[str]:
    """Get posting capabilities for a specific platform type."""
    capabilities_map = {
        'facebook': ['text', 'image', 'video', 'link', 'carousel'],
        'instagram': ['image', 'video', 'carousel', 'story'],
        'twitter': ['text', 'image', 'video', 'thread'],
        'linkedin': ['text', 'image', 'video', 'article', 'document'],
        'pinterest': ['image', 'video'],
        'youtube': ['video', 'shorts'],
        'tiktok': ['video']
    }
    
    return capabilities_map.get(platform_type.lower(), ['text', 'image'])


def _get_all_supported_content_types(platforms: List[Dict[str, Any]]) -> List[str]:
    """Get all unique content types supported across all active platforms."""
    all_types = set()
    
    for platform in platforms:
        if platform.get('is_active'):
            capabilities = platform.get('posting_capabilities', [])
            all_types.update(capabilities)
    
    return sorted(list(all_types))