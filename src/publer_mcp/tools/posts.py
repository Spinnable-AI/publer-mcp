"""MCP tools for Publer post management."""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from mcp.types import Tool

from ..client.api import PublerAPIClient
from ..client.models import Platform, PostStatus, CreatePostRequest, UpdatePostRequest, PostContent
from ..utils.errors import validate_required_params, safe_int_conversion, safe_datetime_parsing

logger = logging.getLogger(__name__)


def get_post_tools() -> List[Tool]:
    """Get all post management MCP tools."""
    return [
        Tool(
            name="publer_post_create",
            description="Create and optionally schedule a new social media post",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The text content of the post"
                    },
                    "account_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "List of account IDs to post to"
                    },
                    "media_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "List of media item IDs to include",
                        "default": []
                    },
                    "scheduled_at": {
                        "type": "string",
                        "description": "ISO datetime to schedule the post (optional)"
                    },
                    "link": {
                        "type": "string",
                        "description": "URL to share with the post"
                    }
                },
                "required": ["content", "account_ids"]
            }
        ),
        Tool(
            name="publer_post_list",
            description="List posts with optional filtering",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": [status.value for status in PostStatus],
                        "description": "Filter by post status"
                    },
                    "account_id": {
                        "type": "integer",
                        "description": "Filter by specific account"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100,
                        "description": "Maximum number of posts to return"
                    }
                }
            }
        ),
        Tool(
            name="publer_post_get",
            description="Get detailed information for a specific post",
            inputSchema={
                "type": "object",
                "properties": {
                    "post_id": {
                        "type": "integer",
                        "description": "The ID of the post to retrieve"
                    }
                },
                "required": ["post_id"]
            }
        ),
        Tool(
            name="publer_post_delete",
            description="Delete or cancel a scheduled post",
            inputSchema={
                "type": "object",
                "properties": {
                    "post_id": {
                        "type": "integer",
                        "description": "The ID of the post to delete"
                    }
                },
                "required": ["post_id"]
            }
        )
    ]


async def handle_post_tool(tool_name: str, arguments: Dict[str, Any], api_client: PublerAPIClient) -> str:
    """Handle post management tool calls."""
    logger.info(f"Executing post tool: {tool_name}")
    
    try:
        if tool_name == "publer_post_create":
            return await _handle_create_post(arguments, api_client)
        elif tool_name == "publer_post_list":
            return await _handle_list_posts(arguments, api_client)
        elif tool_name == "publer_post_get":
            return await _handle_get_post(arguments, api_client)
        elif tool_name == "publer_post_delete":
            return await _handle_delete_post(arguments, api_client)
        else:
            return json.dumps({"error": f"Unknown post tool: {tool_name}"})
    except Exception as e:
        logger.error(f"Error in post tool {tool_name}: {e}")
        raise


async def _handle_create_post(arguments: Dict[str, Any], api_client: PublerAPIClient) -> str:
    """Handle publer_post_create tool call."""
    validate_required_params(arguments, ["content", "account_ids"])
    
    # Parse arguments
    content_text = arguments["content"]
    account_ids = arguments["account_ids"]
    media_ids = arguments.get("media_ids", [])
    link = arguments.get("link")
    
    scheduled_at = None
    if "scheduled_at" in arguments:
        scheduled_at = safe_datetime_parsing(arguments["scheduled_at"], "scheduled_at")
    
    # Create post content
    post_content = PostContent(
        text=content_text,
        media=media_ids,
        link=link
    )
    
    # Create post request
    post_request = CreatePostRequest(
        content=post_content,
        accounts=account_ids,
        scheduled_at=scheduled_at
    )
    
    # Create the post
    post = await api_client.create_post(post_request)
    
    result = {
        "success": True,
        "data": {
            "post_id": post.id,
            "status": post.status.value,
            "content": {
                "text": post.content.text,
                "media_count": len(post.content.media)
            },
            "accounts": post.accounts,
            "scheduled_at": post.scheduled_at.isoformat() if post.scheduled_at else None,
            "created_at": post.created_at.isoformat()
        },
        "message": f"Post created successfully with ID: {post.id}"
    }
    
    if post.status == PostStatus.SCHEDULED:
        result["message"] += f" and scheduled for {post.scheduled_at}"
    
    return json.dumps(result, indent=2)


async def _handle_list_posts(arguments: Dict[str, Any], api_client: PublerAPIClient) -> str:
    """Handle publer_post_list tool call."""
    status = None
    if "status" in arguments:
        try:
            status = PostStatus(arguments["status"])
        except ValueError:
            return json.dumps({
                "error": f"Invalid status: {arguments['status']}",
                "valid_statuses": [s.value for s in PostStatus]
            })
    
    account_id = None
    if "account_id" in arguments:
        account_id = safe_int_conversion(arguments["account_id"], "account_id")
    
    limit = arguments.get("limit", 10)
    
    posts = await api_client.list_posts(
        status=status,
        account_id=account_id,
        limit=limit
    )
    
    posts_data = []
    for post in posts:
        post_data = {
            "id": post.id,
            "status": post.status.value,
            "content": {
                "text": post.content.text,
                "media_count": len(post.content.media)
            },
            "platforms": [p.value for p in post.platforms],
            "accounts": post.accounts,
            "scheduled_at": post.scheduled_at.isoformat() if post.scheduled_at else None,
            "published_at": post.published_at.isoformat() if post.published_at else None,
            "created_at": post.created_at.isoformat()
        }
        posts_data.append(post_data)
    
    result = {
        "success": True,
        "data": {
            "posts": posts_data,
            "count": len(posts_data),
            "filters": {
                "status": status.value if status else None,
                "account_id": account_id,
                "limit": limit
            }
        },
        "message": f"Retrieved {len(posts_data)} posts"
    }
    
    return json.dumps(result, indent=2)


async def _handle_get_post(arguments: Dict[str, Any], api_client: PublerAPIClient) -> str:
    """Handle publer_post_get tool call."""
    validate_required_params(arguments, ["post_id"])
    post_id = safe_int_conversion(arguments["post_id"], "post_id")
    
    post = await api_client.get_post(post_id)
    
    post_data = {
        "id": post.id,
        "status": post.status.value,
        "content": {
            "text": post.content.text,
            "media": post.content.media,
            "link": post.content.link
        },
        "platforms": [p.value for p in post.platforms],
        "accounts": post.accounts,
        "scheduled_at": post.scheduled_at.isoformat() if post.scheduled_at else None,
        "published_at": post.published_at.isoformat() if post.published_at else None,
        "created_at": post.created_at.isoformat(),
        "updated_at": post.updated_at.isoformat()
    }
    
    result = {
        "success": True,
        "data": {"post": post_data},
        "message": f"Retrieved post {post_id}"
    }
    
    return json.dumps(result, indent=2)


async def _handle_delete_post(arguments: Dict[str, Any], api_client: PublerAPIClient) -> str:
    """Handle publer_post_delete tool call."""
    validate_required_params(arguments, ["post_id"])
    post_id = safe_int_conversion(arguments["post_id"], "post_id")
    
    success = await api_client.delete_post(post_id)
    
    result = {
        "success": success,
        "data": {"post_id": post_id},
        "message": f"Post {post_id} deleted successfully" if success else f"Failed to delete post {post_id}"
    }
    
    return json.dumps(result, indent=2)