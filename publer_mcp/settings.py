from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration settings for Publer MCP server."""

    # Publer API Configuration (non-sensitive only)
    publer_api_base_url: str = Field(default="https://app.publer.com/api/v1/", description="Publer API base URL")

    # Server Configuration
    port: int = Field(default=3000, description="Server port")
    host: str = Field(default="0.0.0.0", description="Server host")
    log_level: str = Field(default="INFO", description="Log level")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
