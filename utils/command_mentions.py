"""
Command Mentions Utility Module

This module provides a dynamic command registry that automatically generates
and stores Discord slash command mentions. It eliminates the need for hardcoded
command IDs by maintaining a JSON file that is updated whenever commands are synced.

Usage:
    from utils.command_mentions import get_command_mention, CommandMentions
    
    # Simple usage
    embed.description = f"Use {get_command_mention('vouchsetup')} to configure."
    
    # Advanced usage with CommandMentions instance
    mentions = CommandMentions()
    await mentions.update_from_bot(bot)
    mention = mentions.get("vouch")
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

import discord
from discord import app_commands


# Configuration
COMMAND_MENTIONS_FILE = Path("./command_mentions.json")
logger = logging.getLogger(__name__)


class CommandMentions:
    """
    Manages dynamic slash command mentions for the bot.
    
    This class handles loading, saving, and updating command mentions
    from a JSON file. It ensures that command mentions always reflect
    the current state of the bot's registered commands.
    
    Attributes:
        mentions: Dictionary mapping command names to their Discord mention format.
    """
    
    def __init__(self):
        """Initialize the CommandMentions manager."""
        self.mentions: Dict[str, str] = {}
        self._load()
    
    def _load(self) -> None:
        """Load command mentions from the JSON file."""
        if COMMAND_MENTIONS_FILE.exists():
            try:
                with open(COMMAND_MENTIONS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.mentions = data.get("mentions", {})
                logger.debug(f"Loaded {len(self.mentions)} command mentions from {COMMAND_MENTIONS_FILE}")
            except (json.JSONDecodeError, IOError, KeyError) as e:
                logger.warning(f"Could not load command mentions: {e}. Starting with empty registry.")
                self.mentions = {}
        else:
            logger.info(f"Command mentions file not found. Will create on first update.")
            self.mentions = {}
    
    def _save(self) -> None:
        """Save command mentions to the JSON file."""
        try:
            COMMAND_MENTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "mentions": self.mentions
            }
            with open(COMMAND_MENTIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved {len(self.mentions)} command mentions to {COMMAND_MENTIONS_FILE}")
        except IOError as e:
            logger.error(f"Failed to save command mentions: {e}")
    
    def get(self, command_name: str) -> str:
        """
        Get the Discord mention format for a command.
        
        Args:
            command_name: The name of the command (without slash).
            
        Returns:
            The Discord mention format (e.g., </vouch:123456789>) or 
            a fallback string if the command is not found.
        """
        return self.mentions.get(command_name, f"/{command_name}")
    
    def set(self, command_name: str, command_id: int) -> str:
        """
        Set or update a command mention.
        
        Args:
            command_name: The name of the command.
            command_id: The Discord command ID.
            
        Returns:
            The Discord mention format string.
        """
        mention = f"</{command_name}:{command_id}>"
        self.mentions[command_name] = mention
        self._save()
        return mention
    
    def remove(self, command_name: str) -> bool:
        """
        Remove a command mention.
        
        Args:
            command_name: The name of the command to remove.
            
        Returns:
            True if the command was removed, False if it didn't exist.
        """
        if command_name in self.mentions:
            del self.mentions[command_name]
            self._save()
            return True
        return False
    
    async def update_from_bot(self, bot: discord.Client) -> None:
        """
        Update all command mentions from the bot's registered commands.
        
        This method fetches the current application commands from Discord,
        generates their mention formats, and updates the JSON file.
        It also removes entries for commands that no longer exist.
        
        Args:
            bot: The Discord bot instance.
        """
        logger.info("🔄 Updating command mentions from bot...")
        
        try:
            # Fetch the actual application commands from Discord to get their IDs
            if hasattr(bot, 'tree') and isinstance(bot.tree, app_commands.CommandTree):
                app_commands_list = await bot.tree.fetch_commands()
                
                # Create new mentions dictionary from current commands
                new_mentions: Dict[str, str] = {}
                
                for cmd in app_commands_list:
                    mention = f"</{cmd.name}:{cmd.id}>"
                    new_mentions[cmd.name] = mention
                
                # Compare with existing mentions
                added = set(new_mentions.keys()) - set(self.mentions.keys())
                removed = set(self.mentions.keys()) - set(new_mentions.keys())
                updated = set()
                
                for name in new_mentions:
                    if name in self.mentions and self.mentions[name] != new_mentions[name]:
                        updated.add(name)
                
                # Update internal state
                self.mentions = new_mentions
                self._save()
                
                # Log changes
                if added:
                    logger.info(f"✅ Added {len(added)} new command mentions: {', '.join(sorted(added))}")
                if removed:
                    logger.info(f"🗑️ Removed {len(removed)} obsolete command mentions: {', '.join(sorted(removed))}")
                if updated:
                    logger.info(f"🔄 Updated {len(updated)} command mentions: {', '.join(sorted(updated))}")
                
                if not added and not removed and not updated:
                    logger.info("ℹ️ No changes to command mentions.")
                
                logger.info(f"✨ Command mentions updated successfully. Total: {len(self.mentions)}")
                
            else:
                logger.warning("Bot does not have a valid command tree. Skipping command mention update.")
                
        except Exception as e:
            logger.error(f"❌ Failed to update command mentions: {e}")
            raise
    
    def clear(self) -> None:
        """Clear all command mentions."""
        self.mentions.clear()
        self._save()
    
    def __contains__(self, command_name: str) -> bool:
        """Check if a command mention exists."""
        return command_name in self.mentions
    
    def __getitem__(self, command_name: str) -> str:
        """Get a command mention using dictionary syntax."""
        return self.get(command_name)
    
    def __len__(self) -> int:
        """Return the number of registered command mentions."""
        return len(self.mentions)
    
    def items(self) -> list[tuple[str, str]]:
        """Return all command mentions as a list of (name, mention) tuples."""
        return list(self.mentions.items())
    
    def keys(self) -> list[str]:
        """Return all registered command names."""
        return list(self.mentions.keys())
    
    def values(self) -> list[str]:
        """Return all command mention strings."""
        return list(self.mentions.values())


# Global instance for convenience
_command_mentions: Optional[CommandMentions] = None


def get_command_mentions() -> CommandMentions:
    """
    Get the global CommandMentions instance.
    
    Returns:
        The global CommandMentions singleton instance.
    """
    global _command_mentions
    if _command_mentions is None:
        _command_mentions = CommandMentions()
    return _command_mentions


def get_command_mention(command_name: str) -> str:
    """
    Convenience function to get a command mention.
    
    This is the recommended way to get command mentions in your code.
    
    Args:
        command_name: The name of the command (without slash).
        
    Returns:
        The Discord mention format (e.g., </vouch:123456789>) or 
        a fallback string if the command is not found.
        
    Example:
        >>> get_command_mention("vouchsetup")
        '</vouchsetup:1529382737214177345>'
    """
    return get_command_mentions().get(command_name)


def init_command_mentions() -> CommandMentions:
    """
    Initialize the command mentions system.
    
    Call this during bot setup to ensure the global instance is created.
    
    Returns:
        The initialized CommandMentions instance.
    """
    global _command_mentions
    _command_mentions = CommandMentions()
    return _command_mentions
