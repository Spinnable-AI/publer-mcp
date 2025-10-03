"""
Account and workspace management tools for Publer MCP.
"""

from typing import Any, Dict, List
from mcp.server.fastmcp import Context

from ..client import create_client, PublerAPIError


def extract_publer_credentials(ctx: Context) -> tuple[str | None, str | None]:
    """
    Extract Publer API credentials from MCP request headers.
    
    Returns:
        Tuple of (api_key, workspace_id) or (None, None) if missing
    """
    if not ctx.request_context or not ctx.request_context.request or not ctx.request_context.request.headers:
        return None, None
    
    headers = ctx.request_context.request.headers
    
    # Extract API key
    api_key = headers.get('x-api-key')
    if not api_key:
        auth = headers.get('authorization', '')
        if auth.startswith('Bearer '):
            api_key = auth[len('Bearer '):]
    
    # Extract workspace ID
    workspace_id = headers.get('x-workspace-id')
    
    return api_key, workspace_id


async def publer_check_account_status(ctx: Context) -> Dict[str, Any]:
    """
    Check your Publer account status, workspace access, and subscription limits 
    to verify your integration is working correctly.
    
    This tool validates your authentication and provides an overview of your 
    Publer account capabilities, workspace access, and current status.
    
    Returns:
        Dict containing account info, workspace details, and subscription status
    """
    try:
        # Extract credentials from request context
        api_key, workspace_id = extract_publer_credentials(ctx)
        
        if not api_key:
            return {
                "status": "authentication_failed",
                "error": "Missing API key. Please provide x-api-key header or Authorization: Bearer <key>",
                "integration_status": {
                    "authentication": "failed",
                    "workspace_access": "unknown",
                    "api_connectivity": "failed"
                }
            }
        
        # Create request headers for API client
        request_headers = {
            'x-api-key': api_key,
            'x-workspace-id': workspace_id or ''
        }
        
        client = create_client()
        
        # Get user information (tests basic API key authentication)
        user_info = await client.get("users/me", request_headers, include_workspace_header=False)
        
        # Get workspace information (tests workspace ID authentication)  
        workspaces = await client.get("workspaces", request_headers, include_workspace_header=False)
        
        # Find current workspace from header
        current_workspace = None
        
        if workspace_id and workspaces:
            for workspace in workspaces.get('data', []):
                if str(workspace.get('id')) == str(workspace_id):
                    current_workspace = workspace
                    break
        
        await client.close()
        
        return {
            "status": "connected",
            "account": {
                "user_id": user_info.get("id"),
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "account_type": user_info.get("account_type", "unknown"),
                "api_access": True
            },
            "workspace": {
                "id": workspace_id,
                "name": current_workspace.get("name") if current_workspace else "Unknown",
                "status": "active" if current_workspace else "not_found",
                "permissions": current_workspace.get("permissions", []) if current_workspace else []
            },
            "integration_status": {
                "authentication": "success",
                "workspace_access": "success" if current_workspace else "limited",
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
                    "workspace_access": "unknown",
                    "api_connectivity": "failed"
                }
            }
        elif "Permission denied" in str(e) or "403" in str(e):
            return {
                "status": "permission_denied", 
                "error": "Permission denied. Your API key may lack required scopes or workspace access.",
                "integration_status": {
                    "authentication": "success",
                    "workspace_access": "denied",
                    "api_connectivity": "limited"
                }
            }
        elif "Rate limit" in str(e):
            return {
                "status": "rate_limited",
                "error": "Rate limit exceeded. Please wait before trying again.",
                "integration_status": {
                    "authentication": "unknown",
                    "workspace_access": "unknown", 
                    "api_connectivity": "throttled"
                }
            }
        else:
            return {
                "status": "api_error",
                "error": f"Publer API error: {str(e)}",
                "integration_status": {
                    "authentication": "unknown",
                    "workspace_access": "unknown",
                    "api_connectivity": "error"
                }
            }
    
    except Exception as e:
        return {
            "status": "connection_error",
            "error": f"Connection error: {str(e)}",
            "integration_status": {
                "authentication": "unknown",
                "workspace_access": "unknown",
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
        # Extract credentials from request context
        api_key, workspace_id = extract_publer_credentials(ctx)
        
        if not api_key:
            return {
                "status": "authentication_failed",
                "error": "Missing API key. Please provide x-api-key header or Authorization: Bearer <key>",
                "platforms": []
            }
        
        if not workspace_id:
            return {
                "status": "workspace_required",
                "error": "Missing workspace ID. Please provide x-workspace-id header.",
                "platforms": []
            }
        
        # Create request headers for API client
        request_headers = {
            'x-api-key': api_key,
            'x-workspace-id': workspace_id
        }
        
        client = create_client()
        
        # Get accounts (tests workspace-scoped authentication)
        accounts_response = await client.get("accounts", request_headers)
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