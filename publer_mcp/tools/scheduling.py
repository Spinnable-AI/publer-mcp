"""
Blog-to-Twitter and multi-platform scheduling tools for Publer MCP.
"""

from typing import Any, Dict, List, Optional, Annotated
from mcp.server.fastmcp import Context
from pydantic import Field
import re
from urllib.parse import urlparse

from ..auth import extract_publer_credentials, validate_api_key, validate_workspace_id, create_api_headers
from ..client import create_client, PublerAPIError
from ..utils.content_parser import BlogContentParser
from ..utils.job_tracker import AsyncJobTracker


async def publer_blog_to_twitter_scheduler(
    ctx: Context,
    blog_url: Annotated[str, Field(description="URL of the blog post to promote")],
    twitter_message: Annotated[str, Field(description="Custom Twitter message (max 280 chars)")],
    workspace_id: Annotated[str, Field(description="Publer workspace ID")],
    target_platforms: Annotated[List[str], Field(description="Platform account IDs to post to")] = None,
    schedule_time: Annotated[Optional[str], Field(description="ISO format datetime for scheduling (e.g., '2024-01-15T10:00:00Z')")] = None,
    include_blog_preview: Annotated[bool, Field(description="Include blog preview image if available")] = True
) -> Dict[str, Any]:
    """
    Schedule a Twitter post promoting a blog post across specified social media platforms.
    
    This tool extracts blog metadata (title, preview image, keywords) and creates 
    optimized social media posts that drive traffic to your blog. Perfect for 
    content marketing and blog promotion strategies.
    
    Returns:
        Dict containing job_id for async tracking, scheduled posts details, and blog analysis
    """
    try:
        # Extract and validate credentials
        credentials = extract_publer_credentials(ctx)
        api_valid, api_error = validate_api_key(credentials)
        if not api_valid:
            return {
                "status": "authentication_failed",
                "error": api_error,
                "action_required": "Verify x-api-key header"
            }
        
        # Validate workspace_id parameter
        workspace_valid, workspace_error = validate_workspace_id(workspace_id)
        if not workspace_valid:
            return {
                "status": "validation_failed",
                "error": workspace_error,
                "action_required": "Provide a valid workspace_id parameter"
            }
        
        # Validate inputs
        if not blog_url or not _is_valid_url(blog_url):
            return {
                "status": "validation_failed",
                "error": "Invalid blog URL provided",
                "action_required": "Provide a valid HTTP/HTTPS URL"
            }
        
        if not twitter_message or len(twitter_message) > 280:
            return {
                "status": "validation_failed", 
                "error": f"Twitter message must be 1-280 characters (current: {len(twitter_message or '')})",
                "action_required": "Adjust message length for Twitter requirements"
            }
        
        client = create_client()
        
        # Get available accounts to validate platforms
        accounts_headers = create_api_headers(credentials, workspace_id=workspace_id)
        accounts_response = await client.get("accounts", accounts_headers)
        available_accounts = accounts_response.get('data', [])
        
        # Filter for Twitter accounts if no specific platforms provided
        if not target_platforms:
            target_platforms = [acc['id'] for acc in available_accounts if acc.get('type') == 'twitter' and acc.get('status') == 'active']
        
        # Validate platform IDs
        valid_account_ids = [str(acc['id']) for acc in available_accounts if acc.get('status') == 'active']
        invalid_platforms = [pid for pid in target_platforms if str(pid) not in valid_account_ids]
        
        if invalid_platforms:
            return {
                "status": "validation_failed",
                "error": f"Invalid or disconnected platform IDs: {', '.join(map(str, invalid_platforms))}",
                "action_required": "Use publer_list_connected_platforms to see available accounts",
                "available_accounts": [{"id": acc['id'], "platform": acc.get('type'), "name": acc.get('name')} for acc in available_accounts if acc.get('status') == 'active']
            }
        
        # Parse blog content for metadata
        blog_parser = BlogContentParser()
        blog_analysis = await blog_parser.parse_blog_url(blog_url)
        
        # Create platform-optimized posts
        scheduled_posts = []
        for platform_id in target_platforms:
            # Find platform details
            platform_account = next((acc for acc in available_accounts if str(acc['id']) == str(platform_id)), None)
            if not platform_account:
                continue
                
            platform_type = platform_account.get('type', 'unknown')
            
            # Create optimized content for platform
            optimized_content = _optimize_content_for_platform(
                platform_type=platform_type,
                base_message=twitter_message,
                blog_url=blog_url,
                blog_analysis=blog_analysis
            )
            
            # Prepare media if blog preview available
            media_urls = []
            if include_blog_preview and blog_analysis.get('preview_image'):
                media_urls = [blog_analysis['preview_image']]
            
            post_data = {
                "content": optimized_content,
                "accounts": [platform_id],
                "media_urls": media_urls,
                "scheduled_time": schedule_time
            }
            
            scheduled_posts.append({
                "platform": platform_type,
                "account_id": platform_id,
                "account_name": platform_account.get('name', 'Unknown'),
                "content": optimized_content,
                "media": media_urls,
                "scheduled_time": schedule_time or "immediate"
            })
        
        # Submit job to Publer API
        job_payload = {
            "posts": [
                {
                    "content": post["content"],
                    "accounts": [post["account_id"]],
                    "media_urls": post["media"],
                    "scheduled_time": schedule_time
                } for post in scheduled_posts
            ]
        }
        
        job_result = await AsyncJobTracker.submit_job(
            client=client,
            endpoint="posts/schedule",
            headers=accounts_headers,
            payload=job_payload
        )
        
        await client.close()
        
        # Return comprehensive response
        if job_result.get("status") == "job_submitted":
            return {
                "status": "job_submitted",
                "job_id": job_result["job_id"],
                "scheduled_posts": scheduled_posts,
                "blog_analysis": blog_analysis,
                "summary": {
                    "total_platforms": len(scheduled_posts),
                    "blog_title": blog_analysis.get('title', 'Unknown'),
                    "estimated_reach": _calculate_estimated_reach(available_accounts, target_platforms)
                }
            }
        else:
            return job_result
        
    except PublerAPIError as e:
        return _handle_api_error(e)
    except Exception as e:
        return {
            "status": "error",
            "error": f"Unexpected error: {str(e)}",
            "retry_recommended": True
        }


