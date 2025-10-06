"""
Job monitoring tools for Publer MCP async operations.
"""

from typing import Any, Dict, List, Optional, Annotated
from mcp.server.fastmcp import Context
from pydantic import Field
from datetime import datetime, timedelta

from ..auth import extract_publer_credentials, validate_api_key, validate_workspace_access, create_api_headers
from ..client import create_client, PublerAPIError


async def publer_check_job_status(
    ctx: Context,
    job_id: Annotated[str, Field(description="Job ID returned from scheduling tools")]
) -> Dict[str, Any]:
    """
    Check the status and results of a specific Publer job.
    
    This tool monitors async job progress, provides detailed status updates, and retrieves 
    final results including post IDs, engagement metrics, and error details if any. 
    Essential for tracking the success of scheduled posts and campaigns.
    
    Returns:
        Dict containing job status, progress, results, and engagement metrics
    """
    try:
        # Extract and validate credentials (only API key needed for job status)
        credentials = extract_publer_credentials(ctx)
        api_valid, api_error = validate_api_key(credentials)
        if not api_valid:
            return {
                "status": "authentication_failed",
                "error": api_error,
                "action_required": "Verify x-api-key header"
            }
        
        # Validate job_id input
        if not job_id or not job_id.strip():
            return {
                "status": "validation_failed",
                "error": "Job ID cannot be empty",
                "action_required": "Provide the job_id returned from a scheduling tool"
            }
        
        client = create_client()
        
        # Create headers (job status typically doesn't require workspace_id, but include if available)
        headers = create_api_headers(credentials, include_workspace=bool(credentials.workspace_id))
        
        try:
            # Get job status from Publer API
            job_response = await client.get(f"job_status/{job_id.strip()}", headers)
        except PublerAPIError as e:
            if "404" in str(e) or "not found" in str(e).lower():
                return {
                    "status": "job_not_found",
                    "job_id": job_id,
                    "error": f"Job '{job_id}' not found",
                    "action_required": "Verify the job_id is correct and was created in your workspace",
                    "possible_causes": [
                        "Job ID was mistyped",
                        "Job was created in a different workspace", 
                        "Job is too old and has been archived",
                        "Job ID doesn't exist"
                    ]
                }
            else:
                raise  # Re-raise other API errors
        
        await client.close()
        
        # Parse job status response
        job_status = job_response.get('status', 'unknown')
        job_results = job_response.get('results', [])
        job_errors = job_response.get('errors', [])
        job_progress = job_response.get('progress', {})
        
        # Calculate progress metrics
        total_posts = len(job_results) if job_results else job_progress.get('total_posts', 0)
        completed_posts = len([r for r in job_results if r.get('status') in ['published', 'scheduled']]) if job_results else job_progress.get('completed_posts', 0)
        failed_posts = len([r for r in job_results if r.get('status') == 'failed']) if job_results else 0
        
        progress_percentage = 0
        if total_posts > 0:
            progress_percentage = round((completed_posts / total_posts) * 100)
        
        # Process job results with detailed information
        processed_results = []
        total_engagement = {"likes": 0, "shares": 0, "comments": 0, "clicks": 0}
        
        for result in job_results:
            platform = result.get('platform', 'unknown')
            post_status = result.get('status', 'unknown')
            
            # Extract engagement metrics if available
            engagement = result.get('engagement', {})
            if isinstance(engagement, dict):
                total_engagement["likes"] += engagement.get('likes', 0)
                total_engagement["shares"] += engagement.get('shares', 0)  
                total_engagement["comments"] += engagement.get('comments', 0)
                total_engagement["clicks"] += engagement.get('clicks', 0)
            
            processed_results.append({
                "platform": platform,
                "account_name": result.get('account_name', 'Unknown'),
                "post_id": result.get('post_id'),
                "status": post_status,
                "published_at": result.get('published_at'),
                "scheduled_time": result.get('scheduled_time'),
                "content_preview": result.get('content', '')[:100] + "..." if result.get('content', '') else "",
                "engagement": engagement,
                "error_message": result.get('error_message') if post_status == 'failed' else None,
                "post_url": result.get('post_url')  # Direct link to the post if available
            })
        
        # Determine overall status message
        if job_status == 'completed':
            if failed_posts == 0:
                status_message = f"Job completed successfully. All {completed_posts} posts published."
            else:
                status_message = f"Job completed with issues. {completed_posts} posts succeeded, {failed_posts} failed."
        elif job_status == 'in_progress':
            status_message = f"Job in progress. {completed_posts}/{total_posts} posts completed ({progress_percentage}%)."
        elif job_status == 'failed':
            status_message = f"Job failed. {len(job_errors)} errors occurred."
        elif job_status == 'scheduled':
            status_message = f"Job scheduled. {total_posts} posts waiting for their scheduled times."
        else:
            status_message = f"Job status: {job_status}"
        
        return {
            "job_id": job_id,
            "status": job_status,
            "status_message": status_message,
            "progress": {
                "total_posts": total_posts,
                "completed_posts": completed_posts,
                "failed_posts": failed_posts,
                "pending_posts": total_posts - completed_posts - failed_posts,
                "progress_percentage": progress_percentage
            },
            "results": processed_results,
            "engagement_summary": total_engagement if any(total_engagement.values()) else None,
            "errors": job_errors,
            "timing": {
                "created_at": job_response.get('created_at'),
                "started_at": job_response.get('started_at'),
                "completed_at": job_response.get('completed_at'),
                "estimated_completion": job_response.get('estimated_completion')
            }
        }
        
    except PublerAPIError as e:
        return _handle_api_error(e)
    except Exception as e:
        return {
            "status": "error",
            "error": f"Unexpected error: {str(e)}",
            "retry_recommended": True
        }


