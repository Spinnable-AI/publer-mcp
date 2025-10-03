"""Tool registry for Publer MCP.

Single source of truth for all tool registrations.
All tool names must use the 'publer_' prefix.
"""

from mcp.server import FastMCP


def register_tools(mcp: FastMCP):
    """Register all Publer tools with the MCP server.

    Args:
        mcp: The FastMCP server instance to register tools with.
    """
    # Tools will be registered here as they are implemented
    # Example:
    # from publer_mcp.tools.example import example_tool
    # mcp.add_tool(
    #     fn=example_tool,
    #     name="publer_example",
    #     description="Example tool description",
    # )
    pass
