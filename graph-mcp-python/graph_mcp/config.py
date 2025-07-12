"""Configuration management for Microsoft Graph MCP Server."""

import json
import os
from typing import Any, Dict, Optional

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings using Pydantic."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
        frozen=True,  # Make settings immutable
        # Allow both prefixed and direct environment variables
        env_prefix="",
    )

    def __init__(self, **kwargs):
        """Initialize settings with debug logging."""
        import os
        import logging
        
        # Set up basic logging for debugging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        
        # Debug: Show relevant environment variables
        logger.info("=== Environment Variables Debug ===")
        logger.info(f"USE_APP_REG_CLIENTID: {os.getenv('USE_APP_REG_CLIENTID', 'NOT SET')}")
        logger.info(f"TENANTID: {os.getenv('TENANTID', 'NOT SET')}")
        logger.info(f"CUSTOM_CLIENT_ID: {os.getenv('CUSTOM_CLIENT_ID', 'NOT SET')}")
        logger.info(f"CUSTOM_TENANT_ID: {os.getenv('CUSTOM_TENANT_ID', 'NOT SET')}")
        client_secret_set = bool(os.getenv('CLIENT_SECRET') or os.getenv('CUSTOM_CLIENT_SECRET') or os.getenv('GRAPH_CLIENT_SECRET'))
        logger.info(f"CLIENT_SECRET: {'SET' if client_secret_set else 'NOT SET'}")
        logger.info("====================================")
        
        super().__init__(**kwargs)

    # Application settings
    app_name: str = "graph-mcp"

    # Microsoft Graph settings for user authentication
    graph_tenant_id: Optional[str] = Field(default=None, alias="GRAPH_TENANT_ID")
    graph_client_id: str = Field(
        default="14d82eec-204b-4c2f-b7e8-296a70dab67e",  # Microsoft Graph PowerShell public client
        alias="GRAPH_CLIENT_ID"
    )
    
    # Custom app registration settings (optional - enables read/write mode)
    custom_client_id: Optional[str] = Field(default=None, alias="CUSTOM_CLIENT_ID")
    custom_tenant_id: Optional[str] = Field(default=None, alias="CUSTOM_TENANT_ID")
    custom_client_secret: Optional[str] = Field(default=None, alias="CUSTOM_CLIENT_SECRET")
    
    # Alternative environment variable names for MCP configuration
    use_app_reg_clientid: Optional[str] = Field(default=None, alias="USE_APP_REG_CLIENTID")
    tenantid: Optional[str] = Field(default=None, alias="TENANTID")
    client_secret: Optional[str] = Field(default=None, alias="CLIENT_SECRET")
    
    # Legacy naming (for backward compatibility with existing docs)
    graph_client_secret: Optional[str] = Field(default=None, alias="GRAPH_CLIENT_SECRET")
    
    # Authentication mode
    auth_mode: str = Field(default="device_code", alias="AUTH_MODE")  # "device_code" or "client_secret"

    # Microsoft Graph scopes for broad access
    graph_scopes: list[str] = Field(
        default=[
            "https://graph.microsoft.com/User.Read",
            "https://graph.microsoft.com/Mail.ReadWrite",
            "https://graph.microsoft.com/Calendars.ReadWrite",
            "https://graph.microsoft.com/Files.ReadWrite",
            "https://graph.microsoft.com/Sites.ReadWrite.All",
            "https://graph.microsoft.com/Team.ReadBasic.All",
            "https://graph.microsoft.com/Channel.ReadBasic.All",
            "https://graph.microsoft.com/ChatMessage.Send",
            "https://graph.microsoft.com/User.ReadBasic.All",
            "https://graph.microsoft.com/Group.Read.All",
            "https://graph.microsoft.com/DeviceManagementManagedDevices.ReadWrite.All",
            "https://graph.microsoft.com/DeviceManagementConfiguration.ReadWrite.All",
            "https://graph.microsoft.com/DeviceManagementApps.ReadWrite.All",
            "https://graph.microsoft.com/SecurityEvents.Read.All",
        ],
        alias="GRAPH_SCOPES"
    )

    # Operation execution settings
    operation_timeout: int = Field(
        default=300, ge=1, le=3600, alias="OPERATION_TIMEOUT"
    )  # 1 second to 1 hour
    max_concurrent_operations: int = Field(
        default=5, ge=1, le=50, alias="MAX_CONCURRENT_OPERATIONS"
    )

    # MCP settings
    mcp_server_enabled: bool = True
    mcp_server_stdio: bool = True
    mcp_server_name: str = "graph-mcp"

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_file: str = Field(default="graph_mcp.log", alias="LOG_FILE")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()

    @field_validator("graph_scopes")
    @classmethod
    def validate_graph_scopes(cls, v: list[str]) -> list[str]:
        """Validate Microsoft Graph scopes."""
        if isinstance(v, str):
            # If it's a string, split by comma
            return [scope.strip() for scope in v.split(",")]
        return v

    def get_auth_config(self) -> Dict[str, Any]:
        """Get authentication configuration."""
        # Check for MCP-style configuration first (USE_APP_REG_CLIENTID + TENANTID)
        client_id = self.use_app_reg_clientid or self.custom_client_id
        tenant_id = self.tenantid or self.custom_tenant_id
        
        # Check if custom app registration is configured
        if client_id and tenant_id:
            # Custom app registration mode (read/write)
            config = {
                "mode": "custom",
                "client_id": client_id,
                "tenant_id": tenant_id,
                "auth_mode": "client_secret",  # Always use client secret for custom apps
                "scopes": ["https://graph.microsoft.com/.default"],  # Use .default for custom apps
            }
        else:
            # Default read-only mode using Microsoft Graph PowerShell public client
            config = {
                "mode": "default",
                "client_id": self.graph_client_id,
                "tenant_id": self.graph_tenant_id or "common",
                "auth_mode": "device_code",
                "scopes": ["https://graph.microsoft.com/.default"],  # Read-only permissions
            }
        
        return config
    
    def get_client_secret(self) -> Optional[str]:
        """Get client secret from environment variables."""
        return self.client_secret or self.custom_client_secret or self.graph_client_secret
    
    @computed_field
    @property
    def is_read_only_mode(self) -> bool:
        """Check if running in read-only mode."""
        client_id = self.use_app_reg_clientid or self.custom_client_id
        tenant_id = self.tenantid or self.custom_tenant_id
        return not (client_id and tenant_id)


# Global settings instance
settings = Settings()