async def publer_multi_platform_scheduler(
    ctx: Context,
    content: Annotated[str, Field(description="Main content text for all platforms")],
    target_platforms: Annotated[List[str], Field(description="Platform account IDs to post to")],
    workspace_id: Annotated[str, Field(description="Publer workspace ID")],
    platform_customizations: Annotated[Optional[Dict[str, Dict]], Field(description="Platform-specific content overrides (e.g., {'twitter': {'content': 'Custom tweet'}})")] = None,
    media_urls: Annotated[List[str], Field(description="Media URLs to attach to posts")] = None,
    schedule_time: Annotated[Optional[str], Field(description="ISO format datetime for scheduling (e.g., '2024-01-15T10:00:00Z')")] = None
) -> Dict[str, Any]:
    """
    Schedule the same content across multiple social media platforms with platform-specific optimizations.
    
    This tool handles cross-platform posting with automatic content adaptation for each platform's 
    requirements and best practices. Supports custom content per platform and media attachments.
    
    Returns:
        Dict containing job_id for async tracking and detailed scheduling information per platform
    """
    try:
        # Extract and validate credentials
        credentials = extract_publer_credentials(ctx)
        api_valid, api_error = validate_api_key(credentials)
        if not api_valid:
            return {
                "status": "authentication_failed",
                "error": api_error,
                "action_required": "Verify x-api-key header"
            }
        
        # Validate workspace_id parameter
        workspace_valid, workspace_error = validate_workspace_id(workspace_id)
        if not workspace_valid:
            return {
                "status": "validation_failed",
                "error": workspace_error,
                "action_required": "Provide a valid workspace_id parameter"
            }
        
        # Validate inputs
        if not content or len(content.strip()) == 0:
            return {
                "status": "validation_failed",
                "error": "Content cannot be empty",
                "action_required": "Provide content text for the posts"
            }
        
        if not target_platforms or len(target_platforms) == 0:
            return {
                "status": "validation_failed",
                "error": "At least one target platform is required",
                "action_required": "Specify platform account IDs to post to"
            }
        
        client = create_client()
        
        # Get available accounts to validate platforms and get platform types
        accounts_headers = create_api_headers(credentials, workspace_id=workspace_id)
        accounts_response = await client.get("accounts", accounts_headers)
        available_accounts = accounts_response.get('data', [])
        
        # Validate platform IDs and get platform mapping
        platform_mapping = {}
        valid_account_ids = []
        
        for account in available_accounts:
            if account.get('status') == 'active':
                account_id = str(account['id'])
                valid_account_ids.append(account_id)
                platform_mapping[account_id] = {
                    'type': account.get('type', 'unknown'),
                    'name': account.get('name', 'Unknown'),
                    'capabilities': _get_platform_capabilities(account.get('type', 'unknown'))
                }
        
        invalid_platforms = [pid for pid in target_platforms if str(pid) not in valid_account_ids]
        if invalid_platforms:
            return {
                "status": "validation_failed",
                "error": f"Invalid or disconnected platform IDs: {', '.join(map(str, invalid_platforms))}",
                "action_required": "Use publer_list_connected_platforms to see available accounts",
                "available_accounts": [{"id": acc['id'], "platform": acc.get('type'), "name": acc.get('name')} for acc in available_accounts if acc.get('status') == 'active']
            }
        
        # Validate media URLs if provided
        if media_urls:
            invalid_urls = [url for url in media_urls if not _is_valid_url(url)]
            if invalid_urls:
                return {
                    "status": "validation_failed",
                    "error": f"Invalid media URLs: {', '.join(invalid_urls)}",
                    "action_required": "Provide valid HTTP/HTTPS URLs for media"
                }
        
        # Create platform-optimized posts
        scheduled_posts = []
        platform_posts_data = []
        
        for platform_id in target_platforms:
            platform_id_str = str(platform_id)
            platform_info = platform_mapping.get(platform_id_str)
            
            if not platform_info:
                continue
            
            platform_type = platform_info['type']
            
            # Use platform-specific customization if provided, otherwise optimize base content
            if platform_customizations and platform_type in platform_customizations:
                custom_content = platform_customizations[platform_type].get('content', content)
                optimized_content = _optimize_content_for_platform(
                    platform_type=platform_type,
                    base_message=custom_content,
                    blog_url=None,
                    blog_analysis={}
                )
            else:
                optimized_content = _optimize_content_for_platform(
                    platform_type=platform_type,
                    base_message=content,
                    blog_url=None,
                    blog_analysis={}
                )
            
            # Filter media based on platform capabilities
            platform_media = _filter_media_for_platform(platform_type, media_urls or [])
            
            scheduled_posts.append({
                "platform": platform_type,
                "account_id": platform_id,
                "account_name": platform_info['name'],
                "content": optimized_content,
                "media": platform_media,
                "scheduled_time": schedule_time or "immediate",
                "capabilities": platform_info['capabilities']
            })
            
            # Prepare data for API submission
            platform_posts_data.append({
                "content": optimized_content,
                "accounts": [platform_id],
                "media_urls": platform_media,
                "scheduled_time": schedule_time
            })
        
        # Submit job to Publer API
        job_payload = {"posts": platform_posts_data}
        
        job_result = await AsyncJobTracker.submit_job(
            client=client,
            endpoint="posts/schedule",
            headers=accounts_headers,
            payload=job_payload
        )
        
        await client.close()
        
        # Return comprehensive response
        if job_result.get("status") == "job_submitted":
            return {
                "status": "job_submitted",
                "job_id": job_result["job_id"],
                "scheduled_posts": scheduled_posts,
                "summary": {
                    "total_platforms": len(scheduled_posts),
                    "platforms_by_type": _group_platforms_by_type(scheduled_posts),
                    "total_posts": len(scheduled_posts),
                    "estimated_reach": _calculate_estimated_reach(available_accounts, target_platforms)
                }
            }
        else:
            return job_result
        
    except PublerAPIError as e:
        return _handle_api_error(e)
    except Exception as e:
        return {
            "status": "error",
            "error": f"Unexpected error: {str(e)}",
            "retry_recommended": True
        }


