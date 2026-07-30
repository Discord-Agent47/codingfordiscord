"""
Industry-Level Discord Bot - Main Entry Point

This bot implements production-ready patterns including:
- Structured logging with rotation
- Database persistence with SQLAlchemy
- Configuration management with Pydantic
- Service layer architecture
- Comprehensive error handling
- Health checks and monitoring
- Graceful shutdown handling

Author: Professional Bot Development Team
Version: 2.0.0
"""

from __future__ import annotations

import asyncio
import os
import sys
import signal
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Final

import discord
from discord import app_commands
from discord.ext import commands, tasks

# Import configuration
from config.settings import get_settings, BotSettings

# Import database
from database.connection import get_database_manager

# Import command mentions utility
from utils.command_mentions import get_command_mentions


# =============================================================================
# Constants
# =============================================================================

VERSION: Final[str] = "2.0.0"
BOT_NAME: Final[str] = "Professional Vouch Bot"

# =============================================================================
# Logging Setup
# =============================================================================

def setup_logging(settings: BotSettings) -> logging.Logger:
    """
    Configure and return a logger with both file and console handlers.
    
    Features:
    - Rotating file handler to prevent log files from growing too large
    - Structured logging format
    - Different log levels for file vs console
    
    Args:
        settings: Bot configuration settings
        
    Returns:
        logging.Logger: Configured logger instance.
    """
    # Create logs directory if it doesn't exist
    settings.logs_directory.mkdir(parents=True, exist_ok=True)

    # Generate log filename with date
    log_filename = settings.logs_directory / f"bot_{datetime.now().strftime('%Y%m%d')}.log"

    # Configure root logger
    logger = logging.getLogger('DiscordBot')
    logger.setLevel(getattr(logging, settings.log_level, logging.INFO))

    # Clear existing handlers to prevent duplicates on reload
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        fmt=settings.log_format,
        datefmt=settings.log_date_format
    )

    # File handler with rotation (10MB max, keep 5 backups)
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler(
        log_filename,
        encoding='utf-8',
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.log_level, logging.INFO))
    console_handler.setFormatter(formatter)

    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# =============================================================================
# Custom Exception Classes
# =============================================================================

class BotInitializationError(Exception):
    """Raised when bot initialization fails."""
    pass


class DatabaseConnectionError(Exception):
    """Raised when database connection fails."""
    pass


class CogLoadError(Exception):
    """Raised when a cog fails to load."""
    pass

# =============================================================================
# Bot Class
# =============================================================================

