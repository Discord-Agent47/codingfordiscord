"""Database Models Module

This module defines SQLAlchemy ORM models for the vouch system,
providing persistent storage with proper relationships and constraints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, BigInteger, ForeignKey, 
    Text, DateTime, Boolean, Float, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship, declarative_base


Base = declarative_base()


class GuildConfig(Base):
    """Guild-specific configuration model."""
    
    __tablename__ = "guild_configs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    guild_id = Column(BigInteger, unique=True, nullable=False, index=True)
    
    # Vouch Settings
    vouch_channel_id = Column(BigInteger, nullable=True)
    vouch_enabled = Column(Boolean, default=True, nullable=False)
    trader_role_id = Column(BigInteger, nullable=True)
    cooldown_seconds = Column(Integer, default=300, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    items = relationship("VouchItem", back_populates="guild", cascade="all, delete-orphan")
    vouches = relationship("VouchEntry", back_populates="guild", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_guild_id', 'guild_id'),
    )
    
    def __repr__(self) -> str:
        return f"<GuildConfig(guild_id={self.guild_id}, enabled={self.vouch_enabled})>"


class VouchItem(Base):
    """Custom item/service that can be vouched for."""
    
    __tablename__ = "vouch_items"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    guild_id = Column(BigInteger, ForeignKey('guild_configs.guild_id', ondelete='CASCADE'), nullable=False)
    code = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    guild = relationship("GuildConfig", back_populates="items")
    
    __table_args__ = (
        UniqueConstraint('guild_id', 'code', name='uq_guild_code'),
        Index('idx_guild_items', 'guild_id', 'name'),
    )
    
    def __repr__(self) -> str:
        return f"<VouchItem(code={self.code}, name='{self.name}')>"


class VouchEntry(Base):
    """Individual vouch/review entry."""
    
    __tablename__ = "vouch_entries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    guild_id = Column(BigInteger, ForeignKey('guild_configs.guild_id', ondelete='CASCADE'), nullable=False)
    
    # User IDs
    seller_id = Column(BigInteger, nullable=False, index=True)
    buyer_id = Column(BigInteger, nullable=False)
    vouched_by_id = Column(BigInteger, nullable=True)  # Who submitted the vouch
    
    # Vouch Details
    item_name = Column(String(255), nullable=False)
    stars = Column(Integer, nullable=False)  # 1-5
    review_text = Column(Text, nullable=True)
    image_url = Column(String(512), nullable=True)
    
    # Message tracking
    message_id = Column(BigInteger, nullable=True)
    channel_id = Column(BigInteger, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    guild = relationship("GuildConfig", back_populates="vouches")
    
    __table_args__ = (
        Index('idx_seller_guild', 'seller_id', 'guild_id'),
        Index('idx_created_at', 'created_at'),
    )
    
    def __repr__(self) -> str:
        return f"<VouchEntry(id={self.id}, seller={self.seller_id}, stars={self.stars})>"


class UserCooldown(Base):
    """Track user cooldowns for vouch submissions."""
    
    __tablename__ = "user_cooldowns"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    guild_id = Column(BigInteger, nullable=False, index=True)
    user_id = Column(BigInteger, nullable=False)
    last_vouch_timestamp = Column(Integer, nullable=False)  # Unix timestamp
    
    # Timestamps
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        UniqueConstraint('guild_id', 'user_id', name='uq_guild_user_cooldown'),
        Index('idx_user_cooldown', 'user_id', 'guild_id'),
    )
    
    def __repr__(self) -> str:
        return f"<UserCooldown(user={self.user_id}, guild={self.guild_id})>"


class VouchStats(Base):
    """Cached statistics for quick retrieval."""
    
    __tablename__ = "vouch_stats"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    guild_id = Column(BigInteger, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    
    # Statistics
    total_vouches = Column(Integer, default=0, nullable=False)
    average_rating = Column(Float, default=0.0, nullable=False)
    total_stars = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        UniqueConstraint('guild_id', 'user_id', name='uq_guild_user_stats'),
        Index('idx_stats_user', 'user_id', 'guild_id'),
    )
    
    def __repr__(self) -> str:
        return f"<VouchStats(user={self.user_id}, total={self.total_vouches}, avg={self.average_rating})>"