def _is_valid_url(url: str) -> bool:
    """Validate URL format."""
    try:
        result = urlparse(url)
        return all([result.scheme in ('http', 'https'), result.netloc])
    except:
        return False


def _optimize_content_for_platform(platform_type: str, base_message: str, blog_url: Optional[str], blog_analysis: Dict) -> str:
    """Optimize content for specific platform requirements."""
    content = base_message.strip()
    
    if platform_type == 'twitter':
        # Twitter optimization: hashtags, mentions, length limits
        if blog_url:
            # Ensure space for URL (23 chars after t.co shortening)
            max_content_length = 257  # 280 - 23 for URL
            if len(content) > max_content_length:
                content = content[:max_content_length-3] + "..."
            content = f"{content} {blog_url}"
        
        # Add relevant hashtags if blog has keywords
        keywords = blog_analysis.get('keywords', [])
        if keywords and len(content) < 250:  # Leave space for hashtags
            hashtags = [f"#{kw.replace(' ', '')}" for kw in keywords[:2] if len(kw) < 20]
            if hashtags:
                content += " " + " ".join(hashtags)
    
    elif platform_type == 'linkedin':
        # LinkedIn optimization: professional tone, longer content allowed
        if blog_url:
            content = f"{content}\n\nRead more: {blog_url}"
        
        # Add professional context
        blog_title = blog_analysis.get('title')
        if blog_title and blog_title.lower() not in content.lower():
            content = f'"{blog_title}"\n\n{content}'
    
    elif platform_type == 'facebook':
        # Facebook optimization: engaging, social tone
        if blog_url:
            content = f"{content}\n\n{blog_url}"
    
    elif platform_type == 'instagram':
        # Instagram optimization: visual focus, hashtags
        keywords = blog_analysis.get('keywords', [])
        if keywords:
            hashtags = [f"#{kw.replace(' ', '').lower()}" for kw in keywords[:5]]
            content = f"{content}\n\n" + " ".join(hashtags)
    
    return content


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


