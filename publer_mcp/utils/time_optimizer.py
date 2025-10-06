"""
Optimal posting time calculation utilities for Publer MCP.
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pytz
from dataclasses import dataclass
import statistics


@dataclass
class TimeSlot:
    """Represents a potential posting time with performance metrics."""
    datetime: datetime
    confidence: float
    expected_engagement: str
    reasoning: str
    platform_specific: bool = False


class TimeOptimizer:
    """
    Calculates optimal posting times based on analytics data and best practices.
    
    Combines historical performance data with platform-specific best practices
    to recommend optimal posting times for maximum engagement.
    """
    
    def __init__(self, timezone: str = "UTC", optimization_goal: str = "engagement"):
        """
        Initialize time optimizer.
        
        Args:
            timezone: Target timezone for optimization
            optimization_goal: 'engagement', 'reach', 'clicks', or 'general'
        """
        self.timezone = timezone
        self.optimization_goal = optimization_goal
        self.target_tz = pytz.timezone(timezone)
        
        # Platform-specific best practices (UTC times)
        self.platform_best_times = {
            'facebook': [
                (9, 0, "Morning commute engagement"),
                (13, 0, "Lunch break activity"),
                (15, 0, "Afternoon social browsing"),
                (20, 0, "Evening leisure time")
            ],
            'instagram': [
                (8, 0, "Morning coffee scroll"),
                (12, 0, "Lunch break browsing"),
                (17, 0, "After work relaxation"),
                (19, 0, "Evening prime time")
            ],
            'twitter': [
                (8, 0, "Morning news cycle"),
                (12, 0, "Lunch hour activity"),
                (17, 0, "Commute time"),
                (21, 0, "Evening discussion")
            ],
            'linkedin': [
                (7, 0, "Pre-work check"),
                (12, 0, "Professional lunch break"),
                (17, 0, "End of workday"),
                (20, 0, "Evening networking")
            ],
            'pinterest': [
                (8, 0, "Morning inspiration"),
                (13, 0, "Afternoon planning"),
                (20, 0, "Evening browsing"),
                (22, 0, "Night planning")
            ],
            'tiktok': [
                (6, 0, "Early morning scroll"),
                (9, 0, "Mid-morning break"),
                (19, 0, "Evening entertainment"),
                (21, 0, "Prime time viewing")
            ]
        }
    
    async def find_optimal_time(
        self,
        platform_type: str,
        platform_analytics: Dict[str, Any],
        date_range: str,
        target_timezone: pytz.BaseTzInfo
    ) -> Dict[str, Any]:
        """
        Find optimal posting time for a specific platform.
        
        Args:
            platform_type: Type of social platform (e.g., 'twitter', 'instagram')
            platform_analytics: Historical analytics data
            date_range: Time range for scheduling ('next_24h', 'next_7_days', etc.)
            target_timezone: Target timezone object
            
        Returns:
            Dict containing optimal time recommendation and analysis
        """
        try:
            # Analyze historical data if available
            historical_insights = self._analyze_historical_data(platform_analytics)
            
            # Get platform best practices
            platform_insights = self._get_platform_best_practices(platform_type)
            
            # Generate candidate time slots
            candidate_slots = self._generate_candidate_slots(date_range, target_timezone)
            
            # Score each candidate slot
            scored_slots = []
            for slot in candidate_slots:
                score = self._score_time_slot(
                    slot, 
                    historical_insights,
                    platform_insights,
                    platform_type
                )
                scored_slots.append((slot, score))
            
            # Sort by score and select best time
            scored_slots.sort(key=lambda x: x[1]['total_score'], reverse=True)
            
            if not scored_slots:
                return self._get_fallback_recommendation(platform_type, target_timezone)
            
            best_slot, best_score = scored_slots[0]
            
            # Generate alternative times
            alternatives = []
            for slot, score in scored_slots[1:4]:  # Top 3 alternatives
                alternatives.append({
                    "datetime": slot.isoformat(),
                    "confidence": score['confidence'],
                    "reasoning": score['reasoning']
                })
            
            return {
                "optimal_time": best_slot.isoformat(),
                "confidence": best_score['confidence'],
                "expected_engagement": self._map_score_to_engagement(best_score['total_score']),
                "reasoning": best_score['reasoning'],
                "alternative_times": alternatives,
                "analysis_factors": {
                    "historical_data_available": bool(historical_insights['data_points'] > 0),
                    "platform_best_practices": True,
                    "timezone_optimization": True,
                    "goal_optimization": self.optimization_goal
                }
            }
            
        except Exception as e:
            return self._get_fallback_recommendation(
                platform_type, 
                target_timezone, 
                error=f"Optimization error: {str(e)}"
            )
    
    def _analyze_historical_data(self, analytics_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze historical posting performance data."""
        if not analytics_data:
            return {"data_points": 0, "insights": {}}
        
        # Extract posting times and engagement metrics
        posts = analytics_data.get('recent_posts', [])
        if not posts:
            return {"data_points": 0, "insights": {}}
        
        hourly_engagement = {}
        daily_engagement = {}
        
        for post in posts:
            if not post.get('published_at') or not post.get('engagement'):
                continue
            
            try:
                # Parse posting time
                post_time = datetime.fromisoformat(post['published_at'].replace('Z', '+00:00'))
                post_time = post_time.astimezone(self.target_tz)
                
                hour = post_time.hour
                day = post_time.strftime('%A')
                
                # Get engagement score
                engagement = post.get('engagement', {})
                score = self._calculate_engagement_score(engagement)
                
                # Aggregate by hour
                if hour not in hourly_engagement:
                    hourly_engagement[hour] = []
                hourly_engagement[hour].append(score)
                
                # Aggregate by day
                if day not in daily_engagement:
                    daily_engagement[day] = []
                daily_engagement[day].append(score)
                
            except Exception:
                continue
        
        # Calculate averages and find best times
        best_hours = []
        for hour, scores in hourly_engagement.items():
            avg_score = statistics.mean(scores)
            best_hours.append((hour, avg_score, len(scores)))
        
        best_hours.sort(key=lambda x: x[1], reverse=True)
        
        best_days = []
        for day, scores in daily_engagement.items():
            avg_score = statistics.mean(scores)
            best_days.append((day, avg_score, len(scores)))
        
        best_days.sort(key=lambda x: x[1], reverse=True)
        
        return {
            "data_points": len(posts),
            "insights": {
                "best_hours": best_hours[:3],  # Top 3 hours
                "best_days": best_days[:3],    # Top 3 days
                "hourly_data": hourly_engagement,
                "daily_data": daily_engagement
            }
        }
    
    def _get_platform_best_practices(self, platform_type: str) -> Dict[str, Any]:
        """Get best practice posting times for platform."""
        platform_times = self.platform_best_times.get(platform_type.lower(), [])
        
        # Convert to target timezone
        localized_times = []
        for hour, minute, reason in platform_times:
            utc_time = datetime.now(pytz.UTC).replace(hour=hour, minute=minute, second=0, microsecond=0)
            local_time = utc_time.astimezone(self.target_tz)
            localized_times.append((local_time.hour, local_time.minute, reason))
        
        return {
            "best_times": localized_times,
            "platform": platform_type
        }
    
    def _generate_candidate_slots(self, date_range: str, target_tz: pytz.BaseTzInfo) -> List[datetime]:
        """Generate candidate time slots based on date range."""
        now = datetime.now(target_tz)
        slots = []
        
        # Define range parameters
        range_params = {
            'next_24h': (1, 2),    # 1 day, check every 2 hours
            'next_48h': (2, 3),    # 2 days, check every 3 hours
            'next_7_days': (7, 6), # 7 days, check every 6 hours
            'next_14_days': (14, 12) # 14 days, check every 12 hours
        }
        
        days, interval_hours = range_params.get(date_range, (7, 6))
        
        # Generate time slots
        current = now + timedelta(hours=1)  # Start from next hour
        end_time = now + timedelta(days=days)
        
        while current <= end_time:
            slots.append(current)
            current += timedelta(hours=interval_hours)
        
        return slots
    
    def _score_time_slot(
        self,
        slot_time: datetime,
        historical_insights: Dict[str, Any],
        platform_insights: Dict[str, Any],
        platform_type: str
    ) -> Dict[str, Any]:
        """Score a time slot based on various factors."""
        scores = []
        reasoning_parts = []
        
        # Historical data score
        historical_score = self._score_historical_performance(slot_time, historical_insights)
        if historical_score['score'] > 0:
            scores.append(historical_score['score'])
            reasoning_parts.append(historical_score['reason'])
        
        # Platform best practices score
        platform_score = self._score_platform_best_practices(slot_time, platform_insights)
        scores.append(platform_score['score'])
        reasoning_parts.append(platform_score['reason'])
        
        # Time of day score
        time_score = self._score_time_of_day(slot_time, platform_type)
        scores.append(time_score['score'])
        reasoning_parts.append(time_score['reason'])
        
        # Day of week score
        day_score = self._score_day_of_week(slot_time, platform_type)
        scores.append(day_score['score'])
        reasoning_parts.append(day_score['reason'])
        
        # Calculate total score and confidence
        total_score = sum(scores) / len(scores) if scores else 0.3
        confidence = min(0.95, max(0.1, total_score))
        
        return {
            "total_score": total_score,
            "confidence": confidence,
            "reasoning": self._create_reasoning_text(reasoning_parts, slot_time),
            "component_scores": {
                "historical": historical_score.get('score', 0) if historical_score['score'] > 0 else None,
                "platform_best_practices": platform_score['score'],
                "time_of_day": time_score['score'],
                "day_of_week": day_score['score']
            }
        }
    
    def _score_historical_performance(self, slot_time: datetime, insights: Dict[str, Any]) -> Dict[str, Any]:
        """Score based on historical performance data."""
        if insights['data_points'] == 0:
            return {"score": 0, "reason": ""}
        
        hour = slot_time.hour
        day = slot_time.strftime('%A')
        
        hourly_data = insights['insights'].get('hourly_data', {})
        daily_data = insights['insights'].get('daily_data', {})
        
        score = 0.5  # Default score
        reasons = []
        
        # Hour-based scoring
        if hour in hourly_data:
            hour_scores = hourly_data[hour]
            avg_score = statistics.mean(hour_scores)
            # Normalize to 0-1 range (assuming max engagement score is around 100)
            normalized_score = min(1.0, avg_score / 100)
            score = (score + normalized_score) / 2
            reasons.append(f"hour {hour}:00 historically performs well")
        
        # Day-based scoring
        if day in daily_data:
            day_scores = daily_data[day]
            avg_score = statistics.mean(day_scores)
            normalized_score = min(1.0, avg_score / 100)
            score = (score + normalized_score) / 2
            reasons.append(f"{day}s show good engagement")
        
        return {
            "score": score,
            "reason": " and ".join(reasons) if reasons else ""
        }
    
    def _score_platform_best_practices(self, slot_time: datetime, insights: Dict[str, Any]) -> Dict[str, Any]:
        """Score based on platform best practices."""
        hour = slot_time.hour
        minute = slot_time.minute
        
        best_times = insights.get('best_times', [])
        
        best_score = 0
        best_reason = ""
        
        for best_hour, best_minute, reason in best_times:
            # Calculate time distance (in minutes)
            time_diff = abs((hour * 60 + minute) - (best_hour * 60 + best_minute))
            
            # Score decreases with distance from optimal time
            if time_diff <= 30:  # Within 30 minutes
                score = 1.0
            elif time_diff <= 60:  # Within 1 hour
                score = 0.8
            elif time_diff <= 120: # Within 2 hours
                score = 0.6
            else:
                score = 0.3
            
            if score > best_score:
                best_score = score
                best_reason = f"aligns with {reason.lower()}"
        
        return {
            "score": best_score,
            "reason": best_reason
        }
    
    def _score_time_of_day(self, slot_time: datetime, platform_type: str) -> Dict[str, Any]:
        """Score based on general time of day patterns."""
        hour = slot_time.hour
        
        # General scoring by hour (adjusted for platform)
        if platform_type.lower() == 'linkedin':
            # LinkedIn: business hours are better
            if 7 <= hour <= 9 or 17 <= hour <= 19:
                return {"score": 0.9, "reason": "professional networking hours"}
            elif 10 <= hour <= 16:
                return {"score": 0.7, "reason": "business hours"}
            else:
                return {"score": 0.4, "reason": "outside professional hours"}
        
        elif platform_type.lower() in ['instagram', 'tiktok']:
            # Visual platforms: evening and morning peaks
            if 19 <= hour <= 21 or 8 <= hour <= 9:
                return {"score": 0.9, "reason": "prime visual content consumption"}
            elif 12 <= hour <= 13:
                return {"score": 0.8, "reason": "lunch break browsing"}
            else:
                return {"score": 0.6, "reason": "moderate activity period"}
        
        else:
            # General social media pattern
            if 8 <= hour <= 10 or 12 <= hour <= 13 or 17 <= hour <= 21:
                return {"score": 0.8, "reason": "high social media activity"}
            elif 6 <= hour <= 7 or 14 <= hour <= 16:
                return {"score": 0.6, "reason": "moderate activity"}
            else:
                return {"score": 0.4, "reason": "low activity period"}
    
    def _score_day_of_week(self, slot_time: datetime, platform_type: str) -> Dict[str, Any]:
        """Score based on day of week patterns."""
        weekday = slot_time.weekday()  # 0=Monday, 6=Sunday
        day_name = slot_time.strftime('%A')
        
        if platform_type.lower() == 'linkedin':
            # LinkedIn: weekdays are much better
            if weekday < 5:  # Monday-Friday
                return {"score": 0.9, "reason": f"{day_name} is ideal for professional content"}
            else:
                return {"score": 0.3, "reason": f"{day_name} has low professional engagement"}
        
        elif weekday in [1, 2, 3]:  # Tuesday-Thursday
            return {"score": 0.9, "reason": f"{day_name} shows peak engagement"}
        elif weekday in [0, 4]:  # Monday, Friday
            return {"score": 0.7, "reason": f"{day_name} has good engagement"}
        else:  # Weekend
            return {"score": 0.6, "reason": f"{day_name} has moderate weekend activity"}
    
    def _calculate_engagement_score(self, engagement: Dict[str, Any]) -> float:
        """Calculate engagement score from metrics."""
        likes = engagement.get('likes', 0)
        comments = engagement.get('comments', 0)
        shares = engagement.get('shares', 0)
        clicks = engagement.get('clicks', 0)
        
        # Weight different engagement types based on optimization goal
        if self.optimization_goal == 'clicks':
            return clicks * 3 + likes * 0.5 + comments * 2 + shares * 2
        elif self.optimization_goal == 'reach':
            return shares * 3 + likes * 1 + comments * 1.5 + clicks * 1
        else:  # engagement or general
            return likes * 1 + comments * 2.5 + shares * 2 + clicks * 1.5
    
    def _map_score_to_engagement(self, score: float) -> str:
        """Map numeric score to engagement expectation."""
        if score >= 0.8:
            return "high"
        elif score >= 0.6:
            return "medium-high"  
        elif score >= 0.4:
            return "medium"
        else:
            return "low-medium"
    
    def _create_reasoning_text(self, reasoning_parts: List[str], slot_time: datetime) -> str:
        """Create human-readable reasoning text."""
        day_name = slot_time.strftime('%A')
        time_str = slot_time.strftime('%I:%M %p')
        
        # Filter out empty reasoning parts
        valid_parts = [part for part in reasoning_parts if part.strip()]
        
        if not valid_parts:
            return f"Scheduled for {day_name} at {time_str} based on general best practices"
        
        reasons = ", ".join(valid_parts[:3])  # Limit to first 3 reasons
        return f"Optimal time on {day_name} at {time_str}: {reasons}"
    
    def _get_fallback_recommendation(
        self,
        platform_type: str,
        target_timezone: pytz.BaseTzInfo,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate fallback recommendation when optimization fails."""
        now = datetime.now(target_timezone)
        
        # Use platform best practices as fallback
        platform_times = self.platform_best_times.get(platform_type.lower(), [(9, 0, "morning activity")])
        best_hour, best_minute, reason = platform_times[0]
        
        # Find next occurrence of this time
        fallback_time = now.replace(hour=best_hour, minute=best_minute, second=0, microsecond=0)
        if fallback_time <= now:
            fallback_time += timedelta(days=1)
        
        return {
            "optimal_time": fallback_time.isoformat(),
            "confidence": 0.6,
            "expected_engagement": "medium",
            "reasoning": f"Fallback to {reason} based on {platform_type} best practices",
            "alternative_times": [],
            "error": error,
            "is_fallback": True
        }