"""
Bulk content series scheduling tool for Publer MCP.
"""

from typing import Any, Dict, List, Optional, Annotated
from mcp.server.fastmcp import Context
from pydantic import Field
from datetime import datetime, timedelta
import uuid

from ..auth import extract_publer_credentials, validate_workspace_access, create_api_headers
from ..client import create_client, PublerAPIError
from ..utils.job_tracker import AsyncJobTracker


async def publer_bulk_content_series_scheduler(
    ctx: Context,
    content_series: Annotated[List[Dict], Field(description="Array of content objects with 'content' field and optional 'media_urls', 'schedule_time' fields")],
    target_platforms: Annotated[List[str], Field(description="Platform account IDs to post all content to")],
    schedule_pattern: Annotated[str, Field(description="Scheduling pattern: 'daily', 'weekly', 'custom', or 'immediate'")] = "daily",
    start_date: Annotated[Optional[str], Field(description="ISO format start date (e.g., '2024-01-15T10:00:00Z'). Required for scheduled patterns.")] = None,
    time_spacing: Annotated[int, Field(ge=1, le=168, description="Hours between posts (1-168 hours)")] = 24,
    randomize_timing: Annotated[bool, Field(description="Add random variance to post times (±30 minutes)")] = False
) -> Dict[str, Any]:
    """
    Schedule a series of content posts across multiple platforms with intelligent timing distribution.
    
    This tool handles bulk content scheduling with configurable patterns, perfect for content series, 
    campaigns, or maintaining consistent posting schedules. Supports immediate posting, daily/weekly 
    patterns, or custom timing for each post.
    
    Returns:
        Dict containing batch_id, individual job_ids for tracking, and detailed scheduling information
    """
    try:
        # Extract and validate credentials
        credentials = extract_publer_credentials(ctx)
        workspace_valid, workspace_error = validate_workspace_access(credentials)
        if not workspace_valid:
            return {
                "status": "authentication_failed",
                "error": workspace_error,
                "action_required": "Verify x-api-key and x-workspace-id headers"
            }
        
        # Validate inputs
        if not content_series or len(content_series) == 0:
            return {
                "status": "validation_failed",
                "error": "Content series cannot be empty",
                "action_required": "Provide at least one content item"
            }
        
        if len(content_series) > 50:
            return {
                "status": "validation_failed",
                "error": f"Maximum 50 posts per batch (provided: {len(content_series)})",
                "action_required": "Split into smaller batches for better performance"
            }
        
        # Validate content items
        for i, item in enumerate(content_series):
            if not isinstance(item, dict) or 'content' not in item:
                return {
                    "status": "validation_failed",
                    "error": f"Content item {i+1} missing required 'content' field",
                    "action_required": "Each content item must have a 'content' field with the post text"
                }
            
            if not item['content'] or not item['content'].strip():
                return {
                    "status": "validation_failed",
                    "error": f"Content item {i+1} has empty content",
                    "action_required": "Provide non-empty content for all posts"
                }
        
        if not target_platforms or len(target_platforms) == 0:
            return {
                "status": "validation_failed",
                "error": "At least one target platform is required",
                "action_required": "Specify platform account IDs to post to"
            }
        
        # Validate schedule pattern and timing
        valid_patterns = ['daily', 'weekly', 'custom', 'immediate']
        if schedule_pattern not in valid_patterns:
            return {
                "status": "validation_failed",
                "error": f"Invalid schedule pattern '{schedule_pattern}'. Must be one of: {', '.join(valid_patterns)}",
                "action_required": "Choose a valid scheduling pattern"
            }
        
        if schedule_pattern != 'immediate' and not start_date:
            return {
                "status": "validation_failed",
                "error": f"Start date is required for '{schedule_pattern}' pattern",
                "action_required": "Provide start_date in ISO format (e.g., '2024-01-15T10:00:00Z')"
            }
        
        # Parse and validate start_date if provided
        start_datetime = None
        if start_date:
            try:
                start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                return {
                    "status": "validation_failed",
                    "error": f"Invalid start_date format: '{start_date}'",
                    "action_required": "Use ISO format like '2024-01-15T10:00:00Z'"
                }
        
        client = create_client()
        
        # Get available accounts to validate platforms
        accounts_headers = create_api_headers(credentials, include_workspace=True)
        accounts_response = await client.get("accounts", accounts_headers)
        available_accounts = accounts_response.get('data', [])
        
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
        
        # Generate batch ID for tracking
        batch_id = f"batch_{uuid.uuid4().hex[:8]}"
        
        # Calculate posting schedule
        scheduled_series = []
        job_data = []
        
        for i, content_item in enumerate(content_series):
            content_text = content_item['content'].strip()
            media_urls = content_item.get('media_urls', [])
            
            # Determine scheduling time
            if schedule_pattern == 'immediate':
                scheduled_time = None
            elif schedule_pattern == 'custom' and 'schedule_time' in content_item:
                # Use custom time from content item
                try:
                    custom_datetime = datetime.fromisoformat(content_item['schedule_time'].replace('Z', '+00:00'))
                    scheduled_time = custom_datetime.isoformat()
                except ValueError:
                    return {
                        "status": "validation_failed",
                        "error": f"Invalid schedule_time in content item {i+1}: '{content_item['schedule_time']}'",
                        "action_required": "Use ISO format like '2024-01-15T10:00:00Z'"
                    }
            else:
                # Calculate time based on pattern
                if schedule_pattern == 'daily':
                    post_datetime = start_datetime + timedelta(days=i)
                elif schedule_pattern == 'weekly':
                    post_datetime = start_datetime + timedelta(weeks=i)
                else:  # custom with time_spacing
                    post_datetime = start_datetime + timedelta(hours=i * time_spacing)
                
                # Add randomization if requested
                if randomize_timing:
                    import random
                    variance_minutes = random.randint(-30, 30)
                    post_datetime += timedelta(minutes=variance_minutes)
                
                scheduled_time = post_datetime.isoformat()
            
            # Validate media URLs if provided
            if media_urls:
                invalid_media_urls = [url for url in media_urls if not _is_valid_url(url)]
                if invalid_media_urls:
                    return {
                        "status": "validation_failed",
                        "error": f"Invalid media URLs in content item {i+1}: {', '.join(invalid_media_urls)}",
                        "action_required": "Provide valid HTTP/HTTPS URLs for media"
                    }
            
            # Create job data for this content item
            posts_for_item = []
            for platform_id in target_platforms:
                platform_account = next((acc for acc in available_accounts if str(acc['id']) == str(platform_id)), None)
                platform_type = platform_account.get('type', 'unknown') if platform_account else 'unknown'
                
                # Optimize content for platform
                optimized_content = _optimize_bulk_content_for_platform(platform_type, content_text)
                
                posts_for_item.append({
                    "content": optimized_content,
                    "accounts": [platform_id],
                    "media_urls": media_urls,
                    "scheduled_time": scheduled_time
                })
            
            job_data.append({
                "posts": posts_for_item
            })
            
            # Track in series for response
            scheduled_series.append({
                "post_number": i + 1,
                "content": content_text,
                "platforms": [str(pid) for pid in target_platforms],
                "platform_details": [
                    {
                        "id": pid,
                        "type": next((acc.get('type', 'unknown') for acc in available_accounts if str(acc['id']) == str(pid)), 'unknown'),
                        "name": next((acc.get('name', 'Unknown') for acc in available_accounts if str(acc['id']) == str(pid)), 'Unknown')
                    } for pid in target_platforms
                ],
                "scheduled_time": scheduled_time or "immediate",
                "media_count": len(media_urls),
                "batch_id": batch_id
            })
        
        # Submit all jobs to Publer API
        job_ids = []
        failed_submissions = []
        
        for i, job_payload in enumerate(job_data):
            try:
                job_result = await AsyncJobTracker.submit_job(
                    client=client,
                    endpoint="posts/schedule",
                    headers=accounts_headers,
                    payload=job_payload
                )
                
                if job_result.get("status") == "job_submitted":
                    job_id = job_result["job_id"]
                    job_ids.append(job_id)
                    scheduled_series[i]["job_id"] = job_id
                else:
                    failed_submissions.append({
                        "post_number": i + 1,
                        "error": job_result.get("error", "Unknown submission error")
                    })
            except Exception as e:
                failed_submissions.append({
                    "post_number": i + 1,
                    "error": f"Submission error: {str(e)}"
                })
        
        await client.close()
        
        # Calculate series summary
        total_posts_count = len(content_series) * len(target_platforms)
        successful_jobs = len(job_ids)
        
        if successful_jobs == 0:
            return {
                "status": "all_submissions_failed",
                "batch_id": batch_id,
                "error": "All job submissions failed",
                "failed_submissions": failed_submissions,
                "retry_recommended": True
            }
        
        # Calculate estimated completion time
        if schedule_pattern != 'immediate' and scheduled_series:
            last_scheduled = scheduled_series[-1]["scheduled_time"]
            if last_scheduled != "immediate":
                estimated_completion = last_scheduled
            else:
                estimated_completion = "immediate"
        else:
            estimated_completion = "immediate"
        
        return {
            "status": "bulk_jobs_submitted" if successful_jobs == len(content_series) else "partial_success",
            "batch_id": batch_id,
            "job_ids": job_ids,
            "scheduled_series": scheduled_series,
            "series_summary": {
                "total_content_items": len(content_series),
                "successful_submissions": successful_jobs,
                "failed_submissions": len(failed_submissions),
                "total_scheduled_posts": successful_jobs * len(target_platforms),
                "platforms_used": len(target_platforms),
                "schedule_pattern": schedule_pattern,
                "estimated_completion": estimated_completion,
                "duration_calculation": _calculate_series_duration(schedule_pattern, len(content_series), time_spacing)
            },
            "failed_submissions": failed_submissions if failed_submissions else []
        }
        
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
        from urllib.parse import urlparse
        result = urlparse(url)
        return all([result.scheme in ('http', 'https'), result.netloc])
    except:
        return False