class ProfessionalBot(commands.Bot):
    """
    Professional Discord Bot with enhanced error handling and cog management.
    
    Features:
    - Database integration with SQLAlchemy
    - Service layer architecture
    - Comprehensive error handling
    - Health monitoring
    - Graceful shutdown
    
    Attributes:
        logger: Logger instance for the bot.
        settings: Bot configuration settings.
        start_time: Timestamp when the bot started.
        db_manager: Database manager instance.
    """

    def __init__(self, settings: BotSettings):
        """Initialize the bot with proper intents and settings."""
        intents = discord.Intents.all()  # All intents for full functionality
        
        super().__init__(
            command_prefix=self._get_prefix,
            intents=intents,
            help_command=None,  # Custom help command implemented
            case_insensitive=True,
            owner_ids=settings.owner_ids if settings.owner_ids else None
        )

        self.settings = settings
        self.logger = setup_logging(settings)
        self.start_time: Optional[datetime] = None
        self._shutdown_requested: bool = False
        self.db_manager = get_database_manager()
        
        # Health status
        self._is_healthy: bool = False
        self._last_heartbeat: Optional[datetime] = None

    async def _get_prefix(self, bot: commands.Bot, message: discord.Message) -> str:
        """
        Dynamic prefix getter. Can be extended for per-guild prefixes.
        
        Future enhancement: Load prefixes from database for per-guild customization.
        """
        return self.settings.bot_prefix

    async def setup_hook(self) -> None:
        """
        Called during bot setup to load cogs and perform initialization.
        
        This method handles:
        - Database initialization
        - Cog loading
        - Command synchronization
        - Command mentions update
        """
        self.start_time = datetime.now()
        self.logger.info("=" * 60)
        self.logger.info(f"🚀 Starting {BOT_NAME} v{VERSION} initialization...")
        self.logger.info("=" * 60)

        # Initialize database
        await self._initialize_database()

        # Load cogs
        await self._load_cogs()

        # Sync application commands (slash commands)
        try:
            self.logger.info("🔄 Syncing application commands...")
            if self.settings.guild_ids:
                # Restrict to specific guilds for testing
                self.tree.copy_global_to(guilds=[
                    discord.Object(id=gid) for gid in self.settings.guild_ids
                ])
            await self.tree.sync()
            self.logger.info("✅ Application commands synced successfully.")
        except Exception as e:
            self.logger.error(f"❌ Failed to sync application commands: {e}")
            raise BotInitializationError(f"Command sync failed: {e}")

        # Update command mentions from the synced commands
        await self._update_command_mentions()

        # Start health check task
        self._health_check_task.start()

        # Mark as healthy
        self._is_healthy = True

        self.logger.info("=" * 60)
        self.logger.info("✨ Bot initialization complete!")
        self.logger.info("=" * 60)

    async def _initialize_database(self) -> None:
        """Initialize the database and create tables."""
        try:
            self.logger.info("🗄️ Initializing database...")
            await self.db_manager.initialize()
            await self.db_manager.create_tables()
            self.logger.info("✅ Database initialized successfully.")
        except Exception as e:
            self.logger.error(f"❌ Database initialization failed: {e}")
            raise DatabaseConnectionError(f"Database connection failed: {e}")

    async def _update_command_mentions(self) -> None:
        """
        Update command mentions from the bot's registered commands.
        
        This method uses the command_mentions utility to automatically
        generate and store all slash command mentions in a JSON file.
        """
        try:
            command_mentions = get_command_mentions()
            await command_mentions.update_from_bot(self)
        except Exception as e:
            self.logger.error(f"❌ Failed to update command mentions: {e}")

    async def _load_cogs(self) -> None:
        """
        Load all cogs from the configured cogs directory.
        
        Logs detailed information about loaded and failed cogs.
        """
        if not self.settings.cogs_directory.exists():
            self.logger.warning(
                f"⚠️ Cogs directory '{self.settings.cogs_directory}' does not exist. "
                "Creating it..."
            )
            self.settings.cogs_directory.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"✅ Created cogs directory at '{self.settings.cogs_directory}'")
            return

        # Check for __init__.py in cogs directory
        init_file = self.settings.cogs_directory / '__init__.py'
        if not init_file.exists():
            init_file.touch()
            self.logger.debug("Created __init__.py in cogs directory.")

        loaded_count = 0
        failed_count = 0
        failed_cogs = []

        self.logger.info("📦 Loading cogs...")

        for filepath in sorted(self.settings.cogs_directory.glob('*.py')):
            if filepath.name.startswith('_'):
                continue  # Skip private files

            module_name = f"cogs.{filepath.stem}"

            try:
                await self.load_extension(module_name)
                loaded_count += 1
                self.logger.info(f"✅ Loaded cog: {module_name}")
            except Exception as e:
                failed_count += 1
                error_trace = traceback.format_exc()
                failed_cogs.append((module_name, str(e)))
                self.logger.error(f"❌ Failed to load cog '{module_name}': {e}")
                self.logger.debug(f"Traceback:\n{error_trace}")

        self.logger.info(
            f"📊 Cog loading summary: {loaded_count} loaded, {failed_count} failed"
        )

        if failed_cogs:
            self.logger.warning("⚠️ Failed cogs:")
            for cog_name, error in failed_cogs:
                self.logger.warning(f"   - {cog_name}: {error}")

    @tasks.loop(seconds=30)
    async def _health_check_task(self) -> None:
        """Periodic health check task."""
        self._last_heartbeat = datetime.now()
        
        # Check database connection
        if not self.db_manager.is_initialized:
            self.logger.warning("⚠️ Database not initialized!")
            self._is_healthy = False

    @_health_check_task.before_loop
    async def _before_health_check(self) -> None:
        """Wait until bot is ready before starting health checks."""
        await self.wait_until_ready()

    async def on_ready(self) -> None:
        """Called when the bot has successfully connected to Discord."""
        if self.user is None:
            self.logger.error("Bot user is None after on_ready!")
            return

        uptime = datetime.now() - self.start_time if self.start_time else None

        self.logger.info("=" * 60)
        self.logger.info(f"✅ Logged in as: {self.user} (ID: {self.user.id})")
        self.logger.info(f"📈 Connected to {len(self.guilds)} guilds")
        total_members = sum(
            guild.member_count for guild in self.guilds if guild.member_count
        )
        self.logger.info(f"👥 Serving approximately {total_members} users")
        if uptime:
            self.logger.info(f"⏱️ Startup time: {uptime.total_seconds():.2f}s")
        self.logger.info("=" * 60)

        # Set custom presence
        try:
            await self.change_presence(
                activity=discord.CustomActivity(name="💙 Helping Vouch Services")
            )
            self.logger.info("🎯 Custom status updated successfully.")
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to set custom status: {e}")

    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ) -> None:
        """
        Global command error handler.
        
        Handles various error types with appropriate user feedback.
        """
        # Ignore hidden commands errors
        if hasattr(ctx.command, 'hidden') and ctx.command.hidden:
            return

        # Handle specific error types
        if isinstance(error, commands.CommandNotFound):
            return  # Silently ignore unknown commands

        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"❌ Missing required argument: `{error.param.name}`",
                delete_after=10
            )

        elif isinstance(error, commands.BadArgument):
            await ctx.send(
                f"❌ Invalid argument provided: {str(error)}",
                delete_after=10
            )

        elif isinstance(error, commands.MissingPermissions):
            missing_perms = ', '.join(error.missing_permissions)
            await ctx.send(
                f"❌ You need the following permissions: `{missing_perms}`",
                delete_after=10
            )

        elif isinstance(error, commands.BotMissingPermissions):
            missing_perms = ', '.join(error.missing_permissions)
            await ctx.send(
                f"❌ I need the following permissions: `{missing_perms}`",
                delete_after=10
            )

        elif isinstance(error, commands.CommandOnCooldown):
            retry_after = error.retry_after
            await ctx.send(
                f"⏳ This command is on cooldown. Try again in `{retry_after:.2f}` seconds.",
                delete_after=10
            )

        elif isinstance(error, commands.CheckFailure):
            await ctx.send(
                "❌ You don't have permission to use this command.",
                delete_after=10
            )

        elif isinstance(error, commands.DisabledCommand):
            await ctx.send(
                "❌ This command has been disabled.",
                delete_after=10
            )

        else:
            # Log unexpected errors
            self.logger.error(
                f"Unhandled error in command '{ctx.command}': {error}"
            )
            self.logger.debug(f"Traceback:\n{traceback.format_exc()}")

            # Notify user
            await ctx.send(
                "❌ An unexpected error occurred. The error has been logged.",
                delete_after=10
            )

    async def on_error(self, event_method: str, *args, **kwargs) -> None:
        """
        Global error handler for events.
        
        Logs all event errors with full stack traces.
        """
        error_trace = traceback.format_exc()
        self.logger.error(f"Error in event '{event_method}':\n{error_trace}")

    async def close(self) -> None:
        """Clean up resources before closing."""
        self.logger.info("👋 Cleaning up resources...")
        
        # Stop health check task
        self._health_check_task.stop()
        
        # Close database connections
        await self.db_manager.close()
        
        self.logger.info("✅ Bot shutdown complete.")
        await super().close()

    def request_shutdown(self) -> None:
        """Request a graceful shutdown."""
        self._shutdown_requested = True
        self.logger.info("🛑 Shutdown requested.")

    @property
    def is_healthy(self) -> bool:
        """Check if the bot is in a healthy state."""
        return self._is_healthy and self.is_ready()


