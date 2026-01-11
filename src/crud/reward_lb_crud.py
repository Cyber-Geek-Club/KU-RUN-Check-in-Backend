"""
Reward Leaderboard CRUD Operations
Save as: src/crud/reward_lb_crud.py
"""
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy import func, and_, or_, desc
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import json

from src.models.reward_lb import RewardLeaderboardConfig, RewardLeaderboardEntry
from src.models.user import User
from src.models.reward import Reward
from src.models.event import Event
from src.models.event_participation import EventParticipation, ParticipationStatus
from src.schemas.reward_lb_schema import (  # ✅ เปลี่ยนชื่อ
    LeaderboardConfigCreate,
    LeaderboardConfigUpdate,
    RewardTier
)


# ========== Config CRUD ==========

async def create_leaderboard_config(
    db: AsyncSession,
    config: LeaderboardConfigCreate,
    created_by: int
) -> RewardLeaderboardConfig:
    """Create new leaderboard configuration"""
    
    # Convert reward_tiers to JSON
    tiers_json = [t.model_dump() for t in config.reward_tiers]
    
    db_config = RewardLeaderboardConfig(
        event_id=config.event_id,
        name=config.name,
        description=config.description,
        required_completions=config.required_completions,
        max_reward_recipients=config.max_reward_recipients,
        reward_tiers=tiers_json,
        starts_at=config.starts_at,
        ends_at=config.ends_at,
        created_by=created_by
    )
    
    db.add(db_config)
    await db.commit()
    await db.refresh(db_config)
    
    return db_config


async def get_leaderboard_config_by_id(
    db: AsyncSession,
    config_id: int
) -> Optional[RewardLeaderboardConfig]:
    """Get config by ID"""
    result = await db.execute(
        select(RewardLeaderboardConfig)
        .where(RewardLeaderboardConfig.id == config_id)
    )
    return result.scalar_one_or_none()


async def get_leaderboard_config_by_event(
    db: AsyncSession,
    event_id: int
) -> Optional[RewardLeaderboardConfig]:
    """Get config by event ID"""
    result = await db.execute(
        select(RewardLeaderboardConfig)
        .where(RewardLeaderboardConfig.event_id == event_id)
    )
    return result.scalar_one_or_none()


async def get_all_leaderboard_configs(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None
) -> List[RewardLeaderboardConfig]:
    """Get all configs"""
    query = select(RewardLeaderboardConfig)
    
    if is_active is not None:
        query = query.where(RewardLeaderboardConfig.is_active == is_active)
    
    query = query.offset(skip).limit(limit).order_by(RewardLeaderboardConfig.created_at.desc())
    
    result = await db.execute(query)
    return result.scalars().all()


async def update_leaderboard_config(
    db: AsyncSession,
    config_id: int,
    updates: LeaderboardConfigUpdate
) -> Optional[RewardLeaderboardConfig]:
    """Update leaderboard config"""
    config = await get_leaderboard_config_by_id(db, config_id)
    
    if not config:
        return None
    
    # Don't allow updates if finalized
    if config.finalized_at:
        raise ValueError("Cannot update finalized leaderboard")
    
    update_data = updates.model_dump(exclude_unset=True)
    
    # Convert reward_tiers to JSON if provided
    if 'reward_tiers' in update_data and update_data['reward_tiers']:
        update_data['reward_tiers'] = [t.model_dump() for t in updates.reward_tiers]
    
    for key, value in update_data.items():
        setattr(config, key, value)
    
    config.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(config)
    
    return config


async def delete_leaderboard_config(
    db: AsyncSession,
    config_id: int
) -> bool:
    """Delete leaderboard config"""
    config = await get_leaderboard_config_by_id(db, config_id)
    
    if not config:
        return False
    
    # Don't allow deletion if finalized
    if config.finalized_at:
        raise ValueError("Cannot delete finalized leaderboard")
    
    await db.delete(config)
    await db.commit()
    
    return True


