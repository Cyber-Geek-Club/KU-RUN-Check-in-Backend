from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_
from src.models.reward import Reward, UserReward
from src.models.event_participation import EventParticipation, ParticipationStatus
from src.crud import notification_crud
from datetime import datetime, timedelta, timezone
import pytz
import logging

logger = logging.getLogger(__name__)

async def get_rewards(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(Reward).offset(skip).limit(limit))
    return result.scalars().all()


async def get_reward_by_id(db: AsyncSession, reward_id: int) -> Optional[Reward]:
    result = await db.execute(select(Reward).where(Reward.id == reward_id))
    return result.scalar_one_or_none()


async def create_reward(db: AsyncSession, reward: RewardCreate) -> Reward:
    db_reward = Reward(**reward.model_dump())
    db.add(db_reward)
    await db.commit()
    await db.refresh(db_reward)
    return db_reward


async def update_reward(db: AsyncSession, reward_id: int, reward_data: RewardUpdate) -> Optional[Reward]:
    result = await db.execute(select(Reward).where(Reward.id == reward_id))
    reward = result.scalar_one_or_none()
    if not reward:
        return None

    for key, value in reward_data.model_dump(exclude_unset=True).items():
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
    """
    ตรวจสอบและมอบรางวัล
    ✅ Logic: นับเฉพาะ COMPLETED และ CHECKED_OUT
    ❌ Logic: ไม่นับ EXPIRED, JOINED, CANCELLED
    """
    bangkok_tz = pytz.timezone('Asia/Bangkok')
    now_bkk = datetime.now(bangkok_tz)
    now_utc = datetime.now(timezone.utc)

    rewards = await get_rewards(db)

    for reward in rewards:
        # 1. เช็คว่าเดือนนี้ได้รางวัลไปหรือยัง (ตัดรอบตามเวลาไทย)
        current_month = now_bkk.month
        current_year = now_bkk.year

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

        # 2. นับจำนวนครั้งที่ทำสำเร็จ (Count Success)
        start_date = now_utc - timedelta(days=reward.time_period_days)
        
        # ✅ Whitelist: ระบุสถานะที่ยอมรับให้ชัดเจน
        completed_count_result = await db.execute(
            select(EventParticipation)
            .where(
                and_(
                    EventParticipation.user_id == user_id,
                    EventParticipation.status.in_([
                        ParticipationStatus.COMPLETED,  # สำเร็จแบบปกติ
                        ParticipationStatus.CHECKED_OUT # สำเร็จแบบ Check-out
                    ]),
                    # ❌ EXPIRED จะไม่ถูกนับ เพราะไม่อยู่ใน list ข้างบน
                    
                    # เช็คเวลาจาก field ที่ถูกต้องของแต่ละสถานะ
                    or_(
                        EventParticipation.completed_at >= start_date,
                        EventParticipation.checked_out_at >= start_date
                    )
                )
            )
        )
        completed_participations = completed_count_result.scalars().all()

        if len(completed_participations) >= reward.required_completions:
            try:
                user_reward = UserReward(
                    user_id=user_id,
                    reward_id=reward.id,
                    earned_month=current_month,
                    earned_year=current_year,
                    earned_at=now_utc
                )
                db.add(user_reward)
                await db.commit()
                
                logger.info(f"🏆 Awarded reward '{reward.name}' to user {user_id}")

                await notification_crud.notify_reward_earned(
                    db, user_id, reward.id, reward.name
                )
            except Exception as e:
                logger.error(f"❌ Failed to award reward: {e}")