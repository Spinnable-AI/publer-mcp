import asyncio
import time
from typing import Any, Dict, List, Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .settings import settings


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
    Multi-user async client for Publer API with request-scoped credentials.
    
    All credentials are extracted from request headers per the Spinnable multi-user architecture.
    Never stores credentials as instance variables.
    """
    
    def __init__(self, base_url: str = None):
        """
        Initialize Publer API client.
        
        Args:
            base_url: Optional base API URL override
        """
        self.base_url = (base_url or settings.publer_api_base_url).rstrip('/') + '/'
        self._client = httpx.AsyncClient(timeout=30.0)
    
    def _extract_credentials_from_headers(self, headers: Dict[str, str]) -> tuple[str, str]:
        """
        Extract API credentials from request headers.
        
        Args:
            headers: Request headers containing credentials
            
        Returns:
            Tuple of (api_key, workspace_id)
            
        Raises:
            PublerAuthenticationError: If required headers are missing
        """
        api_key = headers.get('x-api-key')
        workspace_id = headers.get('x-workspace-id') 
        
        if not api_key:
            raise PublerAuthenticationError("Missing x-api-key header")
            
        if not workspace_id:
            raise PublerAuthenticationError("Missing x-workspace-id header")
            
        return api_key, workspace_id
    
    def _build_request_headers(self, api_key: str, workspace_id: str, 
                              include_workspace: bool = True) -> Dict[str, str]:
        """Build headers for API request with extracted credentials."""
        request_headers = {
            "Authorization": f"Bearer-API {api_key}",
            "Content-Type": "application/json",
        }
        
        # Some endpoints (like /workspaces) don't need workspace ID
        if include_workspace and workspace_id:
            request_headers["Publer-Workspace-Id"] = workspace_id
            
        return request_headers
    
    def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Handle API response with proper error parsing."""
        if response.status_code == 401:
            raise PublerAuthenticationError("Invalid API key or insufficient permissions")
        
        if response.status_code == 403:
            raise PublerAuthenticationError("Permission denied. Check API key scopes and workspace access")
        
        if response.status_code == 429:
            raise PublerRateLimitError(
                "Rate limit exceeded. Publer allows 100 requests per 2 minutes."
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
    async def get(self, endpoint: str, request_headers: Dict[str, str],
                  params: Optional[Dict[str, Any]] = None, 
                  include_workspace_header: bool = True) -> Dict[str, Any]:
        """
        Make GET request to Publer API with request-scoped credentials.
        
        Args:
            endpoint: API endpoint path
            request_headers: Headers from incoming request (containing credentials)
            params: Query parameters
            include_workspace_header: Whether to include workspace ID header
            
        Returns:
            API response data
        """
        # Extract credentials from request headers
        api_key, workspace_id = self._extract_credentials_from_headers(request_headers)
        
        # Build API request headers
        api_headers = self._build_request_headers(
            api_key, workspace_id, include_workspace_header
        )
        
        url = f"{self.base_url}{endpoint.lstrip('/')}"
        response = await self._client.get(url, params=params, headers=api_headers)
        return self._handle_response(response)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.RequestError, PublerRateLimitError))
    )
    async def post(self, endpoint: str, request_headers: Dict[str, str],
                   json_data: Optional[Dict[str, Any]] = None,
                   include_workspace_header: bool = True) -> Dict[str, Any]:
        """
        Make POST request to Publer API with request-scoped credentials.
        
        Args:
            endpoint: API endpoint path
            request_headers: Headers from incoming request (containing credentials)
            json_data: Request body data
            include_workspace_header: Whether to include workspace ID header
            
        Returns:
            API response data
        """
        # Extract credentials from request headers
        api_key, workspace_id = self._extract_credentials_from_headers(request_headers)
        
        # Build API request headers
        api_headers = self._build_request_headers(
            api_key, workspace_id, include_workspace_header
        )
        
        url = f"{self.base_url}{endpoint.lstrip('/')}"
        response = await self._client.post(url, json=json_data, headers=api_headers)
        return self._handle_response(response)
    
    async def poll_job_status(self, job_id: str, request_headers: Dict[str, str],
                             timeout: int = 300, poll_interval: int = 2) -> Dict[str, Any]:
        """
        Poll job status until completion with request-scoped credentials.
        
        Args:
            job_id: Job ID returned from async operations
            request_headers: Headers from incoming request (containing credentials)
            timeout: Maximum time to wait in seconds
            poll_interval: Seconds between status checks
            
        Returns:
            Final job result when completed
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                result = await self.get(f"job_status/{job_id}", request_headers)
                
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


# Helper function to create client 
def create_client() -> PublerAPIClient:
    """Create Publer API client."""
    return PublerAPIClient()