# ========== Entry CRUD ==========

async def get_or_create_entry(
    db: AsyncSession,
    config_id: int,
    user_id: int
) -> RewardLeaderboardEntry:
    """Get existing entry or create new one"""
    result = await db.execute(
        select(RewardLeaderboardEntry)
        .where(
            RewardLeaderboardEntry.config_id == config_id,
            RewardLeaderboardEntry.user_id == user_id
        )
    )
    entry = result.scalar_one_or_none()
    
    if not entry:
        entry = RewardLeaderboardEntry(
            config_id=config_id,
            user_id=user_id,
            total_completions=0,
            completed_event_participations=[]
        )
        db.add(entry)
        await db.commit()
        await db.refresh(entry)
    
    return entry


async def update_entry_progress(
    db: AsyncSession,
    config_id: int,
    user_id: int,
    event_id: int
) -> Optional[RewardLeaderboardEntry]:
    """
    Update user's progress when they complete an event
    Called from event_participation_crud after completion
    """
    # Get config
    config = await get_leaderboard_config_by_id(db, config_id)
    
    if not config or not config.is_active:
        return None
    
    # Check if event is within leaderboard timeframe
    now = datetime.now(timezone.utc)
    if now < config.starts_at or now > config.ends_at:
        return None
    
    # Get all user's completed participations for this event
    result = await db.execute(
        select(EventParticipation)
        .where(
            EventParticipation.user_id == user_id,
            EventParticipation.event_id == event_id,
            EventParticipation.status == ParticipationStatus.COMPLETED
        )
        .order_by(EventParticipation.completed_at)
    )
    completions = result.scalars().all()
    
    if not completions:
        return None
    
    # Get or create entry
    entry = await get_or_create_entry(db, config_id, user_id)
    
    # Update completions
    entry.total_completions = len(completions)
    entry.completed_event_participations = [p.id for p in completions]
    
    # Check if qualified (reached required completions)
    if entry.total_completions >= config.required_completions and not entry.qualified_at:
        entry.qualified_at = datetime.now(timezone.utc)
    
    entry.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(entry)
    
    return entry


async def get_leaderboard_entries(
    db: AsyncSession,
    config_id: int,
    qualified_only: bool = False,
    skip: int = 0,
    limit: int = 1000
) -> List[RewardLeaderboardEntry]:
    """Get all entries for a leaderboard"""
    query = select(RewardLeaderboardEntry).where(
        RewardLeaderboardEntry.config_id == config_id
    )
    
    if qualified_only:
        query = query.where(RewardLeaderboardEntry.qualified_at.isnot(None))
    
    query = query.order_by(
        RewardLeaderboardEntry.rank.asc().nullsfirst(),
        RewardLeaderboardEntry.qualified_at.asc().nullsfirst()
    ).offset(skip).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


