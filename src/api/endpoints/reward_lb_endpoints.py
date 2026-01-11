"""
Reward Leaderboard API Endpoints - CORRECTED VERSION
Replace entire file: src/api/endpoints/reward_lb_endpoints.py
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.dependencies import (
    get_db,
    get_current_user,
    require_organizer,
    require_staff_or_organizer
)
# ✅ CORRECT IMPORT - matches the actual module name
from src.crud import reward_lb_crud
from src.schemas.reward_lb_schema import (
    LeaderboardConfigCreate,
    LeaderboardConfigUpdate,
    LeaderboardConfigRead,
    LeaderboardEntryRead,
    UserLeaderboardStatus,
    UserRewardSummary,
    FinalizeLeaderboardRequest,
)
from src.models.user import User
from typing import List, Optional
from datetime import datetime, timezone

router = APIRouter()


@router.post("/configs", response_model=LeaderboardConfigRead, status_code=status.HTTP_201_CREATED)
async def create_leaderboard_config(
    config: LeaderboardConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_organizer)
):
    """Create Leaderboard Configuration (Organizer Only)"""
    existing = await reward_lb_crud.get_leaderboard_config_by_event(db, config.event_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Event {config.event_id} already has a leaderboard configuration"
        )

    total_slots = sum(tier.quantity for tier in config.reward_tiers)
    if total_slots > config.max_reward_recipients:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Total reward slots ({total_slots}) exceeds max_reward_recipients ({config.max_reward_recipients})"
        )

    return await reward_lb_crud.create_leaderboard_config(db, config, current_user.id)


@router.get("/configs", response_model=List[LeaderboardConfigRead])
async def get_all_leaderboard_configs(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_organizer)
):
    """Get All Leaderboard Configurations (Organizer Only)"""
    # ✅ FIXED: Using reward_lb_crud (not reward_leaderboard_crud)
    return await reward_lb_crud.get_all_leaderboard_configs(db, skip, limit, is_active)


@router.get("/configs/{config_id}", response_model=LeaderboardConfigRead)
async def get_leaderboard_config(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_organizer)
):
    """Get Leaderboard Configuration by ID (Organizer Only)"""
    config = await reward_lb_crud.get_leaderboard_config_by_id(db, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Leaderboard configuration not found"
        )

    stats = await reward_lb_crud.get_leaderboard_stats(db, config_id)
    config.total_reward_slots = stats.get("total_reward_slots", 0)
    config.total_qualified = stats.get("qualified_participants", 0)
    config.total_rewarded = stats.get("rewarded_participants", 0)
    config.is_finalized = stats.get("is_finalized", False)

    return config


@router.get("/configs/event/{event_id}", response_model=LeaderboardConfigRead)
async def get_leaderboard_config_by_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_organizer)
):
    """Get Leaderboard Configuration by Event ID"""
    config = await reward_lb_crud.get_leaderboard_config_by_event(db, event_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No leaderboard configuration found for event {event_id}"
        )

    stats = await reward_lb_crud.get_leaderboard_stats(db, config.id)
    config.total_reward_slots = stats.get("total_reward_slots", 0)
    config.total_qualified = stats.get("qualified_participants", 0)
    config.total_rewarded = stats.get("rewarded_participants", 0)
    config.is_finalized = stats.get("is_finalized", False)

    return config


@router.put("/configs/{config_id}", response_model=LeaderboardConfigRead)
async def update_leaderboard_config(
    config_id: int,
    updates: LeaderboardConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_organizer)
):
    """Update Leaderboard Configuration (Organizer Only)"""
    try:
        config = await reward_lb_crud.update_leaderboard_config(db, config_id, updates)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Leaderboard configuration not found"
            )
        return config
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_leaderboard_config(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_organizer)
):
    """Delete Leaderboard Configuration (Organizer Only)"""
    try:
        deleted = await reward_lb_crud.delete_leaderboard_config(db, config_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Leaderboard configuration not found"
            )
        return None
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/configs/{config_id}/entries", response_model=List[LeaderboardEntryRead])
async def get_leaderboard_entries(
    config_id: int,
    qualified_only: bool = Query(False, description="Show only qualified participants"),
    skip: int = 0,
    limit: int = 1000,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_organizer)
):
    """Get All Entries for a Leaderboard (Organizer Only)"""
    config = await reward_lb_crud.get_leaderboard_config_by_id(db, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Leaderboard configuration not found"
        )
    return await reward_lb_crud.get_leaderboard_entries(db, config_id, qualified_only, skip, limit)


@router.get("/configs/{config_id}/stats")
async def get_leaderboard_statistics(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_organizer)
):
    """Get Leaderboard Statistics (Organizer Only)"""
    config = await reward_lb_crud.get_leaderboard_config_by_id(db, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Leaderboard configuration not found"
        )
    return await reward_lb_crud.get_leaderboard_stats(db, config_id)


@router.post("/configs/{config_id}/calculate-ranks")
async def calculate_rankings(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_organizer)
):
    """Calculate Rankings (Organizer Only)"""
    config = await reward_lb_crud.get_leaderboard_config_by_id(db, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Leaderboard configuration not found"
        )
    ranked_count = await reward_lb_crud.calculate_rankings(db, config_id)
    return {
        "success": True,
        "ranked_count": ranked_count,
        "message": f"Calculated ranks for {ranked_count} participants"
    }


@router.post("/configs/{config_id}/finalize")
async def finalize_leaderboard(
    config_id: int,
    request: FinalizeLeaderboardRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_organizer)
):
    """Finalize Leaderboard (Organizer Only)"""
    if not request.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must confirm finalization by setting confirm=true"
        )

    config = await reward_lb_crud.get_leaderboard_config_by_id(db, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Leaderboard configuration not found"
        )

    now = datetime.now(timezone.utc)
    if now < config.ends_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot finalize before event ends ({config.ends_at})"
        )

    try:
        await reward_lb_crud.finalize_leaderboard(db, config_id)
        stats = await reward_lb_crud.get_leaderboard_stats(db, config_id)
        return {
            "success": True,
            "message": "Leaderboard finalized successfully",
            "statistics": stats
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/my-leaderboards", response_model=UserRewardSummary)
async def get_my_leaderboards(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get My Leaderboard Status (Any User)"""
    configs = await reward_lb_crud.get_all_leaderboard_configs(db, is_active=True)
    leaderboard_statuses = []

    for config in configs:
        entry = await reward_lb_crud.get_user_entry(db, config.id, current_user.id)
        if not entry:
            continue

        from src.crud import event_crud, reward_crud
        event = await event_crud.get_event_by_id(db, config.event_id)

        progress_percentage = min(100, (entry.total_completions / config.required_completions) * 100)
        qualified = entry.qualified_at is not None

        now = datetime.now(timezone.utc)
        can_still_qualify = (
            not qualified and
            now <= config.ends_at and
            config.finalized_at is None
        )

        reward_name = None
        if entry.reward_id:
            reward = await reward_crud.get_reward_by_id(db, entry.reward_id)
            if reward:
                reward_name = reward.name

        leaderboard_statuses.append(UserLeaderboardStatus(
            config_id=config.id,
            event_id=config.event_id,
            event_name=event.title if event else "Unknown Event",
            required_completions=config.required_completions,
            current_completions=entry.total_completions,
            progress_percentage=round(progress_percentage, 2),
            rank=entry.rank,
            qualified=qualified,
            qualified_at=entry.qualified_at,
            reward_tier=entry.reward_tier,
            reward_name=reward_name,
            rewarded_at=entry.rewarded_at,
            is_finalized=config.finalized_at is not None,
            can_still_qualify=can_still_qualify
        ))

    total_leaderboards = len(leaderboard_statuses)
    completed_leaderboards = sum(1 for lb in leaderboard_statuses if lb.qualified)
    rewards_received = sum(1 for lb in leaderboard_statuses if lb.reward_name)
    pending_leaderboards = sum(1 for lb in leaderboard_statuses if not lb.is_finalized)

    return UserRewardSummary(
        total_leaderboards=total_leaderboards,
        completed_leaderboards=completed_leaderboards,
        rewards_received=rewards_received,
        pending_leaderboards=pending_leaderboards,
        leaderboards=leaderboard_statuses
    )


