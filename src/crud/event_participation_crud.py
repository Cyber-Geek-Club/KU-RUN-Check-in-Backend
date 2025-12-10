from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.event_participation import EventParticipation, ParticipationStatus
from src.schemas.event_participation_schema import EventParticipationCreate
from datetime import datetime, timezone
from typing import Optional
import random
import string


def generate_join_code() -> str:
    """Generate unique 5-digit code"""
    return ''.join(random.choices(string.digits, k=5))


def generate_completion_code() -> str:
    """Generate unique 10-character code"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))


async def get_participations_by_user(db: AsyncSession, user_id: int):
    result = await db.execute(
        select(EventParticipation)
        .where(EventParticipation.user_id == user_id)
        .order_by(EventParticipation.joined_at.desc())
    )
    return result.scalars().all()


async def get_participations_by_event(db: AsyncSession, event_id: int):
    result = await db.execute(
        select(EventParticipation)
        .where(EventParticipation.event_id == event_id)
        .order_by(EventParticipation.joined_at.desc())
    )
    return result.scalars().all()


async def get_participation_by_id(db: AsyncSession, participation_id: int) -> Optional[EventParticipation]:
    result = await db.execute(
        select(EventParticipation).where(EventParticipation.id == participation_id)
    )
    return result.scalar_one_or_none()


async def get_participation_by_join_code(db: AsyncSession, join_code: str) -> Optional[EventParticipation]:
    result = await db.execute(
        select(EventParticipation).where(EventParticipation.join_code == join_code)
    )
    return result.scalar_one_or_none()


async def create_participation(db: AsyncSession, participation: EventParticipationCreate,
                               user_id: int) -> EventParticipation:
    # Generate unique join code
    join_code = generate_join_code()
    while await get_participation_by_join_code(db, join_code):
        join_code = generate_join_code()

    db_participation = EventParticipation(
        user_id=user_id,
        event_id=participation.event_id,
        join_code=join_code,
        status=ParticipationStatus.JOINED
    )
    db.add(db_participation)
    await db.commit()
    await db.refresh(db_participation)
    return db_participation


async def check_in_participation(db: AsyncSession, join_code: str, staff_id: int) -> Optional[EventParticipation]:
    participation = await get_participation_by_join_code(db, join_code)
    if not participation or participation.status != ParticipationStatus.JOINED:
        return None

    participation.status = ParticipationStatus.CHECKED_IN
    participation.checked_in_by = staff_id
    participation.checked_in_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(participation)
    return participation


async def submit_proof(db: AsyncSession, participation_id: int, proof_image_url: str) -> Optional[EventParticipation]:
    participation = await get_participation_by_id(db, participation_id)
    if not participation or participation.status != ParticipationStatus.CHECKED_IN:
        return None

    participation.proof_image_url = proof_image_url
    participation.proof_submitted_at = datetime.now(timezone.utc)
    participation.status = ParticipationStatus.PROOF_SUBMITTED

    await db.commit()
    await db.refresh(participation)
    return participation


async def verify_completion(db: AsyncSession, participation_id: int, staff_id: int, approved: bool,
                            rejection_reason: Optional[str] = None) -> Optional[EventParticipation]:
    participation = await get_participation_by_id(db, participation_id)
    if not participation or participation.status != ParticipationStatus.PROOF_SUBMITTED:
        return None

    if approved:
        # Generate completion code
        completion_code = generate_completion_code()
        participation.completion_code = completion_code
        participation.status = ParticipationStatus.COMPLETED
        participation.completed_by = staff_id
        participation.completed_at = datetime.now(timezone.utc)
    else:
        participation.status = ParticipationStatus.REJECTED
        participation.rejection_reason = rejection_reason
        participation.rejected_by = staff_id
        participation.rejected_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(participation)
    return participation


async def cancel_participation(db: AsyncSession, participation_id: int, user_id: int) -> Optional[EventParticipation]:
    participation = await get_participation_by_id(db, participation_id)
    if not participation or participation.user_id != user_id:
        return None

    participation.status = ParticipationStatus.CANCELLED
    await db.commit()
    await db.refresh(participation)
    return participation