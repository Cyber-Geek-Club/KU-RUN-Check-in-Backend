from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from src.models.event import Event
from src.models.event_participation import EventParticipation, ParticipationStatus
from src.models.user import User
from src.schemas.event_schema import EventCreate, EventUpdate, ParticipantStats, ParticipantInfo
from typing import Optional, Dict, List
from sqlalchemy.orm import selectinload


async def get_event_participant_stats(db: AsyncSession, event_id: int) -> ParticipantStats:
    """ดึงสถิติผู้เข้าร่วมแบบละเอียด"""
    result = await db.execute(
        select(EventParticipation, User)
        .join(User, EventParticipation.user_id == User.id)
        .where(
            EventParticipation.event_id == event_id,
            EventParticipation.status != ParticipationStatus.CANCELLED
        )
    )
    participations = result.all()

    by_status: Dict[str, int] = {}
    by_role: Dict[str, int] = {}

    for participation, user in participations:
        status = participation.status.value
        by_status[status] = by_status.get(status, 0) + 1

        role = user.role.value
        by_role[role] = by_role.get(role, 0) + 1

    return ParticipantStats(
        total=len(participations),
        by_status=by_status,
        by_role=by_role
    )


async def get_event_participants(db: AsyncSession, event_id: int) -> List[ParticipantInfo]:
    """ดึงรายชื่อผู้เข้าร่วมทั้งหมด"""
    result = await db.execute(
        select(EventParticipation, User)
        .join(User, EventParticipation.user_id == User.id)
        .where(EventParticipation.event_id == event_id)
        .order_by(EventParticipation.joined_at.desc())
    )
    participations = result.all()

    participants = []
    for participation, user in participations:
        participants.append(ParticipantInfo(
            user_id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role.value,
            email=user.email,
            status=participation.status.value,
            joined_at=participation.joined_at
        ))

    return participants


async def get_events(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        is_published: Optional[bool] = None,
        include_stats: bool = False
) -> List[Event]:
    """ดึงรายการงานทั้งหมด"""
    query = select(Event).options(selectinload(Event.participations))

    if is_published is not None:
        query = query.where(Event.is_published == is_published)

    query = query.offset(skip).limit(limit).order_by(Event.event_date.desc())

    result = await db.execute(query)
    events = result.scalars().all()

    if include_stats:
        for event in events:
            event.participant_stats = await get_event_participant_stats(db, event.id)

    return events


async def get_event_by_id(
        db: AsyncSession,
        event_id: int,
        include_stats: bool = False
) -> Optional[Event]:
    """ดึงข้อมูลงานตาม ID"""
    result = await db.execute(
        select(Event)
        .options(selectinload(Event.participations))
        .where(Event.id == event_id)
    )
    event = result.scalar_one_or_none()

    if event and include_stats:
        event.participant_stats = await get_event_participant_stats(db, event.id)

    return event


async def create_event(db: AsyncSession, event: EventCreate, created_by: int) -> Event:
    """สร้างงานใหม่"""
    db_event = Event(
        **event.dict(),
        created_by=created_by
    )
    db.add(db_event)
    await db.commit()

    await db.refresh(db_event, attribute_names=['participations'])

    return db_event


async def update_event(db: AsyncSession, event_id: int, event_data: EventUpdate) -> Optional[Event]:
    """อัปเดตข้อมูลงาน"""
    result = await db.execute(
        select(Event)
        .options(selectinload(Event.participations))
        .where(Event.id == event_id)
    )
    event = result.scalar_one_or_none()

    if not event:
        return None

    for key, value in event_data.dict(exclude_unset=True).items():
        setattr(event, key, value)

    await db.commit()
    await db.refresh(event, attribute_names=['participations'])

    return event


async def delete_event(db: AsyncSession, event_id: int) -> bool:
    """ลบงาน"""
    try:
        result = await db.execute(
            select(Event)
            .options(selectinload(Event.participations))
            .where(Event.id == event_id)
        )
        event = result.scalar_one_or_none()

        if not event:
            return False

        await db.delete(event)
        await db.commit()
        return True

    except Exception as e:
        await db.rollback()
        print(f"Error deleting event: {e}")
        raise


async def get_events_by_creator(db: AsyncSession, creator_id: int) -> List[Event]:
    """ดึงงานที่สร้างโดย user คนนั้น"""
    result = await db.execute(
        select(Event)
        .options(selectinload(Event.participations))
        .where(Event.created_by == creator_id)
        .order_by(Event.created_at.desc())
    )
    return result.scalars().all()


async def check_event_capacity(db: AsyncSession, event_id: int) -> Dict[str, any]:
    """ตรวจสอบความจุของงาน"""
    event = await get_event_by_id(db, event_id)

    if not event:
        return None

    return {
        "event_id": event.id,
        "title": event.title,
        "current_participants": event.participant_count,
        "max_participants": event.max_participants,
        "remaining_slots": event.remaining_slots,
        "is_full": event.is_full,
        "can_join": not event.is_full and event.is_active and event.is_published
    }