from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from src.models.event import Event
from src.models.event_participation import EventParticipation
from src.models.user import User
from src.schemas.event_schema import EventCreate, EventUpdate, ParticipantStats, ParticipantInfo
from typing import Optional, Dict
from sqlalchemy.orm import selectinload


async def get_event_participant_count(db: AsyncSession, event_id: int) -> int:
    """นับจำนวนผู้เข้าร่วมทั้งหมดในงาน"""
    result = await db.execute(
        select(func.count(EventParticipation.id))
        .where(EventParticipation.event_id == event_id)
    )
    return result.scalar() or 0


async def get_event_participant_stats(db: AsyncSession, event_id: int) -> ParticipantStats:
    """ดึงสถิติผู้เข้าร่วมแบบละเอียด"""
    # Get all participations with user info
    result = await db.execute(
        select(EventParticipation, User)
        .join(User, EventParticipation.user_id == User.id)
        .where(EventParticipation.event_id == event_id)
    )
    participations = result.all()

    # Count by status
    by_status: Dict[str, int] = {}
    by_role: Dict[str, int] = {}

    for participation, user in participations:
        # Count by status
        status = participation.status.value
        by_status[status] = by_status.get(status, 0) + 1

        # Count by role
        role = user.role.value
        by_role[role] = by_role.get(role, 0) + 1

    return ParticipantStats(
        total=len(participations),
        by_status=by_status,
        by_role=by_role
    )


async def get_event_participants(db: AsyncSession, event_id: int) -> list:
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
):
    """ดึงรายการงานทั้งหมด"""
    query = select(Event)
    if is_published is not None:
        query = query.where(Event.is_published == is_published)
    query = query.offset(skip).limit(limit).order_by(Event.event_date.desc())

    result = await db.execute(query)
    events = result.scalars().all()

    # เพิ่มข้อมูลจำนวนผู้เข้าร่วมถ้าต้องการ
    if include_stats:
        for event in events:
            event.participant_count = await get_event_participant_count(db, event.id)
            event.participant_stats = await get_event_participant_stats(db, event.id)

    return events


async def get_event_by_id(
        db: AsyncSession,
        event_id: int,
        include_stats: bool = False
) -> Optional[Event]:
    """ดึงข้อมูลงานตาม ID"""
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()

    # เพิ่มข้อมูลจำนวนผู้เข้าร่วมถ้าต้องการ
    if event and include_stats:
        event.participant_count = await get_event_participant_count(db, event.id)
        event.participant_stats = await get_event_participant_stats(db, event.id)

    return event


async def create_event(db: AsyncSession, event: EventCreate, created_by: int) -> Event:
    db_event = Event(
        **event.dict(),
        created_by=created_by
    )
    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)

    # เพิ่มข้อมูล participant_count เริ่มต้น
    db_event.participant_count = 0

    return db_event


async def update_event(db: AsyncSession, event_id: int, event_data: EventUpdate) -> Optional[Event]:
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        return None

    for key, value in event_data.dict(exclude_unset=True).items():
        setattr(event, key, value)

    await db.commit()
    await db.refresh(event)
    return event


async def delete_event(db: AsyncSession, event_id: int) -> bool:
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


async def get_events_by_creator(db: AsyncSession, creator_id: int):
    result = await db.execute(
        select(Event).where(Event.created_by == creator_id).order_by(Event.created_at.desc())
    )
    return result.scalars().all()