"""Authentication handling for Publer API following Spinnable's patterns."""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class PublerAuth:
    """Handles authentication for Publer API using Spinnable's pattern."""
    
    def __init__(self, api_key: str, workspace_id: str) -> None:
        """Initialize authentication with API key and workspace ID.
        
        Args:
            api_key: Publer API key (Business plan required)
            workspace_id: Publer workspace identifier
        """
        if not api_key or not workspace_id:
            raise ValueError("API key and workspace ID are required")
        
        self.api_key = api_key
        self.workspace_id = workspace_id
        logger.info(f"Initialized Publer auth for workspace: {workspace_id[:8]}...")
    
    def get_headers(self) -> Dict[str, str]:
        """Get authentication headers following Publer API requirements.
        
        Returns:
            Dictionary of HTTP headers for API authentication
        """
        return {
            "Authorization": f"Bearer-API {self.api_key}",
            "Publer-Workspace-Id": self.workspace_id,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Spinnable-Publer-MCP/0.1.0"
        }
    
    def validate_credentials(self) -> bool:
        """Validate that credentials are properly formatted.
        
        Returns:
            True if credentials appear valid, False otherwise
        """
        if not self.api_key or len(self.api_key) < 10:
            logger.error("Invalid API key format")
            return False
        
        if not self.workspace_id or len(self.workspace_id) < 5:
            logger.error("Invalid workspace ID format")
            return False
        
        return True
    
    def get_workspace_id(self) -> str:
        """Get the current workspace ID.
        
        Returns:
            The workspace ID
        """
        return self.workspace_id
    
    def update_workspace(self, workspace_id: str) -> None:
        """Update the workspace ID for multi-workspace operations.
        
        Args:
            workspace_id: New workspace identifier
        """
        if not workspace_id:
            raise ValueError("Workspace ID cannot be empty")
        
        old_workspace = self.workspace_id[:8]
        self.workspace_id = workspace_id
        logger.info(f"Updated workspace from {old_workspace}... to {workspace_id[:8]}...")
    
    def __repr__(self) -> str:
        """String representation of auth object (without exposing credentials)."""
        return f"PublerAuth(workspace_id={self.workspace_id[:8]}...)"