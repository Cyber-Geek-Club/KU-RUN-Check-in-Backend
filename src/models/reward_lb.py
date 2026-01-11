"""
Reward Leaderboard Models
Save as: src/models/reward_lb.py
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Numeric, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
# Ensure this import matches your project structure (src.models.base or src.db.session)
from src.models.base import Base


class RewardLeaderboardConfig(Base):
    """ตารางกำหนดค่า Leaderboard"""
    __tablename__ = "reward_leaderboard_configs"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)

    # Configuration name and description
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Required completions
    required_completions = Column(Integer, default=30, nullable=False)

    # Maximum participants who can receive rewards
    max_reward_recipients = Column(Integer, default=200, nullable=False)

    # Reward tiers configuration (JSON format)
    reward_tiers = Column(JSON, nullable=False, default=list)

    # Status and timeline
    is_active = Column(Boolean, default=True, nullable=False)
    starts_at = Column(DateTime(timezone=True), nullable=False)
    ends_at = Column(DateTime(timezone=True), nullable=False)

    # When leaderboard is finalized (becomes read-only)
    finalized_at = Column(DateTime(timezone=True), nullable=True)

    # Metadata
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    event = relationship("Event")  # Removed back_populates to avoid error if Event model isn't updated
    created_by_user = relationship("User", foreign_keys=[created_by])

    # Using 'entries' to match standard naming, mapped to RewardLeaderboardEntry
    entries = relationship(
        "RewardLeaderboardEntry",
        back_populates="config",
        cascade="all, delete-orphan"
    )


class RewardLeaderboardEntry(Base):
    """ตารางรายการผู้เข้าร่วม Leaderboard"""
    __tablename__ = "reward_leaderboard_entries"

    id = Column(Integer, primary_key=True, index=True)
    config_id = Column(Integer, ForeignKey("reward_leaderboard_configs.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Completion tracking
    total_completions = Column(Integer, default=0, nullable=False)

    # Events they participated in (JSON array of event_participation IDs)
    completed_event_participations = Column(JSON, nullable=False, default=list)

    # ✅ Added: Qualification Time (Critical for sorting first-come-first-served)
    qualified_at = Column(DateTime(timezone=True), nullable=True, index=True)

    # Ranking
    rank = Column(Integer, nullable=True, index=True)

    # Reward information
    # Renamed 'rewarded_reward_id' -> 'reward_id' to match CRUD operations
    reward_id = Column(Integer, ForeignKey("rewards.id"), nullable=True)

    # ✅ Added: Reward Tier (To store "Gold", "Silver", etc.)
    reward_tier = Column(String(50), nullable=True)

    rewarded_at = Column(DateTime(timezone=True), nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    config = relationship("RewardLeaderboardConfig", back_populates="entries")
    user = relationship("User")
    reward = relationship("Reward")