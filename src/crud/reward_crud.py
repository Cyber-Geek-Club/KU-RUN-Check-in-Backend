from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_
from src.models.reward import Reward, UserReward
from src.models.event_participation import EventParticipation, ParticipationStatus
from src.schemas.reward_schema import RewardCreate, RewardUpdate
from datetime import datetime, timedelta, timezone
from typing import Optional, List


async def get_rewards(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(Reward).offset(skip).limit(limit))
    return result.scalars().all()


async def get_reward_by_id(db: AsyncSession, reward_id: int) -> Optional[Reward]:
    result = await db.execute(select(Reward).where(Reward.id == reward_id))
    return result.scalar_one_or_none()


async def create_reward(db: AsyncSession, reward: RewardCreate) -> Reward:
    db_reward = Reward(**reward.dict())
    db.add(db_reward)
    await db.commit()
    await db.refresh(db_reward)
    return db_reward


async def update_reward(db: AsyncSession, reward_id: int, reward_data: RewardUpdate) -> Optional[Reward]:
    result = await db.execute(select(Reward).where(Reward.id == reward_id))
    reward = result.scalar_one_or_none()
    if not reward:
        return None

    for key, value in reward_data.dict(exclude_unset=True).items():
        setattr(reward, key, value)

    await db.commit()
    await db.refresh(reward)
    return reward


async def delete_reward(db: AsyncSession, reward_id: int) -> bool:
    result = await db.execute(select(Reward).where(Reward.id == reward_id))
    reward = result.scalar_one_or_none()
    if not reward:
        return False

    await db.delete(reward)
    await db.commit()
    return True


async def get_user_rewards(db: AsyncSession, user_id: int) -> List[UserReward]:
    result = await db.execute(
        select(UserReward)
        .where(UserReward.user_id == user_id)
        .order_by(UserReward.earned_at.desc())
    )
    return result.scalars().all()


async def check_and_award_rewards(db: AsyncSession, user_id: int):
    """Check if user qualifies for any rewards and award them"""
    rewards = await get_rewards(db)
    now = datetime.now(timezone.utc)

    for reward in rewards:
        # Check if user already has this reward for current month
        current_month = now.month
        current_year = now.year

        existing_reward = await db.execute(
            select(UserReward).where(
                and_(
                    UserReward.user_id == user_id,
                    UserReward.reward_id == reward.id,
                    UserReward.earned_month == current_month,
                    UserReward.earned_year == current_year
                )
            )
        )
        if existing_reward.scalar_one_or_none():
            continue

        # Check if user meets criteria
        start_date = now - timedelta(days=reward.time_period_days)
        completed_count = await db.execute(
            select(EventParticipation)
            .where(
                and_(
                    EventParticipation.user_id == user_id,
                    EventParticipation.status == ParticipationStatus.COMPLETED,
                    EventParticipation.completed_at >= start_date
                )
            )
        )
        completed_participations = completed_count.scalars().all()

        if len(completed_participations) >= reward.required_completions:
            # Award the reward
            user_reward = UserReward(
                user_id=user_id,
                reward_id=reward.id,
                earned_month=current_month,
                earned_year=current_year
            )
            db.add(user_reward)

    await db.commit()