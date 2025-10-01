"""MCP tools for Publer media management."""

import json
import logging
from typing import Any, Dict, List

from mcp.types import Tool

from ..client.api import PublerAPIClient
from ..client.models import MediaType
from ..utils.errors import validate_required_params, safe_int_conversion

logger = logging.getLogger(__name__)


def get_media_tools() -> List[Tool]:
    """Get all media management MCP tools."""
    return [
        Tool(
            name="publer_media_list",
            description="List media library items",
            inputSchema={
                "type": "object",
                "properties": {
                    "media_type": {
                        "type": "string",
                        "enum": [t.value for t in MediaType],
                        "description": "Filter by media type"
                    },
                    "limit": {
                        "type": "integer", 
                        "default": 20,
                        "minimum": 1,
                        "maximum": 100,
                        "description": "Maximum items to return"
                    }
                }
            }
        ),
        Tool(
            name="publer_media_get",
            description="Get detailed information for a specific media item",
            inputSchema={
                "type": "object",
                "properties": {
                    "media_id": {
                        "type": "integer",
                        "description": "The ID of the media item"
                    }
                },
                "required": ["media_id"]
            }
        ),
        Tool(
            name="publer_media_upload",
            description="Upload media to Publer library from URL",
            inputSchema={
                "type": "object",
                "properties": {
                    "media_url": {
                        "type": "string",
                        "description": "URL of the media to upload"
                    },
                    "filename": {
                        "type": "string",
                        "description": "Original filename"
                    }
                },
                "required": ["media_url", "filename"]
            }
        )
    ]


async def handle_media_tool(tool_name: str, arguments: Dict[str, Any], api_client: PublerAPIClient) -> str:
    """Handle media management tool calls."""
    logger.info(f"Executing media tool: {tool_name}")
    
    try:
        if tool_name == "publer_media_list":
            return await _handle_list_media(arguments, api_client)
        elif tool_name == "publer_media_get":
            return await _handle_get_media(arguments, api_client)
        elif tool_name == "publer_media_upload":
            return await _handle_upload_media(arguments, api_client)
        else:
            return json.dumps({"error": f"Unknown media tool: {tool_name}"})
    except Exception as e:
        logger.error(f"Error in media tool {tool_name}: {e}")
        raise


async def _handle_list_media(arguments: Dict[str, Any], api_client: PublerAPIClient) -> str:
    """Handle publer_media_list tool call."""
    media_type = arguments.get("media_type")
    limit = arguments.get("limit", 20)
    
    media_items = await api_client.list_media(media_type=media_type, limit=limit)
    
    media_data = []
    for item in media_items:
        item_data = {
            "id": item.id,
            "type": item.type.value,
            "url": item.url,
            "thumbnail_url": item.thumbnail_url,
            "filename": item.filename,
            "size": item.size,
            "width": item.width,
            "height": item.height,
            "duration": item.duration,
            "created_at": item.created_at.isoformat()
        }
        media_data.append(item_data)
    
    result = {
        "success": True,
        "data": {
            "media": media_data,
            "count": len(media_data),
            "filters": {
                "media_type": media_type,
                "limit": limit
            }
        },
        "message": f"Retrieved {len(media_data)} media items"
    }
    
    return json.dumps(result, indent=2)


async def _handle_get_media(arguments: Dict[str, Any], api_client: PublerAPIClient) -> str:
    """Handle publer_media_get tool call."""
    validate_required_params(arguments, ["media_id"])
    media_id = safe_int_conversion(arguments["media_id"], "media_id")
    
    media_item = await api_client.get_media(media_id)
    
    item_data = {
        "id": media_item.id,
        "type": media_item.type.value,
        "url": media_item.url,
        "thumbnail_url": media_item.thumbnail_url,
        "filename": media_item.filename,
        "size": media_item.size,
        "width": media_item.width,
        "height": media_item.height,
        "duration": media_item.duration,
        "created_at": media_item.created_at.isoformat()
    }
    
    result = {
        "success": True,
        "data": {"media": item_data},
        "message": f"Retrieved media item {media_id}: {media_item.filename}"
    }
    
    return json.dumps(result, indent=2)


async def _handle_upload_media(arguments: Dict[str, Any], api_client: PublerAPIClient) -> str:
    """Handle publer_media_upload tool call."""
    validate_required_params(arguments, ["media_url", "filename"])
    
    media_url = arguments["media_url"]
    filename = arguments["filename"]
    
    media_item = await api_client.upload_media(media_url, filename)
    
    item_data = {
        "id": media_item.id,
        "type": media_item.type.value,
        "url": media_item.url,
        "filename": media_item.filename,
        "size": media_item.size,
        "created_at": media_item.created_at.isoformat()
    }
    
    result = {
        "success": True,
        "data": {"media": item_data},
        "message": f"Successfully uploaded {filename} with ID: {media_item.id}"
    }
    
    return json.dumps(result, indent=2)