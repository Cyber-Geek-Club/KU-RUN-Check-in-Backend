from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from datetime import date, timedelta
from typing import Optional, Dict, List

from src.models.event import Event
from src.models.event_participation import EventParticipation, ParticipationStatus
from src.models.event_holiday import EventHoliday
from src.models.user import User
from src.schemas.event_schema import EventCreate, EventUpdate, ParticipantStats, ParticipantInfo, LeaderboardEntry


def get_value_safe(obj, default=None):
    """Safely get value from enum or string"""
    if obj is None:
        return default
    return obj.value if hasattr(obj, 'value') else obj


async def get_event_participant_stats(db: AsyncSession, event_id: int) -> ParticipantStats:
    """ดึงสถิติผู้เข้าร่วมแบบละเอียด"""
    result = await db.execute(
        select(EventParticipation, User)
        .join(User, EventParticipation.user_id == User.id)
        .where(
            EventParticipation.event_id == event_id,
            EventParticipation.status != "cancelled"  # Use string comparison for safety
        )
    )
    participations = result.all()

    unique_user_ids = set()
    by_status_users: Dict[str, set] = {}
    by_role_users: Dict[str, set] = {}

    for participation, user in participations:
        unique_user_ids.add(user.id)

        # Handle both enum and string values safely
        status = get_value_safe(participation.status, "unknown")
        if status not in by_status_users:
            by_status_users[status] = set()
        by_status_users[status].add(user.id)

        role = get_value_safe(user.role, "unknown")
        if role not in by_role_users:
            by_role_users[role] = set()
        by_role_users[role].add(user.id)

    return ParticipantStats(
        total=len(unique_user_ids),
        by_status={k: len(v) for k, v in by_status_users.items()},
        by_role={k: len(v) for k, v in by_role_users.items()}
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
    seen_user_ids = set()
    for participation, user in participations:
        if user.id in seen_user_ids:
            continue
        seen_user_ids.add(user.id)

        # Handle both enum and string status/role values
        status = get_value_safe(participation.status, "unknown")
        role = get_value_safe(user.role, "unknown")

        participants.append(ParticipantInfo(
            user_id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            role=role,
            email=user.email,
            status=status,
            joined_at=participation.joined_at
        ))

    return participants


async def get_event_with_participants_dict(db: AsyncSession, event_id: int) -> Optional[Dict]:
    """
    ดึงข้อมูลงานพร้อมรายชื่อผู้เข้าร่วมในรูปแบบ dict
    สำหรับ EventWithParticipants schema
    """
    # Get event
    event = await get_event_by_id(db, event_id, include_stats=False)

    if not event:
        return None

    # Get participants list
    participants = await get_event_participants(db, event_id)

    # Convert event to dict manually
    event_dict = {
        "id": event.id,
        "title": event.title,
        "description": event.description,
        "event_type": get_value_safe(event.event_type, "single_day"),
        "event_date": event.event_date,
        "event_end_date": event.event_end_date,
        "location": event.location,
        "distance_km": event.distance_km,
        "max_participants": event.max_participants,
        "banner_image_url": event.banner_image_url,
        "is_active": event.is_active,
        "is_published": event.is_published,
        "created_by": event.created_by,
        "created_at": event.created_at,
        "updated_at": event.updated_at,

        # Daily check-in fields
        "allow_daily_checkin": event.allow_daily_checkin if hasattr(event, 'allow_daily_checkin') else False,
        "max_checkins_per_user": event.max_checkins_per_user if hasattr(event, 'max_checkins_per_user') else None,

        # Computed fields
        "participant_count": event.participant_count,
        "remaining_slots": event.remaining_slots,
        "is_full": event.is_full,

        # Participants list
        "participants": participants,

        # Optional stats (set to None since we're not including them)
        "participant_stats": None
    }

    return event_dict


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
        **event.model_dump(),
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

    for key, value in event_data.model_dump(exclude_unset=True).items():
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


async def get_event_leaderboard(db: AsyncSession, event_id: int) -> List[LeaderboardEntry]:
    """
    ดึง Leaderboard - รายชื่อผู้ที่ผ่านเส้นชัยเรียงตามอันดับ
    """
    result = await db.execute(
        select(EventParticipation, User)
        .join(User, EventParticipation.user_id == User.id)
        .where(
            EventParticipation.event_id == event_id,
            EventParticipation.status == "completed",  # Use string for safety
            EventParticipation.completion_rank.isnot(None)
        )
        .order_by(EventParticipation.completion_rank.asc())
    )

    participations = result.all()

    leaderboard = []
    for participation, user in participations:
        role = get_value_safe(user.role, "unknown")

        leaderboard.append(LeaderboardEntry(
            rank=participation.completion_rank,
            user_id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            full_name=f"{user.first_name} {user.last_name}",
            role=role,
            completion_code=participation.completion_code,
            completed_at=participation.completed_at,
            participation_id=participation.id
        ))

    return leaderboard


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


async def get_event_working_days(db: AsyncSession, event_id: int) -> List[date]:
    """
    ดึงรายการวันที่เปิดให้เข้าร่วมกิจกรรม (ไม่รวมวันหยุด)
    สำหรับกิจกรรมหลายวัน
    """
    event = await get_event_by_id(db, event_id)
    if not event or not event.is_multi_day:
        return []
    
    start_date = event.event_date.date()
    end_date = event.event_end_date.date() if event.event_end_date else start_date
    
    # ดึงวันหยุดทั้งหมด
    holidays_result = await db.execute(
        select(EventHoliday.holiday_date)
        .where(EventHoliday.event_id == event_id)
    )
    holiday_dates = set(holidays_result.scalars().all())
    
    # สร้างรายการวันทำการ
    working_days = []
    current_date = start_date
    while current_date <= end_date:
        if current_date not in holiday_dates:
            working_days.append(current_date)
        current_date += timedelta(days=1)
    
    return working_days


async def count_event_working_days(db: AsyncSession, event_id: int) -> int:
    """นับจำนวนวันทำการของกิจกรรม (ไม่รวมวันหยุด)"""
    working_days = await get_event_working_days(db, event_id)
    return len(working_days)


async def is_event_day_holiday(db: AsyncSession, event_id: int, check_date: date) -> bool:
    """ตรวจสอบว่าวันที่กำหนดเป็นวันหยุดของกิจกรรมหรือไม่"""
    result = await db.execute(
        select(EventHoliday).where(
            EventHoliday.event_id == event_id,
            EventHoliday.holiday_date == check_date
        )
    )
    return result.scalar_one_or_none() is not None