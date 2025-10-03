import asyncio
import time
from typing import Any, Dict, Optional

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

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
    Thin HTTP wrapper for Publer API following Section 7 principles.
    
    The client must never contain MCP tool logic. Its only job is to provide 
    safe, consistent access to the API by forwarding headers and handling 
    HTTP concerns like retries and error responses.
    
    All credential validation and header construction is handled by tools
    via the auth.py module.
    """

    def __init__(self, base_url: str = None):
        """
        Initialize Publer API client.

        Args:
            base_url: Optional base API URL override
        """
        self.base_url = (base_url or settings.publer_api_base_url).rstrip("/") + "/"
        self._client = httpx.AsyncClient(timeout=30.0)

    def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """
        Handle API response with proper error parsing.
        
        This only handles HTTP-level concerns. All credential validation
        and business logic is handled in tools via auth.py.
        """
        if response.status_code == 401:
            raise PublerAuthenticationError("Invalid API key or insufficient permissions")

        if response.status_code == 403:
            raise PublerAuthenticationError("Permission denied. Check API key scopes and workspace access")

        if response.status_code == 429:
            raise PublerRateLimitError("Rate limit exceeded. Publer allows 100 requests per 2 minutes.")

        if response.status_code >= 400:
            try:
                error_data = response.json()
                if "errors" in error_data and isinstance(error_data["errors"], list):
                    error_msg = "; ".join(error_data["errors"])
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
            except Exception:
                error_msg = f"HTTP {response.status_code}: {response.text}"

            raise PublerAPIError(error_msg)

        try:
            return response.json()
        except Exception:
            return {}

    @retry(
        stop=stop_after_attempt(3), 
        wait=wait_exponential(multiplier=1, min=4, max=10), 
        retry=retry_if_exception_type((httpx.RequestError, PublerRateLimitError))
    )
    async def get(self, endpoint: str, headers: Dict[str, str], params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make GET request to Publer API with provided headers.
        
        This is a thin wrapper that forwards headers as-is. All credential
        validation and header construction is handled by tools via auth.py.
        
        Args:
            endpoint: API endpoint path
            headers: Pre-built headers from tools (containing Authorization, Publer-Workspace-Id, etc.)
            params: Query parameters
            
        Returns:
            API response data
        """
        # Build full URL
        url = f"{self.base_url}{endpoint.lstrip('/')}"
        
        # Add required Content-Type if not already present
        request_headers = {"Content-Type": "application/json", **headers}
        
        # Forward headers directly - no credential validation or modification
        response = await self._client.get(url, params=params, headers=request_headers)
        return self._handle_response(response)

    @retry(
        stop=stop_after_attempt(3), 
        wait=wait_exponential(multiplier=1, min=4, max=10), 
        retry=retry_if_exception_type((httpx.RequestError, PublerRateLimitError))
    )
    async def post(self, endpoint: str, headers: Dict[str, str], json_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make POST request to Publer API with provided headers.
        
        This is a thin wrapper that forwards headers as-is. All credential
        validation and header construction is handled by tools via auth.py.
        
        Args:
            endpoint: API endpoint path
            headers: Pre-built headers from tools (containing Authorization, Publer-Workspace-Id, etc.)
            json_data: Request body data
            
        Returns:
            API response data
        """
        # Build full URL
        url = f"{self.base_url}{endpoint.lstrip('/')}"
        
        # Add required Content-Type if not already present
        request_headers = {"Content-Type": "application/json", **headers}
        
        # Forward headers directly - no credential validation or modification
        response = await self._client.post(url, json=json_data, headers=request_headers)
        return self._handle_response(response)

    async def poll_job_status(self, job_id: str, headers: Dict[str, str], timeout: int = 300, poll_interval: int = 2) -> Dict[str, Any]:
        """
        Poll job status until completion with provided headers.
        
        This is a thin wrapper for polling. All credential validation
        and header construction is handled by tools via auth.py.
        
        Args:
            job_id: Job ID returned from async operations
            headers: Pre-built headers from tools
            timeout: Maximum time to wait in seconds
            poll_interval: Seconds between status checks
            
        Returns:
            Final job result when completed
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                result = await self.get(f"job_status/{job_id}", headers)

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
            except Exception:
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