async def get_user_entry(
    db: AsyncSession,
    config_id: int,
    user_id: int
) -> Optional[RewardLeaderboardEntry]:
    """Get specific user's entry"""
    result = await db.execute(
        select(RewardLeaderboardEntry)
        .where(
            RewardLeaderboardEntry.config_id == config_id,
            RewardLeaderboardEntry.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


# ========== Ranking & Finalization ==========

async def calculate_rankings(
    db: AsyncSession,
    config_id: int
) -> int:
    """
    Calculate rankings for all qualified participants
    Returns number of participants ranked
    """
    config = await get_leaderboard_config_by_id(db, config_id)
    
    if not config:
        return 0
    
    # Get all qualified entries, ordered by qualified_at (first come first served)
    result = await db.execute(
        select(RewardLeaderboardEntry)
        .where(
            RewardLeaderboardEntry.config_id == config_id,
            RewardLeaderboardEntry.qualified_at.isnot(None)
        )
        .order_by(RewardLeaderboardEntry.qualified_at.asc())
    )
    entries = result.scalars().all()
    
    # Assign ranks
    for index, entry in enumerate(entries, start=1):
        entry.rank = index
    
    await db.commit()
    
    return len(entries)


async def assign_rewards(
    db: AsyncSession,
    config_id: int
) -> Dict[str, int]:
    """
    Assign rewards based on ranks and reward tiers
    Returns statistics
    """
    config = await get_leaderboard_config_by_id(db, config_id)
    
    if not config:
        return {"assigned": 0, "skipped": 0}
    
    # Parse reward tiers
    reward_tiers = [RewardTier(**tier) for tier in config.reward_tiers]
    
    # Get all ranked entries
    result = await db.execute(
        select(RewardLeaderboardEntry)
        .where(
            RewardLeaderboardEntry.config_id == config_id,
            RewardLeaderboardEntry.rank.isnot(None)
        )
        .order_by(RewardLeaderboardEntry.rank.asc())
    )
    entries = result.scalars().all()
    
    assigned = 0
    skipped = 0
    
    # Track how many rewards given per tier
    tier_counts = {tier.tier: 0 for tier in reward_tiers}
    
    for entry in entries:
        # Check if exceeds max recipients
        if entry.rank > config.max_reward_recipients:
            skipped += 1
            continue
        
        # Find appropriate tier
        matching_tier = None
        for tier in reward_tiers:
            if tier.min_rank <= entry.rank <= tier.max_rank:
                # Check if tier still has rewards available
                if tier_counts[tier.tier] < tier.quantity:
                    matching_tier = tier
                    break
        
        if matching_tier:
            entry.reward_id = matching_tier.reward_id
            entry.reward_tier = matching_tier.tier
            entry.rewarded_at = datetime.now(timezone.utc)
            tier_counts[matching_tier.tier] += 1
            assigned += 1
        else:
            skipped += 1
    
    await db.commit()
    
    return {
        "assigned": assigned,
        "skipped": skipped,
        "tier_distribution": tier_counts
    }


async def finalize_leaderboard(
    db: AsyncSession,
    config_id: int
) -> bool:
    """
    Finalize leaderboard - calculate ranks and assign rewards
    """
    config = await get_leaderboard_config_by_id(db, config_id)
    
    if not config:
        return False
    
    if config.finalized_at:
        raise ValueError("Leaderboard already finalized")
    
    # Step 1: Calculate rankings
    ranked_count = await calculate_rankings(db, config_id)
    
    # Step 2: Assign rewards
    reward_stats = await assign_rewards(db, config_id)
    
    # Step 3: Mark as finalized
    config.finalized_at = datetime.now(timezone.utc)
    await db.commit()
    
    return True


# ========== Statistics ==========

async def get_leaderboard_stats(
    db: AsyncSession,
    config_id: int
) -> Dict[str, Any]:
    """Get leaderboard statistics"""
    config = await get_leaderboard_config_by_id(db, config_id)
    
    if not config:
        return {}
    
    # Count entries
    result = await db.execute(
        select(
            func.count(RewardLeaderboardEntry.id).label('total'),
            func.count(RewardLeaderboardEntry.qualified_at).label('qualified'),
            func.count(RewardLeaderboardEntry.reward_id).label('rewarded')
        )
        .where(RewardLeaderboardEntry.config_id == config_id)
    )
    counts = result.first()
    
    # Calculate total slots
    reward_tiers = [RewardTier(**tier) for tier in config.reward_tiers]
    total_slots = sum(tier.quantity for tier in reward_tiers)
    remaining_slots = max(0, total_slots - (counts.rewarded or 0))
    
    return {
        "total_participants": counts.total or 0,
        "qualified_participants": counts.qualified or 0,
        "rewarded_participants": counts.rewarded or 0,
        "total_reward_slots": total_slots,
        "remaining_slots": remaining_slots,
        "is_finalized": config.finalized_at is not None,
        "finalized_at": config.finalized_at
    }