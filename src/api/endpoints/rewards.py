from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.dependencies.auth import (
    get_db,
    get_current_user,
    require_organizer
)
from src.crud import reward_crud
from src.schemas.reward_schema import RewardCreate, RewardUpdate, RewardRead, UserRewardRead
from src.models.user import User
from typing import List

router = APIRouter()


@router.get("/", response_model=List[RewardRead])
async def get_rewards(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all rewards
    Requires: Any authenticated user
    """
    return await reward_crud.get_rewards(db, skip, limit)


@router.get("/{reward_id}", response_model=RewardRead)
async def get_reward(
    reward_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get reward by ID
    Requires: Any authenticated user
    """
    reward = await reward_crud.get_reward_by_id(db, reward_id)
    if not reward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reward not found"
        )
    return reward


@router.post("/", response_model=RewardRead, status_code=status.HTTP_201_CREATED)
async def create_reward(
    reward: RewardCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_organizer)
):
    """
    Create new reward
    Requires: Organizer role
    """
    return await reward_crud.create_reward(db, reward)


@router.put("/{reward_id}", response_model=RewardRead)
async def update_reward(
    reward_id: int,
    reward_data: RewardUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_organizer)
):
    """
    Update reward
    Requires: Organizer role
    """
    reward = await reward_crud.update_reward(db, reward_id, reward_data)
    if not reward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reward not found"
        )
    return reward


@router.delete("/{reward_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reward(
    reward_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_organizer)
):
    """
    Delete reward
    Requires: Organizer role
    """
    deleted = await reward_crud.delete_reward(db, reward_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reward not found"
        )
    return None


@router.get("/user/{user_id}", response_model=List[UserRewardRead])
async def get_user_rewards(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all rewards earned by a user
    Requires: User can only view their own or organizer can view any
    """
    # Users can only view their own rewards, unless they're organizer
    if current_user.id != user_id and current_user.role.value != 'organizer':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own rewards"
        )
    return await reward_crud.get_user_rewards(db, user_id)