# =============================================================================
# Main Entry Point
# =============================================================================

def main() -> None:
    """
    Main entry point for the bot.
    
    This function handles:
    - Configuration loading and validation
    - Bot instantiation
    - Signal handler setup for graceful shutdown
    - Bot execution with proper error handling
    """
    # Load configuration
    try:
        settings = get_settings()
        print(f"✅ Configuration loaded successfully")
        print(f"   Environment: {'Production' if settings.is_production else 'Development'}")
        print(f"   Log Level: {settings.log_level}")
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("Please ensure DISCORD_TOKEN is set in your .env file.")
        sys.exit(1)
    
    # Initialize logger (will be recreated in bot, but needed for startup messages)
    logger = setup_logging(settings)
    logger.info("🎬 Bot starting up...")
    logger.info(f"📦 Version: {VERSION}")
    logger.info(f"🌍 Environment: {'Production' if settings.is_production else 'Development'}")

    # Create bot instance
    bot = ProfessionalBot(settings)

    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")
        # Schedule bot closure on the event loop
        if bot.is_ready():
            asyncio.create_task(bot.close())
        else:
            # If bot isn't ready yet, we need to stop the run loop
            raise KeyboardInterrupt()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run the bot
    try:
        logger.info(f"🔑 Attempting to login with prefix '{settings.bot_prefix}'...")
        bot.run(settings.discord_token)
    except KeyboardInterrupt:
        logger.info("🛑 Keyboard interrupt received, shutting down...")
        if bot.is_running():
            asyncio.run(bot.close())
    except discord.LoginFailure as e:
        logger.critical(f"❌ Login failed: {e}")
        logger.critical("Please check your DISCORD_TOKEN in the .env file.")
        sys.exit(1)
    except discord.PrivilegedIntentsRequired as e:
        logger.critical(f"❌ Privileged intents required: {e}")
        logger.critical(
            "Please enable the required intents in the Discord Developer Portal:\n"
            "https://discord.com/developers/applications"
        )
        sys.exit(1)
    except Exception as e:
        logger.critical(f"❌ Unexpected error during bot startup: {e}")
        logger.critical(f"Traceback:\n{traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    main()