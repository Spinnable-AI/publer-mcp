"""Pydantic models for Publer API data structures."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, ConfigDict


class PostStatus(str, Enum):
    """Post status enumeration."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"


class MediaType(str, Enum):
    """Media type enumeration."""
    PHOTO = "photo"
    VIDEO = "video"
    GIF = "gif"


class Platform(str, Enum):
    """Social media platform enumeration."""
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    PINTEREST = "pinterest"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    GOOGLE_BUSINESS = "google_business"


class Account(BaseModel):
    """Publer social media account model."""
    model_config = ConfigDict(extra="allow")
    
    id: int = Field(..., description="Account ID")
    platform: Platform = Field(..., description="Social media platform")
    username: str = Field(..., description="Account username/handle")
    display_name: Optional[str] = Field(None, description="Display name")
    profile_picture: Optional[str] = Field(None, description="Profile picture URL")
    is_active: bool = Field(True, description="Whether account is active")
    created_at: Optional[datetime] = Field(None, description="Account creation date")
    updated_at: Optional[datetime] = Field(None, description="Last update date")


class MediaItem(BaseModel):
    """Publer media library item model."""
    model_config = ConfigDict(extra="allow")
    
    id: int = Field(..., description="Media item ID")
    type: MediaType = Field(..., description="Media type")
    url: str = Field(..., description="Media URL")
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail URL")
    filename: str = Field(..., description="Original filename")
    size: Optional[int] = Field(None, description="File size in bytes")
    width: Optional[int] = Field(None, description="Image/video width")
    height: Optional[int] = Field(None, description="Image/video height")
    duration: Optional[float] = Field(None, description="Video duration in seconds")
    created_at: datetime = Field(..., description="Upload date")


class PostContent(BaseModel):
    """Post content model."""
    model_config = ConfigDict(extra="allow")
    
    text: Optional[str] = Field(None, description="Post text content")
    media: List[int] = Field(default_factory=list, description="Media item IDs")
    link: Optional[str] = Field(None, description="Shared link")
    link_preview: Optional[bool] = Field(True, description="Show link preview")


class Post(BaseModel):
    """Publer post model."""
    model_config = ConfigDict(extra="allow")
    
    id: int = Field(..., description="Post ID")
    status: PostStatus = Field(..., description="Post status")
    content: PostContent = Field(..., description="Post content")
    platforms: List[Platform] = Field(..., description="Target platforms")
    accounts: List[int] = Field(..., description="Target account IDs")
    scheduled_at: Optional[datetime] = Field(None, description="Scheduled publish time")
    published_at: Optional[datetime] = Field(None, description="Actual publish time")
    created_at: datetime = Field(..., description="Post creation time")
    updated_at: datetime = Field(..., description="Last update time")
    analytics: Optional[Dict[str, Any]] = Field(None, description="Post analytics data")


class PostAnalytics(BaseModel):
    """Post analytics model."""
    model_config = ConfigDict(extra="allow")
    
    post_id: int = Field(..., description="Post ID")
    platform: Platform = Field(..., description="Platform")
    impressions: Optional[int] = Field(None, description="Total impressions")
    reach: Optional[int] = Field(None, description="Unique reach")
    engagement: Optional[int] = Field(None, description="Total engagement")
    likes: Optional[int] = Field(None, description="Likes count")
    comments: Optional[int] = Field(None, description="Comments count")
    shares: Optional[int] = Field(None, description="Shares count")
    clicks: Optional[int] = Field(None, description="Link clicks")
    saves: Optional[int] = Field(None, description="Saves count")
    updated_at: datetime = Field(..., description="Analytics last updated")


class AccountAnalytics(BaseModel):
    """Account analytics model."""
    model_config = ConfigDict(extra="allow")
    
    account_id: int = Field(..., description="Account ID")
    platform: Platform = Field(..., description="Platform")
    followers: Optional[int] = Field(None, description="Follower count")
    following: Optional[int] = Field(None, description="Following count")
    posts_count: Optional[int] = Field(None, description="Total posts")
    engagement_rate: Optional[float] = Field(None, description="Average engagement rate")
    period_start: datetime = Field(..., description="Analytics period start")
    period_end: datetime = Field(..., description="Analytics period end")
    updated_at: datetime = Field(..., description="Analytics last updated")


class CreatePostRequest(BaseModel):
    """Request model for creating a post."""
    model_config = ConfigDict(extra="allow")
    
    content: PostContent = Field(..., description="Post content")
    accounts: List[int] = Field(..., description="Target account IDs")
    scheduled_at: Optional[datetime] = Field(None, description="Schedule time (UTC)")
    
    def to_publer_format(self) -> Dict[str, Any]:
        """Convert to Publer API format."""
        data = {
            "text": self.content.text or "",
            "accounts": self.accounts,
            "media": self.content.media,
        }
        
        if self.content.link:
            data["link"] = self.content.link
            data["link_preview"] = self.content.link_preview
        
        if self.scheduled_at:
            data["scheduled_at"] = self.scheduled_at.isoformat()
        
        return data


class UpdatePostRequest(BaseModel):
    """Request model for updating a post."""
    model_config = ConfigDict(extra="allow")
    
    content: Optional[PostContent] = Field(None, description="Updated content")
    scheduled_at: Optional[datetime] = Field(None, description="Updated schedule time")
    
    def to_publer_format(self) -> Dict[str, Any]:
        """Convert to Publer API format."""
        data = {}
        
        if self.content:
            if self.content.text is not None:
                data["text"] = self.content.text
            if self.content.media:
                data["media"] = self.content.media
            if self.content.link:
                data["link"] = self.content.link
                data["link_preview"] = self.content.link_preview
        
        if self.scheduled_at:
            data["scheduled_at"] = self.scheduled_at.isoformat()
        
        return data


class PublerAPIResponse(BaseModel):
    """Base Publer API response model."""
    model_config = ConfigDict(extra="allow")
    
    success: bool = Field(True, description="Request success status")
    data: Optional[Any] = Field(None, description="Response data")
    error: Optional[str] = Field(None, description="Error message")
    errors: Optional[Dict[str, List[str]]] = Field(None, description="Validation errors")


class PaginatedResponse(BaseModel):
    """Paginated response model."""
    model_config = ConfigDict(extra="allow")
    
    data: List[Any] = Field(..., description="Response data items")
    total: int = Field(..., description="Total items count")
    page: int = Field(1, description="Current page")
    per_page: int = Field(20, description="Items per page")
    total_pages: int = Field(..., description="Total pages")
    has_more: bool = Field(False, description="Whether more pages exist")