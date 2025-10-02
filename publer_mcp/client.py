import asyncio
import time
from typing import Any, Dict, List, Optional, Union
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .settings import Settings


class PublerAPIError(Exception):
    """Base exception for Publer API errors."""
    pass


class PublerRateLimitError(PublerAPIError):
    """Raised when rate limit is exceeded."""
    pass


class PublerAuthenticationError(PublerAPIError):
    """Raised when authentication fails."""
    pass


class PublerJobTimeoutError(PublerAPIError):
    """Raised when async job times out."""
    pass


class PublerAPIClient:
    """
    Async client for Publer API with proper authentication, error handling,
    rate limiting, and asynchronous job processing support.
    """
    
    def __init__(self, api_key: str, workspace_id: str, base_url: str = "https://app.publer.com/api/v1/"):
        """
        Initialize Publer API client.
        
        Args:
            api_key: Publer API key (requires Enterprise access)
            workspace_id: Publer workspace ID (required for most operations)
            base_url: Base API URL
        """
        self.api_key = api_key
        self.workspace_id = workspace_id
        self.base_url = base_url.rstrip('/') + '/'
        
        # Rate limiting tracking
        self._rate_limit_reset = 0
        self._rate_limit_remaining = 100
        
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers=self._get_base_headers()
        )
    
    def _get_base_headers(self, include_workspace: bool = True) -> Dict[str, str]:
        """Get base headers for API requests."""
        headers = {
            "Authorization": f"Bearer-API {self.api_key}",
            "Content-Type": "application/json",
        }
        
        # Some endpoints (like /workspaces) don't need workspace ID
        if include_workspace and self.workspace_id:
            headers["Publer-Workspace-Id"] = self.workspace_id
            
        return headers
    
    def _update_rate_limit_info(self, response: httpx.Response) -> None:
        """Update rate limit tracking from response headers."""
        if "X-RateLimit-Remaining" in response.headers:
            self._rate_limit_remaining = int(response.headers["X-RateLimit-Remaining"])
        
        if "X-RateLimit-Reset" in response.headers:
            self._rate_limit_reset = int(response.headers["X-RateLimit-Reset"])
    
    def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Handle API response with proper error parsing."""
        self._update_rate_limit_info(response)
        
        if response.status_code == 401:
            raise PublerAuthenticationError("Invalid API key or insufficient permissions")
        
        if response.status_code == 403:
            raise PublerAuthenticationError("Permission denied. Check API key scopes and workspace access")
        
        if response.status_code == 429:
            reset_time = self._rate_limit_reset
            wait_time = max(0, reset_time - int(time.time()))
            raise PublerRateLimitError(
                f"Rate limit exceeded. Limit resets in {wait_time} seconds. "
                f"Current limit: 100 requests per 2 minutes."
            )
        
        if response.status_code >= 400:
            try:
                error_data = response.json()
                if "errors" in error_data and isinstance(error_data["errors"], list):
                    error_msg = "; ".join(error_data["errors"])
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
            except:
                error_msg = f"HTTP {response.status_code}: {response.text}"
            
            raise PublerAPIError(error_msg)
        
        try:
            return response.json()
        except:
            return {}
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.RequestError, PublerRateLimitError))
    )
    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, 
                  include_workspace_header: bool = True) -> Dict[str, Any]:
        """Make GET request to Publer API."""
        url = f"{self.base_url}{endpoint.lstrip('/')}"
        headers = self._get_base_headers(include_workspace=include_workspace_header)
        
        response = await self._client.get(url, params=params, headers=headers)
        return self._handle_response(response)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.RequestError, PublerRateLimitError))
    )
    async def post(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None,
                   include_workspace_header: bool = True) -> Dict[str, Any]:
        """Make POST request to Publer API."""
        url = f"{self.base_url}{endpoint.lstrip('/')}"
        headers = self._get_base_headers(include_workspace=include_workspace_header)
        
        response = await self._client.post(url, json=json_data, headers=headers)
        return self._handle_response(response)
    
    async def poll_job_status(self, job_id: str, timeout: int = 300, 
                             poll_interval: int = 2) -> Dict[str, Any]:
        """
        Poll job status until completion or timeout.
        
        Args:
            job_id: Job ID returned from async operations
            timeout: Maximum time to wait in seconds (default: 5 minutes)
            poll_interval: Seconds between status checks
            
        Returns:
            Final job result when completed
            
        Raises:
            PublerJobTimeoutError: If job doesn't complete within timeout
            PublerAPIError: If job fails or other API error occurs
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                result = await self.get(f"job_status/{job_id}")
                
                status = result.get("status")
                if status == "completed":
                    return result
                elif status == "failed":
                    error_msg = result.get("error", "Job failed without specific error message")
                    raise PublerAPIError(f"Job {job_id} failed: {error_msg}")
                
                # Job still in progress, wait before next poll
                await asyncio.sleep(poll_interval)
                
            except PublerAPIError:
                # Re-raise API errors (auth, rate limit, etc.)
                raise
            except Exception as e:
                # Log other errors but continue polling
                await asyncio.sleep(poll_interval)
        
        raise PublerJobTimeoutError(f"Job {job_id} did not complete within {timeout} seconds")
    
    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Helper function to create client from settings
def create_client_from_settings(settings: Settings) -> PublerAPIClient:
    """Create Publer API client from settings."""
    return PublerAPIClient(
        api_key=settings.publer_api_key,
        workspace_id=settings.publer_workspace_id,
        base_url=settings.publer_api_base_url
    )