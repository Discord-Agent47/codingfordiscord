import asyncio
import os
import sys
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

# Import command mentions utility
from utils.command_mentions import get_command_mentions

# Load environment variables from .env file
load_dotenv()

# =============================================================================
# Configuration
# =============================================================================

class Config:
    """Bot configuration loaded from environment variables."""

    DISCORD_TOKEN: str = os.getenv('DISCORD_TOKEN', '')
    BOT_PREFIX: str = os.getenv('BOT_PREFIX', '!')
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO').upper()
    COGS_DIRECTORY: Path = Path('./cogs')

    # Validation
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration."""
        if not cls.DISCORD_TOKEN:
            raise ValueError("DISCORD_TOKEN environment variable is not set!")
        return True

# =============================================================================
# Logging Setup
# =============================================================================

def setup_logging() -> logging.Logger:
    """
    Configure and return a logger with both file and console handlers.

    Returns:
        logging.Logger: Configured logger instance.
    """
    # Create logs directory if it doesn't exist
    logs_dir = Path('./logs')
    logs_dir.mkdir(exist_ok=True)

    # Generate log filename with date
    log_filename = logs_dir / f"bot_{datetime.now().strftime('%Y%m%d')}.log"

    # Configure root logger
    logger = logging.getLogger('DiscordBot')
    logger.setLevel(getattr(logging, Config.LOG_LEVEL, logging.INFO))

    # Clear existing handlers
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File handler
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, Config.LOG_LEVEL, logging.INFO))
    console_handler.setFormatter(formatter)

    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# Initialize logger
logger = setup_logging()

# =============================================================================
# Custom Exception Classes
# =============================================================================

class BotInitializationError(Exception):
    """Raised when bot initialization fails."""
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

    Attributes:
        logger: Logger instance for the bot.
        start_time: Timestamp when the bot started.
    """

    def __init__(self):
        """Initialize the bot with proper intents and settings."""
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True

        super().__init__(
            command_prefix=self._get_prefix,
            intents=intents,
            help_command=None,  # We'll implement a custom help command
            case_insensitive=True
        )

        self.logger = logger
        self.start_time: Optional[datetime] = None
        self._shutdown_requested: bool = False

    async def _get_prefix(self, bot: commands.Bot, message: discord.Message) -> str:
        """
        Dynamic prefix getter. Can be extended for per-guild prefixes.

        Args:
            bot: The bot instance.
            message: The message that triggered the command.

        Returns:
            str: The command prefix.
        """
        return Config.BOT_PREFIX

    async def setup_hook(self) -> None:
        """
        Called during bot setup to load cogs and perform initialization.

        Raises:
            BotInitializationError: If critical setup fails.
        """
        self.start_time = datetime.now()
        self.logger.info("=" * 60)
        self.logger.info("🚀 Starting bot initialization...")
        self.logger.info("=" * 60)

        # Load cogs
        await self._load_cogs()

        # Sync application commands (slash commands)
        try:
            self.logger.info("🔄 Syncing application commands...")
            await self.tree.sync()
            self.logger.info("✅ Application commands synced successfully.")
        except Exception as e:
            self.logger.error(f"❌ Failed to sync application commands: {e}")
            raise BotInitializationError(f"Command sync failed: {e}")

        # Update command mentions from the synced commands
        await self._update_command_mentions()

        self.logger.info("=" * 60)
        self.logger.info("✨ Bot initialization complete!")
        self.logger.info("=" * 60)

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

        Raises:
            BotInitializationError: If the cogs directory doesn't exist.
        """
        if not Config.COGS_DIRECTORY.exists():
            self.logger.warning(f"⚠️ Cogs directory '{Config.COGS_DIRECTORY}' does not exist. Creating it...")
            Config.COGS_DIRECTORY.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"✅ Created cogs directory at '{Config.COGS_DIRECTORY}'")
            return

        # Check for __init__.py in cogs directory
        init_file = Config.COGS_DIRECTORY / '__init__.py'
        if not init_file.exists():
            init_file.touch()
            self.logger.debug("Created __init__.py in cogs directory.")

        loaded_count = 0
        failed_count = 0

        self.logger.info("📦 Loading cogs...")

        for filepath in Config.COGS_DIRECTORY.glob('*.py'):
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
                self.logger.error(f"❌ Failed to load cog '{module_name}': {e}")
                self.logger.debug(f"Traceback:\n{error_trace}")

        self.logger.info(f"📊 Cog loading summary: {loaded_count} loaded, {failed_count} failed")

        if failed_count > 0:
            self.logger.warning("⚠️ Some cogs failed to load. Check logs for details.")

    async def on_ready(self) -> None:
        """Called when the bot has successfully connected to Discord."""
        if self.user is None:
            self.logger.error("Bot user is None after on_ready!")
            return

        uptime = datetime.now() - self.start_time if self.start_time else None

        self.logger.info("=" * 60)
        self.logger.info(f"✅ Logged in as: {self.user} (ID: {self.user.id})")
        self.logger.info(f"📈 Connected to {len(self.guilds)} guilds")
        self.logger.info(f"👥 Serving {sum(guild.member_count for guild in self.guilds)} users")
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

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        """
        Global command error handler.

        Args:
            ctx: The command context.
            error: The error that occurred.
        """
        # Ignore hidden commands errors
        if hasattr(ctx.command, 'hidden') and ctx.command.hidden:
            return

        # Handle specific error types
        if isinstance(error, commands.CommandNotFound):
            return  # Silently ignore unknown commands

        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: `{error.param.name}`", delete_after=10)

        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Invalid argument provided: {str(error)}", delete_after=10)

        elif isinstance(error, commands.MissingPermissions):
            missing_perms = ', '.join(error.missing_permissions)
            await ctx.send(f"❌ You need the following permissions: `{missing_perms}`", delete_after=10)

        elif isinstance(error, commands.BotMissingPermissions):
            missing_perms = ', '.join(error.missing_permissions)
            await ctx.send(f"❌ I need the following permissions: `{missing_perms}`", delete_after=10)

        elif isinstance(error, commands.CommandOnCooldown):
            retry_after = error.retry_after
            await ctx.send(f"⏳ This command is on cooldown. Try again in `{retry_after:.2f}` seconds.", delete_after=10)

        elif isinstance(error, commands.CheckFailure):
            await ctx.send("❌ You don't have permission to use this command.", delete_after=10)

        elif isinstance(error, commands.DisabledCommand):
            await ctx.send("❌ This command has been disabled.", delete_after=10)

        else:
            # Log unexpected errors
            self.logger.error(f"Unhandled error in command '{ctx.command}': {error}")
            self.logger.debug(f"Traceback:\n{traceback.format_exc()}")

            # Notify user
            await ctx.send(
                "❌ An unexpected error occurred. The error has been logged.",
                delete_after=10
            )

            # Optionally send error to admin/developer
            # await self._notify_admins(error, ctx)

    async def on_error(self, event_method: str, *args, **kwargs) -> None:
        """
        Global error handler for events.

        Args:
            event_method: Name of the event where the error occurred.
            args: Event arguments.
            kwargs: Event keyword arguments.
        """
        error_trace = traceback.format_exc()
        self.logger.error(f"Error in event '{event_method}':\n{error_trace}")

    async def close(self) -> None:
        """Clean up resources before closing."""
        self.logger.info("👋 Cleaning up resources...")
        await super().close()
        self.logger.info("✅ Bot shutdown complete.")

    def request_shutdown(self) -> None:
        """Request a graceful shutdown."""
        self._shutdown_requested = True
        self.logger.info("🛑 Shutdown requested.")


# =============================================================================
# Main Entry Point
# =============================================================================

def main() -> None:
    """Main entry point for the bot."""
    logger.info("🎬 Bot starting up...")

    # Validate configuration
    try:
        Config.validate()
        logger.info("✅ Configuration validated successfully.")
    except ValueError as e:
        logger.critical(f"❌ Configuration error: {e}")
        logger.critical("Please ensure DISCORD_TOKEN is set in your .env file.")
        sys.exit(1)

    # Create bot instance
    bot = ProfessionalBot()

    # Setup signal handlers for graceful shutdown
    import signal

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
        logger.info(f"🔑 Attempting to login with prefix '{Config.BOT_PREFIX}'...")
        bot.run(Config.DISCORD_TOKEN)
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
        logger.critical("Please enable the required intents in the Discord Developer Portal.")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"❌ Unexpected error during bot startup: {e}")
        logger.critical(f"Traceback:\n{traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    main()