def _optimize_bulk_content_for_platform(platform_type: str, content: str) -> str:
    """Optimize content for specific platform in bulk operations."""
    if platform_type == 'twitter' and len(content) > 280:
        # Truncate for Twitter with ellipsis
        return content[:277] + "..."
    elif platform_type == 'instagram':
        # Add basic hashtag optimization for Instagram
        if not any(word.startswith('#') for word in content.split()):
            # Add generic hashtags if none present
            return f"{content} #content #socialmedia"
    
    return content


def _calculate_series_duration(schedule_pattern: str, content_count: int, time_spacing: int) -> str:
    """Calculate total duration for content series."""
    if schedule_pattern == 'immediate':
        return "All posts published immediately"
    elif schedule_pattern == 'daily':
        return f"{content_count} days (daily posting)"
    elif schedule_pattern == 'weekly':
        return f"{content_count} weeks (weekly posting)"
    else:  # custom
        total_hours = (content_count - 1) * time_spacing
        if total_hours < 24:
            return f"{total_hours} hours"
        elif total_hours < 24 * 7:
            days = total_hours / 24
            return f"{days:.1f} days"
        else:
            weeks = total_hours / (24 * 7)
            return f"{weeks:.1f} weeks"


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
            "action_required": "Wait before retrying. Consider reducing batch size or frequency."
        }
    else:
        return {
            "status": "api_error",
            "error": f"Publer API error: {error_str}",
            "retry_recommended": True
        }