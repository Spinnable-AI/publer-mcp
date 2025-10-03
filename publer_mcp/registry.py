"""
Tool registry for Publer MCP server.
"""

from mcp.server import FastMCP

from publer_mcp.tools.account import (
    publer_check_account_status,
    publer_list_connected_platforms,
)


def register_tools(mcp: FastMCP):
    """Register all Publer MCP tools."""
    
    # Account and workspace management tools
    mcp.add_tool(
        fn=publer_check_account_status,
        name="publer_check_account_status",
        description="Check your Publer account status, workspace access, and subscription limits to verify your integration is working correctly.",
    )
    
    mcp.add_tool(
        fn=publer_list_connected_platforms,
        name="publer_list_connected_platforms", 
        description="List all your connected social media platforms with their posting capabilities and current status.",
    )