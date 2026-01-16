"""
Reward Leaderboard CRUD Operations - Final Version (Greenlet Fixed)
Save as: src/crud/reward_lb_crud.py
"""
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import func
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import logging

from src.models.reward_lb import RewardLeaderboardConfig, RewardLeaderboardEntry
from src.models.event_participation import EventParticipation, ParticipationStatus
from src.schemas.reward_lb_schema import (
    LeaderboardConfigCreate,
    LeaderboardConfigUpdate,
    RewardTier
)

logger = logging.getLogger(__name__)

# ==========================================
# 1. Config CRUD
# ==========================================

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

    if config.finalized_at:
        raise ValueError("Cannot update finalized leaderboard")

    update_data = updates.model_dump(exclude_unset=True)

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

    if config.finalized_at:
        raise ValueError("Cannot delete finalized leaderboard")

    await db.delete(config)
    await db.commit()

    return True


# ==========================================
# 2. Entry CRUD
# ==========================================

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
    """Update user's progress"""
    config = await get_leaderboard_config_by_id(db, config_id)

    if not config or not config.is_active:
        return None

    if config.finalized_at:
        return None

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

    entry = await get_or_create_entry(db, config_id, user_id)

    entry.total_completions = len(completions)
    entry.completed_event_participations = [p.id for p in completions]

    # Check minimum requirement
    reward_tiers = [RewardTier(**tier) for tier in config.reward_tiers]
    min_required = config.required_completions

    for tier in reward_tiers:
        tier_required = tier.required_completions if tier.required_completions is not None else config.required_completions
        min_required = min(min_required, tier_required)

    if entry.total_completions >= min_required and not entry.qualified_at:
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
        query = query.where(RewardLeaderboardEntry.rank.isnot(None))

    query = query.order_by(
        RewardLeaderboardEntry.rank.asc().nullslast(),
        RewardLeaderboardEntry.total_completions.desc()
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


# ==========================================
# 3. CORE LOGIC: Dynamic Reward Allocation
# ==========================================

async def calculate_and_allocate_rewards(
    db: AsyncSession,
    config_id: int
) -> Dict[str, Any]:
    """
    🔥 Core function for 'Dynamic Priority Reallocation' (Steal Logic)
    """
    # 1. Get Config & Tiers
    config = await get_leaderboard_config_by_id(db, config_id)
    if not config:
        raise ValueError("Leaderboard config not found")

    # ✅ FIX: Extract scalar values to variables (avoid accessing ORM inside lambda/loop)
    default_required_completions = config.required_completions
    global_inventory = config.max_reward_recipients

    raw_tiers = config.reward_tiers
    tiers = [RewardTier(**t) for t in raw_tiers]

    # Sort Tiers by Difficulty (Higher Req = Higher Priority)
    # ✅ Safe Sort: Using extracted variable 'default_required_completions'
    tiers.sort(
        key=lambda x: x.required_completions if x.required_completions is not None else default_required_completions,
        reverse=True
    )

    # 2. Get All Entries
    result = await db.execute(
        select(RewardLeaderboardEntry)
        .where(RewardLeaderboardEntry.config_id == config_id)
    )
    entries = result.scalars().all()

    qualified_users = []

    # 3. Evaluate each user
    for entry in entries:
        best_tier = None

        # Safe extraction of entry data
        entry_completions = entry.total_completions

        # Check against all tiers (sorted High -> Low)
        for tier in tiers:
            tier_req = tier.required_completions if tier.required_completions is not None else default_required_completions

            if entry_completions >= tier_req:
                best_tier = tier
                break

        if best_tier:
            q_time = entry.qualified_at or entry.updated_at or datetime.now(timezone.utc)

            # Priority Score (Higher is better)
            priority_score = best_tier.required_completions if best_tier.required_completions is not None else default_required_completions

            qualified_users.append({
                "entry": entry,
                "tier": best_tier,
                "priority_score": priority_score,
                "qualified_at": q_time
            })
        else:
            # Reset status
            entry.rank = None
            entry.reward_id = None
            entry.reward_tier = None

    # 4. Sort (The "Steal" Logic)
    # Sort by Priority (High->Low), then Time (Old->New)
    qualified_users.sort(key=lambda x: (-x["priority_score"], x["qualified_at"]))

    # 5. Allocate
    stats = {
        "total_qualified": len(qualified_users),
        "awarded": 0,
        "waitlisted": 0,
        "tier_distribution": {str(t.tier): 0 for t in tiers}
    }

    current_rank = 1

    for item in qualified_users:
        entry = item["entry"]
        tier = item["tier"]

        if current_rank <= global_inventory:
            # ✅ AWARDED
            entry.rank = current_rank
            entry.reward_id = tier.reward_id
            entry.reward_tier = str(tier.tier)

            if not entry.rewarded_at:
                entry.rewarded_at = datetime.now(timezone.utc)

            stats["awarded"] += 1
            if str(tier.tier) in stats["tier_distribution"]:
                stats["tier_distribution"][str(tier.tier)] += 1
        else:
            # ❌ WAITLIST
            entry.rank = current_rank
            entry.reward_id = None
            entry.reward_tier = "WAITLIST"

            stats["waitlisted"] += 1

        current_rank += 1

    await db.commit()
    return stats


async def finalize_leaderboard(
    db: AsyncSession,
    config_id: int
) -> bool:
    """Finalize leaderboard"""
    config = await get_leaderboard_config_by_id(db, config_id)
    if not config:
        return False

    if config.finalized_at:
        raise ValueError("Leaderboard already finalized")

    await calculate_and_allocate_rewards(db, config_id)

    config.finalized_at = datetime.now(timezone.utc)
    await db.commit()

    return True


# ==========================================
# 4. Statistics & User Status
# ==========================================

async def get_leaderboard_stats(db: AsyncSession, config_id: int) -> Dict[str, Any]:
    config = await get_leaderboard_config_by_id(db, config_id)
    if not config: return {}

    result = await db.execute(
        select(
            func.count(RewardLeaderboardEntry.id).label('total'),
            func.count(RewardLeaderboardEntry.qualified_at).label('qualified'),
            func.count(RewardLeaderboardEntry.reward_id).label('rewarded')
        ).where(RewardLeaderboardEntry.config_id == config_id)
    )
    counts = result.first()

    return {
        "total_participants": counts.total or 0,
        "qualified_participants": counts.qualified or 0,
        "rewarded_participants": counts.rewarded or 0,
        "total_reward_slots": config.max_reward_recipients,
        "remaining_slots": max(0, config.max_reward_recipients - (counts.rewarded or 0)),
        "is_finalized": config.finalized_at is not None,
        "finalized_at": config.finalized_at
    }

async def get_user_event_status(db: AsyncSession, user_id: int, event_id: int) -> Optional[Dict[str, Any]]:
    from src.models.event import Event
    from src.models.user import User
    from decimal import Decimal

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    event = (await db.execute(select(Event).where(Event.id == event_id))).scalar_one_or_none()
    if not user or not event: return None

    participations = (await db.execute(
        select(EventParticipation)
        .where(EventParticipation.user_id == user_id, EventParticipation.event_id == event_id)
        .order_by(EventParticipation.joined_at)
    )).scalars().all()

    status_counts = {"completed": 0, "checked_in": 0, "checked_out": 0}
    total_distance = Decimal("0")

    for p in participations:
        status_str = p.status if isinstance(p.status, str) else p.status.value
        if status_str in status_counts: status_counts[status_str] += 1
        if p.status == ParticipationStatus.COMPLETED and p.actual_distance_km:
            total_distance += p.actual_distance_km

    # Leaderboard Logic
    config = await get_leaderboard_config_by_event(db, event_id)
    leaderboard_rank = None
    leaderboard_reward_name = None
    leaderboard_qualified = False
    leaderboard_config_id = None
    tier_progress = []

    if config:
        leaderboard_config_id = config.id
        entry = await get_user_entry(db, config.id, user_id)
        if entry:
            leaderboard_rank = entry.rank
            leaderboard_qualified = entry.qualified_at is not None
            if entry.reward_id:
                from src.models.reward import Reward
                reward = (await db.execute(select(Reward).where(Reward.id == entry.reward_id))).scalar_one_or_none()
                if reward: leaderboard_reward_name = reward.name

        reward_tiers = [RewardTier(**tier) for tier in config.reward_tiers]
        for tier in sorted(reward_tiers, key=lambda t: t.tier):
            req = tier.required_completions if tier.required_completions is not None else config.required_completions
            prog = min(100, (status_counts["completed"] / req) * 100) if req > 0 else 0
            tier_progress.append({
                "tier": tier.tier,
                "tier_name": tier.reward_name or f"Tier {tier.tier}",
                "required_completions": req,
                "current_completions": status_counts["completed"],
                "progress_percentage": round(prog, 2),
                "qualified": status_counts["completed"] >= req
            })

    return {
        "user_id": user_id,
        "user_full_name": f"{user.first_name} {user.last_name}",
        "user_email": user.email,
        "event_id": event_id,
        "event_name": event.title,
        "total_participations": len(participations),
        "completed_participations": status_counts["completed"],
        "checked_in_count": status_counts["checked_in"] + status_counts["checked_out"],
        "total_distance_km": float(total_distance),
        "leaderboard_config_id": leaderboard_config_id,
        "leaderboard_rank": leaderboard_rank,
        "leaderboard_qualified": leaderboard_qualified,
        "leaderboard_reward_name": leaderboard_reward_name,
        "tier_progress": tier_progress
    }

async def get_all_users_event_status(db: AsyncSession, event_id: int, skip: int = 0, limit: int = 100) -> Dict[str, Any]:
    from src.models.event import Event
    from src.models.event_participation import EventParticipation

    event = (await db.execute(select(Event).where(Event.id == event_id))).scalar_one_or_none()
    if not event: return None

    users_result = await db.execute(
        select(EventParticipation.user_id)
        .where(EventParticipation.event_id == event_id)
        .distinct().offset(skip).limit(limit)
    )
    user_ids = users_result.scalars().all()

    total_result = await db.execute(
        select(func.count(func.distinct(EventParticipation.user_id)))
        .where(EventParticipation.event_id == event_id)
    )
    total_users = total_result.scalar() or 0

    users_status = []
    for uid in user_ids:
        s = await get_user_event_status(db, uid, event_id)
        if s: users_status.append(s)

    return {
        "total_users": total_users,
        "event_id": event_id,
        "event_name": event.title,
        "users": users_status
    }

async def get_event_users_summary(db: AsyncSession, event_id: int) -> Dict[str, Any]:
    from src.models.event import Event

    event = (await db.execute(select(Event).where(Event.id == event_id))).scalar_one_or_none()
    if not event: return None

    status_counts_result = await db.execute(
        select(EventParticipation.status, func.count(EventParticipation.id))
        .where(EventParticipation.event_id == event_id)
        .group_by(EventParticipation.status)
    )

    by_status = {}
    total_participations = 0
    completed_count = 0

    for row in status_counts_result.fetchall():
        status_str = row[0] if isinstance(row[0], str) else row[0].value
        by_status[status_str] = row[1]
        total_participations += row[1]
        if status_str == "completed":
            completed_count = row[1]

    unique_result = await db.execute(
        select(func.count(func.distinct(EventParticipation.user_id)))
        .where(EventParticipation.event_id == event_id)
    )
    total_participants = unique_result.scalar() or 0

    completion_rate = (completed_count / total_participations * 100) if total_participations > 0 else 0

    return {
        "event_id": event_id,
        "event_name": event.title,
        "total_participants": total_participants,
        "by_status": by_status,
        "completion_rate": round(completion_rate, 2)
    }