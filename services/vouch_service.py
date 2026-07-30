"""Vouch Service Layer

This module provides business logic for the vouch system,
separating data access from bot commands.
"""

from __future__ import annotations

import time
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.database_models import (
    GuildConfig, VouchItem, VouchEntry, 
    UserCooldown, VouchStats
)


logger = logging.getLogger(__name__)


class VouchService:
    """
    Business logic service for vouch operations.
    
    This class handles all vouch-related operations including:
    - Guild configuration management
    - Item management
    - Vouch submission and retrieval
    - Statistics calculation
    - Cooldown management
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # =========================================================================
    # Guild Configuration Methods
    # =========================================================================
    
    async def get_guild_config(self, guild_id: int) -> Optional[GuildConfig]:
        """Get configuration for a specific guild."""
        result = await self.session.execute(
            select(GuildConfig).where(GuildConfig.guild_id == guild_id)
        )
        return result.scalar_one_or_none()
    
    async def create_guild_config(self, guild_id: int) -> GuildConfig:
        """Create a new guild configuration."""
        config = GuildConfig(guild_id=guild_id)
        self.session.add(config)
        await self.session.flush()
        return config
    
    async def get_or_create_guild_config(self, guild_id: int) -> GuildConfig:
        """Get existing config or create a new one."""
        config = await self.get_guild_config(guild_id)
        if not config:
            config = await self.create_guild_config(guild_id)
        return config
    
    async def set_vouch_channel(self, guild_id: int, channel_id: int) -> None:
        """Set the vouch channel for a guild."""
        config = await self.get_or_create_guild_config(guild_id)
        config.vouch_channel_id = channel_id
        await self.session.flush()
        logger.info(f"Set vouch channel {channel_id} for guild {guild_id}")
    
    async def toggle_vouch_enabled(self, guild_id: int, enabled: bool) -> None:
        """Enable or disable vouching for a guild."""
        config = await self.get_or_create_guild_config(guild_id)
        config.vouch_enabled = enabled
        await self.session.flush()
        logger.info(f"Vouch {'enabled' if enabled else 'disabled'} for guild {guild_id}")
    
    async def set_trader_role(self, guild_id: int, role_id: int) -> None:
        """Set the trader role for a guild."""
        config = await self.get_or_create_guild_config(guild_id)
        config.trader_role_id = role_id
        await self.session.flush()
        logger.info(f"Set trader role {role_id} for guild {guild_id}")
    
    async def remove_trader_role(self, guild_id: int) -> None:
        """Remove the trader role configuration."""
        config = await self.get_or_create_guild_config(guild_id)
        config.trader_role_id = None
        await self.session.flush()
    
    async def set_cooldown(self, guild_id: int, cooldown_seconds: int) -> None:
        """Set the vouch cooldown for a guild."""
        config = await self.get_or_create_guild_config(guild_id)
        config.cooldown_seconds = max(300, cooldown_seconds)  # Minimum 5 minutes
        await self.session.flush()
        logger.info(f"Set cooldown {cooldown_seconds}s for guild {guild_id}")
    
    # =========================================================================
    # Item Management Methods
    # =========================================================================
    
    async def get_items(self, guild_id: int) -> List[VouchItem]:
        """Get all items for a guild."""
        result = await self.session.execute(
            select(VouchItem)
            .where(VouchItem.guild_id == guild_id)
            .order_by(VouchItem.code)
        )
        return list(result.scalars().all())
    
    async def add_item(self, guild_id: int, name: str) -> Optional[int]:
        """Add a new item for a guild. Returns the assigned code or None if exists."""
        # Check if item already exists
        existing = await self.session.execute(
            select(VouchItem).where(
                VouchItem.guild_id == guild_id,
                func.lower(VouchItem.name) == func.lower(name.strip())
            )
        )
        if existing.scalar_one_or_none():
            return None
        
        # Find next available code
        result = await self.session.execute(
            select(VouchItem.code)
            .where(VouchItem.guild_id == guild_id)
            .order_by(VouchItem.code)
        )
        existing_codes = [row[0] for row in result.all()]
        
        # Find first gap
        next_code = 1
        for code in existing_codes:
            if code != next_code:
                break
            next_code += 1
        
        item = VouchItem(guild_id=guild_id, code=next_code, name=name.strip())
        self.session.add(item)
        await self.session.flush()
        
        logger.info(f"Added item '{name}' with code {next_code} for guild {guild_id}")
        return next_code
    
    async def remove_item(self, guild_id: int, code: int) -> bool:
        """Remove an item by code. Returns True if removed."""
        result = await self.session.execute(
            delete(VouchItem)
            .where(
                VouchItem.guild_id == guild_id,
                VouchItem.code == code
            )
        )
        
        if result.rowcount > 0:
            logger.info(f"Removed item with code {code} from guild {guild_id}")
            return True
        return False
    
    async def get_item_by_code(self, guild_id: int, code: int) -> Optional[str]:
        """Get item name by code."""
        result = await self.session.execute(
            select(VouchItem.name)
            .where(
                VouchItem.guild_id == guild_id,
                VouchItem.code == code
            )
        )
        return result.scalar_one_or_none()
    
    # =========================================================================
    # Vouch Operations
    # =========================================================================
    
    async def submit_vouch(
        self,
        guild_id: int,
        seller_id: int,
        buyer_id: int,
        item_name: str,
        stars: int,
        review_text: Optional[str],
        image_url: Optional[str],
        vouched_by_id: Optional[int] = None,
        message_id: Optional[int] = None,
        channel_id: Optional[int] = None
    ) -> VouchEntry:
        """Submit a new vouch entry."""
        vouch = VouchEntry(
            guild_id=guild_id,
            seller_id=seller_id,
            buyer_id=buyer_id,
            item_name=item_name,
            stars=stars,
            review_text=review_text,
            image_url=image_url,
            vouched_by_id=vouched_by_id or buyer_id,
            message_id=message_id,
            channel_id=channel_id
        )
        self.session.add(vouch)
        await self.session.flush()
        
        # Update statistics
        await self._update_stats(guild_id, seller_id)
        
        logger.info(
            f"Vouch submitted: seller={seller_id}, stars={stars}, "
            f"item={item_name} in guild {guild_id}"
        )
        return vouch
    
    async def get_vouch_count(self, guild_id: int, user_id: int) -> int:
        """Get total vouch count for a user in a guild."""
        result = await self.session.execute(
            select(func.count(VouchEntry.id))
            .where(
                VouchEntry.guild_id == guild_id,
                VouchEntry.seller_id == user_id
            )
        )
        return result.scalar() or 0
    
    async def get_recent_vouches(
        self,
        guild_id: int,
        user_id: int,
        limit: int = 5
    ) -> List[VouchEntry]:
        """Get recent vouches for a user in a guild."""
        result = await self.session.execute(
            select(VouchEntry)
            .where(
                VouchEntry.guild_id == guild_id,
                VouchEntry.seller_id == user_id
            )
            .order_by(VouchEntry.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def calculate_average_rating(
        self,
        guild_id: int,
        user_id: int
    ) -> float:
        """Calculate average rating for a user in a guild."""
        result = await self.session.execute(
            select(func.avg(VouchEntry.stars))
            .where(
                VouchEntry.guild_id == guild_id,
                VouchEntry.seller_id == user_id
            )
        )
        avg = result.scalar()
        return round(avg, 2) if avg else 0.0
    
    async def _update_stats(self, guild_id: int, user_id: int) -> None:
        """Update cached statistics for a user."""
        total_vouches = await self.get_vouch_count(guild_id, user_id)
        average_rating = await self.calculate_average_rating(guild_id, user_id)
        total_stars = int(average_rating * total_vouches) if total_vouches > 0 else 0
        
        # Upsert stats
        result = await self.session.execute(
            select(VouchStats).where(
                VouchStats.guild_id == guild_id,
                VouchStats.user_id == user_id
            )
        )
        stats = result.scalar_one_or_none()
        
        if stats:
            stats.total_vouches = total_vouches
            stats.average_rating = average_rating
            stats.total_stars = total_stars
        else:
            stats = VouchStats(
                guild_id=guild_id,
                user_id=user_id,
                total_vouches=total_vouches,
                average_rating=average_rating,
                total_stars=total_stars
            )
            self.session.add(stats)
        
        await self.session.flush()
    
    async def get_cached_stats(
        self,
        guild_id: int,
        user_id: int
    ) -> Optional[VouchStats]:
        """Get cached statistics for a user."""
        result = await self.session.execute(
            select(VouchStats).where(
                VouchStats.guild_id == guild_id,
                VouchStats.user_id == user_id
            )
        )
        return result.scalar_one_or_none()
    
    # =========================================================================
    # Cooldown Management
    # =========================================================================
    
    async def check_cooldown(self, guild_id: int, user_id: int) -> Tuple[bool, int]:
        """
        Check if user is on cooldown.
        
        Returns:
            Tuple of (is_on_cooldown, remaining_seconds)
        """
        # Get guild cooldown setting
        config = await self.get_guild_config(guild_id)
        cooldown_seconds = config.cooldown_seconds if config else 300
        
        # Get user's last vouch
        result = await self.session.execute(
            select(UserCooldown.last_vouch_timestamp)
            .where(
                UserCooldown.guild_id == guild_id,
                UserCooldown.user_id == user_id
            )
        )
        last_vouch = result.scalar_one_or_none()
        
        if not last_vouch:
            return False, 0
        
        current_time = int(time.time())
        time_since_last = current_time - last_vouch
        
        if time_since_last < cooldown_seconds:
            remaining = cooldown_seconds - time_since_last
            return True, remaining
        
        return False, 0
    
    async def set_cooldown_timestamp(self, guild_id: int, user_id: int) -> None:
        """Set the cooldown timestamp for a user."""
        result = await self.session.execute(
            select(UserCooldown).where(
                UserCooldown.guild_id == guild_id,
                UserCooldown.user_id == user_id
            )
        )
        cooldown = result.scalar_one_or_none()
        
        current_time = int(time.time())
        
        if cooldown:
            cooldown.last_vouch_timestamp = current_time
        else:
            cooldown = UserCooldown(
                guild_id=guild_id,
                user_id=user_id,
                last_vouch_timestamp=current_time
            )
            self.session.add(cooldown)
        
        await self.session.flush()
