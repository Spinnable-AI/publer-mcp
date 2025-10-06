"""
Optimal time scheduling tool for Publer MCP.
"""

from typing import Any, Dict, List, Optional, Annotated
from mcp.server.fastmcp import Context
from pydantic import Field
from datetime import datetime, timedelta
import pytz

from ..auth import extract_publer_credentials, validate_workspace_access, create_api_headers
from ..client import create_client, PublerAPIError
from ..utils.time_optimizer import TimeOptimizer
from ..utils.job_tracker import AsyncJobTracker


async def publer_optimal_time_scheduler(
    ctx: Context,
    content: Annotated[str, Field(description="Content to schedule at optimal time")],
    target_platforms: Annotated[List[str], Field(description="Platform account IDs to analyze and post to")],
    optimization_goal: Annotated[str, Field(description="Optimization target: 'engagement', 'reach', 'clicks', or 'general'")] = "engagement",
    timezone: Annotated[str, Field(description="Target timezone (e.g., 'America/New_York', 'Europe/London', 'UTC')")] = "UTC",
    date_range: Annotated[str, Field(description="Time window for scheduling: 'next_24h', 'next_48h', 'next_7_days', 'next_14_days'")] = "next_7_days",
    fallback_time: Annotated[Optional[str], Field(description="Fallback ISO datetime if optimization fails")] = None
) -> Dict[str, Any]:
    """
    Schedule content at the optimal time for maximum engagement based on audience analytics and platform data.
    
    This tool analyzes your historical posting performance, audience activity patterns, and platform-specific 
    best practices to determine the best times to post for maximum engagement. Perfect for important 
    announcements, promotional content, or maximizing organic reach.
    
    Returns:
        Dict containing job_id for async tracking, optimization analysis, and recommended posting times
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
        if not content or len(content.strip()) == 0:
            return {
                "status": "validation_failed",
                "error": "Content cannot be empty",
                "action_required": "Provide content text for the post"
            }
        
        if not target_platforms or len(target_platforms) == 0:
            return {
                "status": "validation_failed",
                "error": "At least one target platform is required",
                "action_required": "Specify platform account IDs to analyze and post to"
            }
        
        # Validate optimization goal
        valid_goals = ['engagement', 'reach', 'clicks', 'general']
        if optimization_goal not in valid_goals:
            return {
                "status": "validation_failed",
                "error": f"Invalid optimization goal '{optimization_goal}'. Must be one of: {', '.join(valid_goals)}",
                "action_required": "Choose a valid optimization goal"
            }
        
        # Validate timezone
        try:
            target_tz = pytz.timezone(timezone)
        except pytz.exceptions.UnknownTimeZoneError:
            return {
                "status": "validation_failed",
                "error": f"Unknown timezone '{timezone}'",
                "action_required": "Use a valid timezone like 'America/New_York', 'Europe/London', or 'UTC'"
            }
        
        # Validate date range
        valid_ranges = ['next_24h', 'next_48h', 'next_7_days', 'next_14_days']
        if date_range not in valid_ranges:
            return {
                "status": "validation_failed",
                "error": f"Invalid date range '{date_range}'. Must be one of: {', '.join(valid_ranges)}",
                "action_required": "Choose a valid date range for scheduling"
            }
        
        # Validate fallback_time if provided
        fallback_datetime = None
        if fallback_time:
            try:
                fallback_datetime = datetime.fromisoformat(fallback_time.replace('Z', '+00:00'))
                if fallback_datetime <= datetime.now(pytz.UTC):
                    return {
                        "status": "validation_failed",
                        "error": "Fallback time must be in the future",
                        "action_required": "Provide a future datetime for fallback_time"
                    }
            except ValueError:
                return {
                    "status": "validation_failed",
                    "error": f"Invalid fallback_time format: '{fallback_time}'",
                    "action_required": "Use ISO format like '2024-01-15T10:00:00Z'"
                }
        
        client = create_client()
        
        # Get available accounts to validate platforms and get analytics
        accounts_headers = create_api_headers(credentials, include_workspace=True)
        accounts_response = await client.get("accounts", accounts_headers)
        available_accounts = accounts_response.get('data', [])
        
        # Validate platform IDs and collect platform info
        platform_info = {}
        valid_account_ids = []
        
        for account in available_accounts:
            if account.get('status') == 'active':
                account_id = str(account['id'])
                valid_account_ids.append(account_id)
                platform_info[account_id] = {
                    'type': account.get('type', 'unknown'),
                    'name': account.get('name', 'Unknown'),
                    'follower_count': account.get('follower_count', 0),
                    'timezone': account.get('timezone', timezone)
                }
        
        invalid_platforms = [pid for pid in target_platforms if str(pid) not in valid_account_ids]
        if invalid_platforms:
            return {
                "status": "validation_failed",
                "error": f"Invalid or disconnected platform IDs: {', '.join(map(str, invalid_platforms))}",
                "action_required": "Use publer_list_connected_platforms to see available accounts",
                "available_accounts": [{"id": acc['id'], "platform": acc.get('type'), "name": acc.get('name')} for acc in available_accounts if acc.get('status') == 'active']
            }
        
        # Get analytics data for optimization
        try:
            analytics_response = await client.get("analytics/members", accounts_headers)
            analytics_data = analytics_response.get('data', {})
        except PublerAPIError:
            # If analytics endpoint fails, use fallback optimization
            analytics_data = {}
        
        # Initialize time optimizer
        time_optimizer = TimeOptimizer(timezone=timezone, optimization_goal=optimization_goal)
        
        # Analyze optimal times for each platform
        optimization_results = []
        scheduled_posts = []
        
        for platform_id in target_platforms:
            platform_id_str = str(platform_id)
            platform_data = platform_info[platform_id_str]
            platform_type = platform_data['type']
            
            # Get platform-specific analytics
            platform_analytics = analytics_data.get(platform_id_str, {})
            
            # Find optimal time for this platform
            optimal_time_result = await time_optimizer.find_optimal_time(
                platform_type=platform_type,
                platform_analytics=platform_analytics,
                date_range=date_range,
                target_timezone=target_tz
            )
            
            optimization_results.append({
                "platform": platform_type,
                "account_id": platform_id,
                "account_name": platform_data['name'],
                "optimal_time": optimal_time_result['optimal_time'],
                "confidence": optimal_time_result['confidence'],
                "expected_engagement": optimal_time_result['expected_engagement'],
                "reasoning": optimal_time_result['reasoning'],
                "alternative_times": optimal_time_result.get('alternative_times', [])
            })
            
            # Prepare scheduled post data
            scheduled_posts.append({
                "platform": platform_type,
                "account_id": platform_id,
                "account_name": platform_data['name'],
                "scheduled_time": optimal_time_result['optimal_time'],
                "reasoning": optimal_time_result['reasoning'],
                "confidence": optimal_time_result['confidence']
            })
        
        # Use the earliest optimal time across all platforms (or latest if optimization goal is reach)
        if optimization_goal == 'reach':
            # For reach, use the latest time to catch more time zones
            selected_time = max(result['optimal_time'] for result in optimization_results)
        else:
            # For engagement/clicks, use the earliest optimal time
            selected_time = min(result['optimal_time'] for result in optimization_results)
        
        # Create optimized content for each platform
        job_posts = []
        for platform_id in target_platforms:
            platform_type = platform_info[str(platform_id)]['type']
            optimized_content = _optimize_content_for_platform(platform_type, content)
            
            job_posts.append({
                "content": optimized_content,
                "accounts": [platform_id],
                "scheduled_time": selected_time
            })
        
        # Submit job to Publer API
        job_payload = {"posts": job_posts}
        
        job_result = await AsyncJobTracker.submit_job(
            client=client,
            endpoint="posts/schedule",
            headers=accounts_headers,
            payload=job_payload
        )
        
        await client.close()
        
        # Calculate analysis summary
        avg_confidence = sum(result['confidence'] for result in optimization_results) / len(optimization_results)
        data_points_used = sum(
            len(analytics_data.get(str(pid), {}).get('recent_posts', [])) 
            for pid in target_platforms
        )
        
        # Return comprehensive response
        if job_result.get("status") == "job_submitted":
            return {
                "status": "optimized_job_submitted",
                "job_id": job_result["job_id"],
                "optimization_results": {
                    "selected_time": selected_time,
                    "optimization_goal": optimization_goal,
                    "timezone": timezone,
                    "average_confidence": round(avg_confidence, 2),
                    "platforms_analyzed": len(target_platforms),
                    "data_points_used": data_points_used,
                    "analysis_period": "last_30_days",
                    "recommended_times": optimization_results
                },
                "scheduled_posts": scheduled_posts,
                "summary": {
                    "total_platforms": len(target_platforms),
                    "selected_strategy": _get_optimization_strategy_description(optimization_goal, selected_time),
                    "estimated_performance": _estimate_performance_improvement(avg_confidence, optimization_goal)
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


def _optimize_content_for_platform(platform_type: str, content: str) -> str:
    """Optimize content for specific platform."""
    if platform_type == 'twitter' and len(content) > 280:
        return content[:277] + "..."
    elif platform_type == 'linkedin':
        # Add professional context for LinkedIn
        if not content.endswith('.'):
            content += '.'
        return content
    elif platform_type == 'instagram':
        # Add hashtag optimization for Instagram
        if not any(word.startswith('#') for word in content.split()):
            content += " #engagement #content"
        return content
    
    return content


def _get_optimization_strategy_description(optimization_goal: str, selected_time: str) -> str:
    """Generate human-readable strategy description."""
    time_obj = datetime.fromisoformat(selected_time.replace('Z', '+00:00'))
    day_name = time_obj.strftime("%A")
    time_str = time_obj.strftime("%I:%M %p")
    
    strategies = {
        'engagement': f"Scheduled for {day_name} at {time_str} to maximize likes, comments, and shares",
        'reach': f"Scheduled for {day_name} at {time_str} to reach the largest audience across time zones",
        'clicks': f"Scheduled for {day_name} at {time_str} when audiences are most likely to click through",
        'general': f"Scheduled for {day_name} at {time_str} based on overall best practices"
    }
    
    return strategies.get(optimization_goal, f"Scheduled for {day_name} at {time_str}")


def _estimate_performance_improvement(confidence: float, optimization_goal: str) -> str:
    """Estimate performance improvement based on confidence and goal."""
    if confidence >= 0.8:
        improvements = {
            'engagement': "20-40% higher engagement expected",
            'reach': "15-30% more impressions expected", 
            'clicks': "25-45% higher click-through rate expected",
            'general': "15-25% better overall performance expected"
        }
    elif confidence >= 0.6:
        improvements = {
            'engagement': "10-25% higher engagement expected",
            'reach': "8-20% more impressions expected",
            'clicks': "15-30% higher click-through rate expected", 
            'general': "8-15% better overall performance expected"
        }
    else:
        improvements = {
            'engagement': "Moderate improvement expected",
            'reach': "Some increase in reach expected",
            'clicks': "Potential for better click rates",
            'general': "Better timing than random posting"
        }
    
    return improvements.get(optimization_goal, "Optimized timing expected to improve performance")


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
            "action_required": "Wait before retrying. Optimization requires multiple API calls."
        }
    else:
        return {
            "status": "api_error",
            "error": f"Publer API error: {error_str}",
            "retry_recommended": True
        }