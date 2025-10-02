"""Configuration settings for Publer MCP server.

All configuration is centralized here. Never hardcode credentials.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Server configuration
    host: str = "0.0.0.0"
    port: int = 3000
    log_level: str = "INFO"

    # Publer API configuration
    # Credentials will be extracted from request headers via Spinnable backend
    publer_api_base_url: str = "https://api.publer.io/v1"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
