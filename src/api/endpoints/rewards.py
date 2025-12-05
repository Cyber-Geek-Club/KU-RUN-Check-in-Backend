from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.db_config import SessionLocal
from src.crud import reward_crud
from src.schemas.reward_schema import RewardCreate, RewardUpdate, RewardRead, UserRewardRead
from typing import List

router = APIRouter()

async def get_db():
    async with SessionLocal() as session:
        yield session

@router.get("/", response_model=List[RewardRead])
async def get_rewards(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """Get all rewards"""
    return await reward_crud.get_rewards(db, skip, limit)

@router.get("/{reward_id}", response_model=RewardRead)
async def get_reward(reward_id: int, db: AsyncSession = Depends(get_db)):
    """Get reward by ID"""
    reward = await reward_crud.get_reward_by_id(db, reward_id)
    if not reward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reward not found"
        )
    return reward

@router.post("/", response_model=RewardRead, status_code=status.HTTP_201_CREATED)
async def create_reward(reward: RewardCreate, db: AsyncSession = Depends(get_db)):
    """Create new reward (admin only)"""
    return await reward_crud.create_reward(db, reward)

@router.put("/{reward_id}", response_model=RewardRead)
async def update_reward(
    reward_id: int,
    reward_data: RewardUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update reward"""
    reward = await reward_crud.update_reward(db, reward_id, reward_data)
    if not reward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reward not found"
        )
    return reward

@router.delete("/{reward_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reward(reward_id: int, db: AsyncSession = Depends(get_db)):
    """Delete reward"""
    deleted = await reward_crud.delete_reward(db, reward_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reward not found"
        )
    return None

@router.get("/user/{user_id}", response_model=List[UserRewardRead])
async def get_user_rewards(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get all rewards earned by a user"""
    return await reward_crud.get_user_rewards(db, user_id)