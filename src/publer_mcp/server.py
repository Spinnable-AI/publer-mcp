"""
Publer MCP Server

The main MCP server implementation for Publer social media platform integration.
Provides comprehensive tools for social media management through the Model Context Protocol.
"""

import asyncio
import os
from typing import Any, Dict, List, Optional

import httpx
from mcp.server import Server
from mcp.server.models import InitializationOptions
from pydantic import BaseModel, Field

# Server configuration
app = Server("publer-mcp")

# Publer API configuration
PUBLER_API_BASE = "https://api.publer.io/v1"

class PublerConfig:
    """Publer API configuration"""
    
    def __init__(self):
        self.api_key: Optional[str] = None
        self.workspace_id: Optional[str] = None
        self.base_url = PUBLER_API_BASE
    
    def configure_from_headers(self, headers: Dict[str, str]) -> None:
        """Configure from request headers (Spinnable auth pattern)"""
        self.api_key = headers.get("x-api-key") or headers.get("X-API-Key")
        self.workspace_id = headers.get("x-workspace-id") or headers.get("X-Workspace-Id")
    
    @property
    def is_configured(self) -> bool:
        """Check if API credentials are configured"""
        return bool(self.api_key and self.workspace_id)
    
    @property
    def auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for Publer API"""
        if not self.is_configured:
            raise ValueError("Publer API credentials not configured")
        
        return {
            "Authorization": f"Bearer-API {self.api_key}",
            "Publer-Workspace-Id": self.workspace_id,
            "Content-Type": "application/json"
        }

class PublerClient:
    """Publer API client"""
    
    def __init__(self, config: PublerConfig):
        self.config = config
        self.client = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=30.0
        )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def get_accounts(self) -> List[Dict[str, Any]]:
        """Get connected social media accounts"""
        response = await self.client.get("/accounts", headers=self.config.auth_headers)
        response.raise_for_status()
        return response.json()
    
    async def health_check(self) -> Dict[str, Any]:
        """Verify API connectivity and credentials"""
        try:
            accounts = await self.get_accounts()
            return {
                "status": "healthy",
                "api_accessible": True,
                "accounts_count": len(accounts),
                "workspace_id": self.config.workspace_id
            }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return {
                    "status": "error",
                    "error": "authentication_failed",
                    "message": "Invalid API key or insufficient permissions",
                    "api_accessible": False
                }
            elif e.response.status_code == 403:
                return {
                    "status": "error", 
                    "error": "workspace_access_denied",
                    "message": "Access denied to workspace - verify workspace ID",
                    "api_accessible": True
                }
            else:
                return {
                    "status": "error",
                    "error": "api_error",
                    "message": f"Publer API error: {e.response.status_code}",
                    "api_accessible": False
                }
        except Exception as e:
            return {
                "status": "error",
                "error": "connection_failed",
                "message": f"Failed to connect to Publer API: {str(e)}",
                "api_accessible": False
            }

# Global configuration instance
publer_config = PublerConfig()

@app.list_tools()
async def handle_list_tools() -> List[Any]:
    """List available MCP tools"""
    return [
        {
            "name": "publer_status",
            "description": "Check Publer API connection status and account information",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        },
        {
            "name": "publer_list_accounts",
            "description": "List all connected social media accounts in the workspace",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        }
    ]

@app.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[Any]:
    """Handle tool execution"""
    
    # Configure API credentials from environment or headers
    # In production, Spinnable backend will pass credentials via headers
    if not publer_config.is_configured:
        # Try environment variables for local development
        api_key = os.getenv("PUBLER_API_KEY")
        workspace_id = os.getenv("PUBLER_WORKSPACE_ID")
        
        if api_key and workspace_id:
            publer_config.api_key = api_key
            publer_config.workspace_id = workspace_id
    
    if name == "publer_status":
        return await _handle_publer_status()
    elif name == "publer_list_accounts":
        return await _handle_list_accounts()
    else:
        raise ValueError(f"Unknown tool: {name}")

async def _handle_publer_status() -> List[Any]:
    """Handle publer_status tool"""
    if not publer_config.is_configured:
        return [{
            "type": "text",
            "text": "❌ Publer MCP Status: NOT CONFIGURED\n\n"
                   "Missing API credentials. Please configure:\n"
                   "- PUBLER_API_KEY environment variable\n"
                   "- PUBLER_WORKSPACE_ID environment variable\n\n"
                   "Or ensure Spinnable backend is passing credentials via headers."
        }]
    
    async with PublerClient(publer_config) as client:
        status = await client.health_check()
        
        if status["status"] == "healthy":
            return [{
                "type": "text",
                "text": f"✅ Publer MCP Status: HEALTHY\n\n"
                       f"🔗 API Connection: Active\n"
                       f"🏢 Workspace ID: {status['workspace_id']}\n"
                       f"📱 Connected Accounts: {status['accounts_count']}\n\n"
                       f"Ready to manage your social media accounts!"
            }]
        else:
            return [{
                "type": "text", 
                "text": f"❌ Publer MCP Status: ERROR\n\n"
                       f"Error Type: {status['error']}\n"
                       f"Message: {status['message']}\n\n"
                       f"Please verify your API credentials and permissions."
            }]

async def _handle_list_accounts() -> List[Any]:
    """Handle publer_list_accounts tool"""
    if not publer_config.is_configured:
        return [{
            "type": "text",
            "text": "❌ Cannot list accounts - Publer API not configured\n\n"
                   "Please run 'publer_status' tool first to verify configuration."
        }]
    
    try:
        async with PublerClient(publer_config) as client:
            accounts = await client.get_accounts()
            
            if not accounts:
                return [{
                    "type": "text",
                    "text": "📱 No social media accounts connected to this workspace.\n\n"
                           "Visit https://app.publer.io to connect your social media accounts."
                }]
            
            # Format accounts list
            account_list = "📱 **Connected Social Media Accounts**\n\n"
            for i, account in enumerate(accounts, 1):
                platform = account.get("platform", "Unknown")
                name = account.get("name", "Unknown")
                status = "✅ Active" if account.get("status") == "active" else "❌ Inactive"
                account_list += f"{i}. **{platform}**: {name} - {status}\n"
            
            account_list += f"\n**Total**: {len(accounts)} connected accounts"
            
            return [{"type": "text", "text": account_list}]
            
    except Exception as e:
        return [{
            "type": "text",
            "text": f"❌ Error retrieving accounts: {str(e)}\n\n"
                   "Please check your API credentials and try again."
        }]

@app.list_resources()
async def handle_list_resources() -> List[Any]:
    """List available resources"""
    return []

@app.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Read a specific resource"""
    raise ValueError(f"Resource not found: {uri}")

# Health check endpoint for Fly.io
async def health_check() -> Dict[str, str]:
    """Health check for deployment platforms"""
    return {"status": "healthy", "service": "publer-mcp"}

if __name__ == "__main__":
    # For local development
    import mcp.server.stdio
    
    async def main():
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream, 
                write_stream, 
                InitializationOptions(
                    server_name="publer-mcp",
                    server_version="0.1.0",
                    capabilities={}
                )
            )
    
    asyncio.run(main())