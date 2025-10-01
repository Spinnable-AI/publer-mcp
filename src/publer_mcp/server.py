"""Main MCP server implementation for Publer integration."""

import asyncio
import logging
import os
from typing import Any, Sequence

from fastapi import FastAPI
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.server.sse import SseServerTransport
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    Tool,
    TextContent,
    EmptyResult,
)
from uvicorn import run

from publer_mcp.client.auth import PublerAuth
from publer_mcp.client.api import PublerAPIClient
from publer_mcp.tools.accounts import get_account_tools
from publer_mcp.tools.posts import get_post_tools
from publer_mcp.tools.media import get_media_tools
from publer_mcp.tools.analytics import get_analytics_tools
from publer_mcp.utils.errors import PublerMCPError, format_error_response

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables for server state
server = Server("publer-mcp")
api_client: PublerAPIClient | None = None


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List all available Publer MCP tools."""
    tools = []
    
    # Add all tool categories
    tools.extend(get_account_tools())
    tools.extend(get_post_tools())
    tools.extend(get_media_tools())
    tools.extend(get_analytics_tools())
    
    return tools


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
    """Handle tool execution requests."""
    if not api_client:
        raise PublerMCPError("API client not initialized. Please check your configuration.")
    
    try:
        # Route tool calls to appropriate handlers
        if name.startswith("publer_account_"):
            from publer_mcp.tools.accounts import handle_account_tool
            result = await handle_account_tool(name, arguments or {}, api_client)
        elif name.startswith("publer_post_"):
            from publer_mcp.tools.posts import handle_post_tool
            result = await handle_post_tool(name, arguments or {}, api_client)
        elif name.startswith("publer_media_"):
            from publer_mcp.tools.media import handle_media_tool
            result = await handle_media_tool(name, arguments or {}, api_client)
        elif name.startswith("publer_analytics_"):
            from publer_mcp.tools.analytics import handle_analytics_tool
            result = await handle_analytics_tool(name, arguments or {}, api_client)
        else:
            raise PublerMCPError(f"Unknown tool: {name}")
        
        return [TextContent(type="text", text=result)]
    
    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}")
        error_response = format_error_response(e, name, arguments)
        return [TextContent(type="text", text=error_response)]


def initialize_api_client() -> PublerAPIClient | None:
    """Initialize Publer API client with authentication."""
    api_key = os.getenv("PUBLER_API_KEY")
    workspace_id = os.getenv("PUBLER_WORKSPACE_ID")
    
    if not api_key or not workspace_id:
        logger.warning(
            "Publer API credentials not found. "
            "Set PUBLER_API_KEY and PUBLER_WORKSPACE_ID environment variables."
        )
        return None
    
    auth = PublerAuth(api_key=api_key, workspace_id=workspace_id)
    return PublerAPIClient(auth=auth)


# FastAPI app for SSE transport and health checks
app = FastAPI(title="Publer MCP Server", version="0.1.0")

@app.get("/health")
async def health_check():
    """Health check endpoint for deployment monitoring."""
    return {
        "status": "healthy",
        "service": "publer-mcp",
        "version": "0.1.0",
        "api_client_status": "connected" if api_client else "not_configured"
    }

@app.get("/sse")
async def handle_sse(request):
    """Handle Server-Sent Events transport."""
    transport = SseServerTransport("/sse")
    
    # Initialize API client if not already done
    global api_client
    if not api_client:
        api_client = initialize_api_client()
    
    async with transport.run_server(server, request):
        await asyncio.sleep(float("inf"))


async def main():
    """Main entry point for the MCP server."""
    transport = os.getenv("TRANSPORT", "stdio").lower()
    
    # Initialize API client
    global api_client
    api_client = initialize_api_client()
    
    if transport == "sse":
        # Run FastAPI server for SSE transport
        logger.info("Starting Publer MCP Server with SSE transport on port 8000")
        run(
            "publer_mcp.server:app",
            host="0.0.0.0",
            port=int(os.getenv("PORT", "8000")),
            log_level="info"
        )
    else:
        # Default to stdio transport for local development
        logger.info("Starting Publer MCP Server with stdio transport")
        async with stdio_server() as streams:
            await server.run(
                streams[0], streams[1], InitializationOptions(
                    server_name="publer-mcp",
                    server_version="0.1.0",
                    capabilities=server.get_capabilities(
                        notification_options=None,
                        experimental_capabilities=None,
                    ),
                )
            )


if __name__ == "__main__":
    asyncio.run(main())