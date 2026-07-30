"""
Configuration Management Module

This module provides centralized configuration management using Pydantic
for validation and environment variable handling.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BotSettings(BaseSettings):
    """Bot configuration loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Discord Configuration
    discord_token: str = Field(..., description="Discord bot token")
    bot_prefix: str = Field(default="!", description="Command prefix for text commands")
    client_id: Optional[int] = Field(default=None, description="Discord application client ID")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        description="Log format string"
    )
    log_date_format: str = Field(
        default="%Y-%m-%d %H:%M:%S",
        description="Log date format string"
    )
    
    # Database Configuration
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/bot_database.db",
        description="Database connection URL"
    )
    use_sqlite: bool = Field(
        default=True,
        description="Use SQLite instead of configured database (for development)"
    )
    
    # Bot Behavior
    owner_ids: List[int] = Field(
        default_factory=list,
        description="List of Discord user IDs that are bot owners"
    )
    guild_ids: Optional[List[int]] = Field(
        default=None,
        description="Restrict slash commands to specific guilds (for testing)"
    )
    
    # Feature Flags
    enable_vouch_system: bool = Field(default=True, description="Enable vouch system")
    enable_trader_vouch: bool = Field(default=True, description="Enable trader vouch feature")
    default_cooldown_seconds: int = Field(
        default=300,
        ge=60,
        description="Default cooldown between vouch submissions in seconds"
    )
    min_cooldown_seconds: int = Field(
        default=300,
        ge=60,
        description="Minimum allowed cooldown in seconds"
    )
    
    # Paths
    data_directory: Path = Field(
        default=Path("./data"),
        description="Directory for storing bot data"
    )
    logs_directory: Path = Field(
        default=Path("./logs"),
        description="Directory for storing log files"
    )
    
    @field_validator('discord_token')
    @classmethod
    def validate_token(cls, v: str) -> str:
        if not v or len(v) < 10:
            raise ValueError("DISCORD_TOKEN must be a valid Discord bot token")
        return v
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v_upper
    
    @property
    def cogs_directory(self) -> Path:
        """Get the cogs directory path."""
        return Path("./cogs")
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return os.getenv("BOT_ENVIRONMENT", "development").lower() == "production"


# Global settings instance
_settings: Optional[BotSettings] = None


def get_settings() -> BotSettings:
    """
    Get the global bot settings instance.
    
    Returns:
        BotSettings: The validated bot configuration.
        
    Raises:
        ValueError: If required configuration is missing.
    """
    global _settings
    if _settings is None:
        try:
            _settings = BotSettings()
        except Exception as e:
            raise ValueError(f"Failed to load bot settings: {e}")
    return _settings


def reload_settings() -> BotSettings:
    """Reload settings from environment variables."""
    global _settings
    _settings = BotSettings()
    return _settings