@router.get("/leaderboard/{config_id}/my-status", response_model=UserLeaderboardStatus)
async def get_my_leaderboard_status(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get My Status in Specific Leaderboard"""
    config = await reward_lb_crud.get_leaderboard_config_by_id(db, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Leaderboard not found"
        )

    entry = await reward_lb_crud.get_user_entry(db, config_id, current_user.id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You haven't participated in this leaderboard yet"
        )

    from src.crud import event_crud, reward_crud
    event = await event_crud.get_event_by_id(db, config.event_id)

    progress_percentage = min(100, (entry.total_completions / config.required_completions) * 100)
    qualified = entry.qualified_at is not None

    now = datetime.now(timezone.utc)
    can_still_qualify = (
        not qualified and
        now <= config.ends_at and
        config.finalized_at is None
    )

    reward_name = None
    if entry.reward_id:
        reward = await reward_crud.get_reward_by_id(db, entry.reward_id)
        if reward:
            reward_name = reward.name

    return UserLeaderboardStatus(
        config_id=config.id,
        event_id=config.event_id,
        event_name=event.title if event else "Unknown Event",
        required_completions=config.required_completions,
        current_completions=entry.total_completions,
        progress_percentage=round(progress_percentage, 2),
        rank=entry.rank,
        qualified=qualified,
        qualified_at=entry.qualified_at,
        reward_tier=entry.reward_tier,
        reward_name=reward_name,
        rewarded_at=entry.rewarded_at,
        is_finalized=config.finalized_at is not None,
        can_still_qualify=can_still_qualify
    )


@router.get("/leaderboard/{config_id}/public", response_model=List[LeaderboardEntryRead])
async def get_public_leaderboard(
    config_id: int,
    limit: int = Query(100, ge=1, le=500, description="จำนวนอันดับที่จะแสดง"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get Public Leaderboard Rankings (All Users)"""
    config = await reward_lb_crud.get_leaderboard_config_by_id(db, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Leaderboard not found"
        )

    if not config.finalized_at:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Leaderboard is not finalized yet. Rankings are not public."
        )

    return await reward_lb_crud.get_leaderboard_entries(
        db, config_id, qualified_only=True, skip=0, limit=limit
    )