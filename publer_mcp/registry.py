"""
Tool registry for Publer MCP server.
"""

from mcp.server import FastMCP

# Account management tools  
from publer_mcp.tools.account import (
    publer_check_account_status,
    publer_list_connected_platforms,
)

# Scheduling tools
from publer_mcp.tools.scheduling import (
    publer_blog_to_twitter_scheduler,
    publer_multi_platform_scheduler,
)

# Bulk operations tools
from publer_mcp.tools.bulk import (
    publer_bulk_content_series_scheduler,
)

# Optimization tools  
from publer_mcp.tools.optimization import (
    publer_optimal_time_scheduler,
)

# Monitoring tools
from publer_mcp.tools.monitoring import (
    publer_check_job_status,
    publer_monitor_recent_jobs,
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

    # Blog-to-Social and Multi-Platform Scheduling Tools
    mcp.add_tool(
        fn=publer_blog_to_twitter_scheduler,
        name="publer_blog_to_twitter_scheduler",
        description="Schedule a Twitter post promoting a blog post across specified social media platforms with automatic content optimization and metadata extraction.",
    )

    mcp.add_tool(
        fn=publer_multi_platform_scheduler,
        name="publer_multi_platform_scheduler", 
        description="Schedule the same content across multiple social media platforms with platform-specific optimizations and custom content per platform.",
    )

    # Bulk Content Operations
    mcp.add_tool(
        fn=publer_bulk_content_series_scheduler,
        name="publer_bulk_content_series_scheduler",
        description="Schedule a series of content posts across multiple platforms with intelligent timing distribution and configurable scheduling patterns.",
    )

    # Optimal Time Scheduling
    mcp.add_tool(
        fn=publer_optimal_time_scheduler,
        name="publer_optimal_time_scheduler",
        description="Schedule content at the optimal time for maximum engagement based on audience analytics, platform data, and historical performance.",
    )

    # Job Monitoring and Status Tools
    mcp.add_tool(
        fn=publer_check_job_status,
        name="publer_check_job_status",
        description="Check the status and results of a specific Publer job, including progress updates, engagement metrics, and error details.",
    )

    mcp.add_tool(
        fn=publer_monitor_recent_jobs,
        name="publer_monitor_recent_jobs",
        description="Monitor recent Publer jobs and their status across your workspace, with filtering options and success rate analytics.",
    )