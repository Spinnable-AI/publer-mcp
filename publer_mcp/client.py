"""Publer API client.

Thin wrapper around the Publer API providing:
- Authentication (credentials from request headers)
- Retry logic for transient failures
- Clear error handling
- Generic request helpers

This client should NOT contain MCP tool logic.
"""

from typing import Any, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from publer_mcp.settings import settings


class PublerAPIError(Exception):
    """Base exception for Publer API errors."""
    pass


class PublerClient:
    """HTTP client for Publer API interactions."""

    def __init__(self, api_key: str):
        """Initialize the Publer API client.
        
        Args:
            api_key: API key extracted from request headers by Spinnable backend.
        """
        self.api_key = api_key
        self.base_url = settings.publer_api_base_url
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        json: Optional[dict] = None,
    ) -> Any:
        """Make an HTTP request with retry logic.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint path
            params: Query parameters
            json: JSON request body
            
        Returns:
            Response data (parsed JSON)
            
        Raises:
            PublerAPIError: If the API returns an error response.
        """
        try:
            response = await self.client.request(
                method=method,
                url=endpoint,
                params=params,
                json=json,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise PublerAPIError(
                f"Publer API error: {e.response.status_code} - {e.response.text}"
            ) from e
        except httpx.RequestError as e:
            raise PublerAPIError(f"Request failed: {str(e)}") from e

    async def get(self, endpoint: str, params: Optional[dict] = None) -> Any:
        """GET request helper."""
        return await self._request("GET", endpoint, params=params)

    async def post(self, endpoint: str, json: Optional[dict] = None) -> Any:
        """POST request helper."""
        return await self._request("POST", endpoint, json=json)

    async def put(self, endpoint: str, json: Optional[dict] = None) -> Any:
        """PUT request helper."""
        return await self._request("PUT", endpoint, json=json)

    async def delete(self, endpoint: str) -> Any:
        """DELETE request helper."""
        return await self._request("DELETE", endpoint)