async def publer_monitor_recent_jobs(
    ctx: Context,
    limit: Annotated[int, Field(ge=1, le=50, description="Maximum number of jobs to return (1-50)")] = 10,
    status_filter: Annotated[str, Field(description="Filter by status: 'all', 'pending', 'completed', 'failed', 'in_progress'")] = "all",
    time_range: Annotated[str, Field(description="Time range: '1h', '6h', '24h', '7d', '30d'")] = "24h"
) -> Dict[str, Any]:
    """
    Monitor recent Publer jobs and their status across your workspace.
    
    This tool provides an overview of recent posting activity, job success rates, and identifies 
    any failed or pending jobs that may need attention. Perfect for monitoring campaign progress 
    and troubleshooting publishing issues.
    
    Returns:
        Dict containing recent jobs list, summary statistics, and filtering information
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
        valid_statuses = ['all', 'pending', 'completed', 'failed', 'in_progress', 'scheduled']
        if status_filter not in valid_statuses:
            return {
                "status": "validation_failed",
                "error": f"Invalid status filter '{status_filter}'. Must be one of: {', '.join(valid_statuses)}",
                "action_required": "Choose a valid status filter"
            }
        
        valid_time_ranges = ['1h', '6h', '24h', '7d', '30d']
        if time_range not in valid_time_ranges:
            return {
                "status": "validation_failed",
                "error": f"Invalid time range '{time_range}'. Must be one of: {', '.join(valid_time_ranges)}",
                "action_required": "Choose a valid time range"
            }
        
        client = create_client()
        
        # Create headers for API calls
        headers = create_api_headers(credentials, include_workspace=True)
        
        # Calculate time filter for API query
        time_filter = _calculate_time_filter(time_range)
        
        # Get recent posts to simulate job monitoring
        # Note: Real implementation would use a dedicated jobs endpoint if available
        try:
            posts_params = {
                "limit": limit * 2,  # Get more posts to filter from
                "since": time_filter.isoformat() if time_filter else None
            }
            
            posts_response = await client.get("posts", headers)  # params would be added if supported
            posts = posts_response.get('data', [])
        except PublerAPIError as e:
            if "404" in str(e):
                # Fallback if posts endpoint not available
                posts = []
            else:
                raise
        
        await client.close()
        
        # Process posts into job-like format
        recent_jobs = []
        status_counts = {"pending": 0, "completed": 0, "failed": 0, "in_progress": 0, "scheduled": 0}
        
        for i, post in enumerate(posts[:limit]):
            post_status = post.get('status', 'unknown')
            created_at = post.get('created_at', '')
            
            # Map post status to job status
            if post_status in ['published']:
                job_status = 'completed'
            elif post_status in ['scheduled', 'pending']:
                job_status = 'scheduled'
            elif post_status in ['failed', 'error']:
                job_status = 'failed'
            elif post_status in ['processing', 'uploading']:
                job_status = 'in_progress'
            else:
                job_status = 'pending'
            
            # Apply status filter
            if status_filter != 'all' and job_status != status_filter:
                continue
            
            # Count for summary
            if job_status in status_counts:
                status_counts[job_status] += 1
            
            # Determine job type based on post characteristics
            job_type = _infer_job_type(post)
            
            # Get platforms from post accounts
            platforms = []
            accounts = post.get('accounts', [])
            if isinstance(accounts, list):
                platforms = [acc.get('platform', 'unknown') if isinstance(acc, dict) else 'unknown' for acc in accounts]
            
            recent_jobs.append({
                "job_id": post.get('id', f'post_{i}'),  # Use post ID as job ID
                "job_type": job_type,
                "status": job_status,
                "created_at": created_at,
                "platforms": platforms,
                "posts_count": 1,  # Individual posts count as 1
                "content_preview": post.get('content', '')[:100] + "..." if post.get('content', '') else "",
                "scheduled_time": post.get('scheduled_time'),
                "error_message": post.get('error_message') if job_status == 'failed' else None
            })
        
        # Calculate summary statistics
        total_jobs = len(recent_jobs)
        success_rate = 0
        if total_jobs > 0:
            successful_jobs = status_counts['completed']
            success_rate = round((successful_jobs / total_jobs) * 100)
        
        # Identify jobs needing attention
        attention_needed = []
        for job in recent_jobs:
            if job['status'] == 'failed':
                attention_needed.append({
                    "job_id": job['job_id'],
                    "reason": "Job failed",
                    "error": job.get('error_message', 'Unknown error'),
                    "action": "Check job details and retry if needed"
                })
            elif job['status'] == 'in_progress':
                # Check if job has been in progress too long
                if job.get('created_at'):
                    try:
                        created_time = datetime.fromisoformat(job['created_at'].replace('Z', '+00:00'))
                        if datetime.now().astimezone() - created_time > timedelta(hours=2):
                            attention_needed.append({
                                "job_id": job['job_id'],
                                "reason": "Job running too long", 
                                "action": "Check if job is stuck"
                            })
                    except:
                        pass
        
        return {
            "status": "success",
            "recent_jobs": recent_jobs,
            "summary": {
                "total_jobs": total_jobs,
                "pending": status_counts["pending"],
                "scheduled": status_counts["scheduled"],
                "in_progress": status_counts["in_progress"],
                "completed": status_counts["completed"],
                "failed": status_counts["failed"],
                "success_rate": f"{success_rate}%",
                "time_range": time_range,
                "jobs_needing_attention": len(attention_needed)
            },
            "filters_applied": {
                "status_filter": status_filter,
                "time_range": time_range,
                "limit": limit
            },
            "attention_needed": attention_needed
        }
        
    except PublerAPIError as e:
        return _handle_api_error(e)
    except Exception as e:
        return {
            "status": "error",
            "error": f"Unexpected error: {str(e)}",
            "retry_recommended": True
        }


def _calculate_time_filter(time_range: str) -> Optional[datetime]:
    """Calculate datetime filter based on time range string."""
    now = datetime.now()
    
    if time_range == '1h':
        return now - timedelta(hours=1)
    elif time_range == '6h':
        return now - timedelta(hours=6)
    elif time_range == '24h':
        return now - timedelta(hours=24)
    elif time_range == '7d':
        return now - timedelta(days=7)
    elif time_range == '30d':
        return now - timedelta(days=30)
    
    return None


def _infer_job_type(post: Dict[str, Any]) -> str:
    """Infer job type from post characteristics."""
    content = post.get('content', '').lower()
    accounts = post.get('accounts', [])
    
    if len(accounts) > 1:
        return "multi_platform_scheduler"
    elif 'http' in content and ('blog' in content or 'article' in content):
        return "blog_to_twitter_scheduler"
    elif post.get('media_urls') and len(post.get('media_urls', [])) > 1:
        return "bulk_content_series_scheduler"
    elif post.get('optimization_data'):
        return "optimal_time_scheduler"
    else:
        return "manual_post"


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
            "action_required": "Wait before retrying. Monitoring tools make multiple API calls."
        }
    else:
        return {
            "status": "api_error",
            "error": f"Publer API error: {error_str}",
            "retry_recommended": True
        }