def _filter_media_for_platform(platform_type: str, media_urls: List[str]) -> List[str]:
    """Filter media URLs based on platform capabilities."""
    capabilities = _get_platform_capabilities(platform_type)
    
    # For now, return all media - future enhancement could filter by media type
    # e.g., TikTok only supports video, Pinterest prefers images
    return media_urls


def _calculate_estimated_reach(available_accounts: List[Dict], target_platform_ids: List[str]) -> str:
    """Calculate estimated reach based on follower counts."""
    total_followers = 0
    account_count = 0
    
    for platform_id in target_platform_ids:
        account = next((acc for acc in available_accounts if str(acc['id']) == str(platform_id)), None)
        if account and account.get('follower_count'):
            total_followers += account['follower_count']
            account_count += 1
    
    if account_count == 0:
        return "Unable to calculate reach"
    
    if total_followers < 1000:
        return f"{total_followers} followers across {account_count} accounts"
    elif total_followers < 1000000:
        return f"{total_followers/1000:.1f}K followers across {account_count} accounts"
    else:
        return f"{total_followers/1000000:.1f}M followers across {account_count} accounts"


def _group_platforms_by_type(scheduled_posts: List[Dict]) -> Dict[str, int]:
    """Group platforms by type for summary."""
    platform_counts = {}
    for post in scheduled_posts:
        platform_type = post['platform']
        platform_counts[platform_type] = platform_counts.get(platform_type, 0) + 1
    return platform_counts


def _handle_api_error(error: PublerAPIError) -> Dict[str, Any]:
    """Handle Publer API errors with appropriate responses."""
    error_str = str(error)
    
    if "Invalid API key" in error_str or "401" in error_str:
        return {
            "status": "authentication_failed",
            "error": "Invalid API key. Please check your Publer API credentials.",
            "action_required": "Verify your x-api-key header"
        }
    elif "Permission denied" in error_str or "403" in error_str:
        return {
            "status": "permission_denied",
            "error": "Permission denied. Your API key may lack required scopes or workspace access.",
            "action_required": "Contact your Publer workspace admin to verify permissions"
        }
    elif "Rate limit" in error_str:
        return {
            "status": "rate_limited",
            "error": "Rate limit exceeded. Publer allows 100 requests per 2 minutes.",
            "action_required": "Wait before retrying. Consider reducing concurrent requests."
        }
    else:
        return {
            "status": "api_error",
            "error": f"Publer API error: {error_str}",
            "retry_recommended": True
        }