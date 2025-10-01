"""Publer API client implementation with rate limiting and error handling."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import httpx
from pydantic import ValidationError

from .auth import PublerAuth
from .models import (
    Account,
    Post,
    MediaItem,
    PostAnalytics,
    AccountAnalytics,
    CreatePostRequest,
    UpdatePostRequest,
    PublerAPIResponse,
    PaginatedResponse,
    PostStatus,
    Platform
)
from ..utils.errors import (
    PublerMCPError,
    AuthenticationError,
    RateLimitError,
    NetworkError,
    ValidationError as PublerValidationError
)

logger = logging.getLogger(__name__)


class PublerAPIClient:
    """Publer API client with comprehensive error handling and rate limiting."""
    
    BASE_URL = "https://app.publer.io/api/v1"
    
    def __init__(self, auth: PublerAuth, timeout: int = 30) -> None:
        """Initialize Publer API client.
        
        Args:
            auth: PublerAuth instance with credentials
            timeout: Request timeout in seconds
        """
        self.auth = auth
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limit_remaining = 100
        self._rate_limit_reset = datetime.now()
        
        logger.info(f"Initialized Publer API client for workspace {auth.get_workspace_id()[:8]}...")
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            headers=self.auth.get_headers()
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get HTTP client instance."""
        if not self._client:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers=self.auth.get_headers()
            )
        return self._client
    
    async def _handle_rate_limiting(self) -> None:
        """Handle rate limiting with exponential backoff."""
        if self._rate_limit_remaining <= 0:
            wait_time = (self._rate_limit_reset - datetime.now()).total_seconds()
            if wait_time > 0:
                logger.warning(f"Rate limit hit, waiting {wait_time:.1f} seconds")
                await asyncio.sleep(wait_time)
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to Publer API with error handling.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request body data
            params: Query parameters
            
        Returns:
            Response data
            
        Raises:
            PublerMCPError: API error occurred
        """
        await self._handle_rate_limiting()
        
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        
        try:
            response = await self.client.request(
                method=method,
                url=url,
                json=data,
                params=params
            )
            
            # Update rate limiting info from headers
            self._rate_limit_remaining = int(response.headers.get("X-RateLimit-Remaining", "100"))
            reset_timestamp = response.headers.get("X-RateLimit-Reset")
            if reset_timestamp:
                self._rate_limit_reset = datetime.fromtimestamp(int(reset_timestamp))
            
            if response.status_code == 429:
                raise RateLimitError("API rate limit exceeded")
            
            if response.status_code == 401:
                raise AuthenticationError("Invalid API key or insufficient permissions")
            
            if response.status_code == 403:
                raise AuthenticationError("Access forbidden - check workspace permissions")
            
            if response.status_code >= 400:
                error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                error_msg = error_data.get("error", f"API error: {response.status_code}")
                raise PublerMCPError(f"API request failed: {error_msg}")
            
            response.raise_for_status()
            return response.json()
            
        except httpx.TimeoutException:
            raise NetworkError("Request timeout - Publer API did not respond in time")
        except httpx.NetworkError as e:
            raise NetworkError(f"Network error: {e}")
        except httpx.HTTPStatusError as e:
            raise PublerMCPError(f"HTTP error: {e.response.status_code}")
    
    # Account Management Methods
    
    async def list_accounts(self, platform: Optional[Platform] = None) -> List[Account]:
        """List connected social media accounts.
        
        Args:
            platform: Filter by specific platform
            
        Returns:
            List of connected accounts
        """
        params = {}
        if platform:
            params["platform"] = platform.value
        
        response_data = await self._make_request("GET", "/accounts", params=params)
        
        try:
            accounts = [Account(**account) for account in response_data.get("data", [])]
            logger.info(f"Retrieved {len(accounts)} accounts")
            return accounts
        except ValidationError as e:
            raise PublerValidationError(f"Invalid account data from API: {e}")
    
    async def get_account(self, account_id: int) -> Account:
        """Get specific account details.
        
        Args:
            account_id: Account ID
            
        Returns:
            Account details
        """
        response_data = await self._make_request("GET", f"/accounts/{account_id}")
        
        try:
            account = Account(**response_data["data"])
            logger.info(f"Retrieved account {account_id}: {account.username}")
            return account
        except ValidationError as e:
            raise PublerValidationError(f"Invalid account data from API: {e}")
    
    # Post Management Methods
    
    async def list_posts(
        self,
        status: Optional[PostStatus] = None,
        platform: Optional[Platform] = None,
        account_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 20
    ) -> List[Post]:
        """List posts with filtering options.
        
        Args:
            status: Filter by post status
            platform: Filter by platform
            account_id: Filter by account
            start_date: Filter by date range start
            end_date: Filter by date range end
            limit: Maximum posts to return
            
        Returns:
            List of posts
        """
        params = {"limit": limit}
        
        if status:
            params["status"] = status.value
        if platform:
            params["platform"] = platform.value
        if account_id:
            params["account_id"] = account_id
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()
        
        response_data = await self._make_request("GET", "/posts", params=params)
        
        try:
            posts = [Post(**post) for post in response_data.get("data", [])]
            logger.info(f"Retrieved {len(posts)} posts")
            return posts
        except ValidationError as e:
            raise PublerValidationError(f"Invalid post data from API: {e}")
    
    async def get_post(self, post_id: int) -> Post:
        """Get specific post details.
        
        Args:
            post_id: Post ID
            
        Returns:
            Post details
        """
        response_data = await self._make_request("GET", f"/posts/{post_id}")
        
        try:
            post = Post(**response_data["data"])
            logger.info(f"Retrieved post {post_id}")
            return post
        except ValidationError as e:
            raise PublerValidationError(f"Invalid post data from API: {e}")
    
    async def create_post(self, post_request: CreatePostRequest) -> Post:
        """Create a new post.
        
        Args:
            post_request: Post creation request
            
        Returns:
            Created post
        """
        data = post_request.to_publer_format()
        response_data = await self._make_request("POST", "/posts", data=data)
        
        try:
            post = Post(**response_data["data"])
            logger.info(f"Created post {post.id}")
            return post
        except ValidationError as e:
            raise PublerValidationError(f"Invalid post data from API: {e}")
    
    async def update_post(self, post_id: int, update_request: UpdatePostRequest) -> Post:
        """Update an existing post.
        
        Args:
            post_id: Post ID to update
            update_request: Post update request
            
        Returns:
            Updated post
        """
        data = update_request.to_publer_format()
        response_data = await self._make_request("PUT", f"/posts/{post_id}", data=data)
        
        try:
            post = Post(**response_data["data"])
            logger.info(f"Updated post {post_id}")
            return post
        except ValidationError as e:
            raise PublerValidationError(f"Invalid post data from API: {e}")
    
    async def delete_post(self, post_id: int) -> bool:
        """Delete a post.
        
        Args:
            post_id: Post ID to delete
            
        Returns:
            True if successful
        """
        await self._make_request("DELETE", f"/posts/{post_id}")
        logger.info(f"Deleted post {post_id}")
        return True
    
    async def schedule_post(self, post_id: int, scheduled_at: datetime) -> Post:
        """Schedule a draft post.
        
        Args:
            post_id: Post ID to schedule
            scheduled_at: Schedule datetime
            
        Returns:
            Updated post
        """
        data = {"scheduled_at": scheduled_at.isoformat()}
        response_data = await self._make_request("PUT", f"/posts/{post_id}/schedule", data=data)
        
        try:
            post = Post(**response_data["data"])
            logger.info(f"Scheduled post {post_id} for {scheduled_at}")
            return post
        except ValidationError as e:
            raise PublerValidationError(f"Invalid post data from API: {e}")
    
    # Media Management Methods
    
    async def list_media(self, media_type: Optional[str] = None, limit: int = 20) -> List[MediaItem]:
        """List media library items.
        
        Args:
            media_type: Filter by media type
            limit: Maximum items to return
            
        Returns:
            List of media items
        """
        params = {"limit": limit}
        if media_type:
            params["type"] = media_type
        
        response_data = await self._make_request("GET", "/media", params=params)
        
        try:
            media_items = [MediaItem(**item) for item in response_data.get("data", [])]
            logger.info(f"Retrieved {len(media_items)} media items")
            return media_items
        except ValidationError as e:
            raise PublerValidationError(f"Invalid media data from API: {e}")
    
    async def get_media(self, media_id: int) -> MediaItem:
        """Get specific media item details.
        
        Args:
            media_id: Media item ID
            
        Returns:
            Media item details
        """
        response_data = await self._make_request("GET", f"/media/{media_id}")
        
        try:
            media_item = MediaItem(**response_data["data"])
            logger.info(f"Retrieved media item {media_id}")
            return media_item
        except ValidationError as e:
            raise PublerValidationError(f"Invalid media data from API: {e}")
    
    async def upload_media(self, media_url: str, filename: str) -> MediaItem:
        """Upload media to library.
        
        Args:
            media_url: URL of media to upload
            filename: Original filename
            
        Returns:
            Uploaded media item
        """
        data = {"url": media_url, "filename": filename}
        response_data = await self._make_request("POST", "/media", data=data)
        
        try:
            media_item = MediaItem(**response_data["data"])
            logger.info(f"Uploaded media: {filename}")
            return media_item
        except ValidationError as e:
            raise PublerValidationError(f"Invalid media data from API: {e}")
    
    # Analytics Methods
    
    async def get_post_analytics(self, post_id: int) -> List[PostAnalytics]:
        """Get post analytics.
        
        Args:
            post_id: Post ID
            
        Returns:
            Post analytics data
        """
        response_data = await self._make_request("GET", f"/posts/{post_id}/analytics")
        
        try:
            analytics = [PostAnalytics(**item) for item in response_data.get("data", [])]
            logger.info(f"Retrieved analytics for post {post_id}")
            return analytics
        except ValidationError as e:
            raise PublerValidationError(f"Invalid analytics data from API: {e}")
    
    async def get_account_analytics(
        self,
        account_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> AccountAnalytics:
        """Get account analytics for date range.
        
        Args:
            account_id: Account ID
            start_date: Analytics period start
            end_date: Analytics period end
            
        Returns:
            Account analytics data
        """
        params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
        response_data = await self._make_request(
            "GET", f"/accounts/{account_id}/analytics", params=params
        )
        
        try:
            analytics = AccountAnalytics(**response_data["data"])
            logger.info(f"Retrieved analytics for account {account_id}")
            return analytics
        except ValidationError as e:
            raise PublerValidationError(f"Invalid analytics data from API: {e}")
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None