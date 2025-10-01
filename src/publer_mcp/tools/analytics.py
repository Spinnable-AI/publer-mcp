"""MCP tools for Publer analytics."""

import json
import logging
from typing import Any, Dict, List

from mcp.types import Tool

from ..client.api import PublerAPIClient
from ..utils.errors import validate_required_params, safe_int_conversion, safe_datetime_parsing

logger = logging.getLogger(__name__)


def get_analytics_tools() -> List[Tool]:
    """Get all analytics MCP tools."""
    return [
        Tool(
            name="publer_analytics_post",
            description="Get analytics data for a specific post",
            inputSchema={
                "type": "object",
                "properties": {
                    "post_id": {
                        "type": "integer",
                        "description": "The ID of the post"
                    }
                },
                "required": ["post_id"]
            }
        ),
        Tool(
            name="publer_analytics_account",
            description="Get analytics data for a specific account over a date range",
            inputSchema={
                "type": "object",
                "properties": {
                    "account_id": {
                        "type": "integer",
                        "description": "The ID of the account"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date for analytics (ISO format)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date for analytics (ISO format)"
                    }
                },
                "required": ["account_id", "start_date", "end_date"]
            }
        )
    ]


async def handle_analytics_tool(tool_name: str, arguments: Dict[str, Any], api_client: PublerAPIClient) -> str:
    """Handle analytics tool calls."""
    logger.info(f"Executing analytics tool: {tool_name}")
    
    try:
        if tool_name == "publer_analytics_post":
            return await _handle_post_analytics(arguments, api_client)
        elif tool_name == "publer_analytics_account":
            return await _handle_account_analytics(arguments, api_client)
        else:
            return json.dumps({"error": f"Unknown analytics tool: {tool_name}"})
    except Exception as e:
        logger.error(f"Error in analytics tool {tool_name}: {e}")
        raise


async def _handle_post_analytics(arguments: Dict[str, Any], api_client: PublerAPIClient) -> str:
    """Handle publer_analytics_post tool call."""
    validate_required_params(arguments, ["post_id"])
    post_id = safe_int_conversion(arguments["post_id"], "post_id")
    
    analytics_list = await api_client.get_post_analytics(post_id)
    
    analytics_data = []
    for analytics in analytics_list:
        data = {
            "post_id": analytics.post_id,
            "platform": analytics.platform.value,
            "impressions": analytics.impressions,
            "reach": analytics.reach,
            "engagement": analytics.engagement,
            "likes": analytics.likes,
            "comments": analytics.comments,
            "shares": analytics.shares,
            "clicks": analytics.clicks,
            "saves": analytics.saves,
            "updated_at": analytics.updated_at.isoformat()
        }
        analytics_data.append(data)
    
    result = {
        "success": True,
        "data": {
            "post_analytics": analytics_data,
            "platforms_count": len(analytics_data)
        },
        "message": f"Retrieved analytics for post {post_id} across {len(analytics_data)} platforms"
    }
    
    return json.dumps(result, indent=2)


async def _handle_account_analytics(arguments: Dict[str, Any], api_client: PublerAPIClient) -> str:
    """Handle publer_analytics_account tool call."""
    validate_required_params(arguments, ["account_id", "start_date", "end_date"])
    
    account_id = safe_int_conversion(arguments["account_id"], "account_id")
    start_date = safe_datetime_parsing(arguments["start_date"], "start_date")
    end_date = safe_datetime_parsing(arguments["end_date"], "end_date")
    
    analytics = await api_client.get_account_analytics(account_id, start_date, end_date)
    
    analytics_data = {
        "account_id": analytics.account_id,
        "platform": analytics.platform.value,
        "followers": analytics.followers,
        "following": analytics.following,
        "posts_count": analytics.posts_count,
        "engagement_rate": analytics.engagement_rate,
        "period_start": analytics.period_start.isoformat(),
        "period_end": analytics.period_end.isoformat(),
        "updated_at": analytics.updated_at.isoformat()
    }
    
    result = {
        "success": True,
        "data": {"account_analytics": analytics_data},
        "message": f"Retrieved analytics for account {account_id} from {start_date.date()} to {end_date.date()}"
    }
    
    return json.dumps(result, indent=2)