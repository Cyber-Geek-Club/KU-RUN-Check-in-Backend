from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.event import Event
from src.schemas.event_schema import EventCreate, EventUpdate
from typing import Optional


async def get_events(db: AsyncSession, skip: int = 0, limit: int = 100, is_published: Optional[bool] = None):
    query = select(Event)
    if is_published is not None:
        query = query.where(Event.is_published == is_published)
    query = query.offset(skip).limit(limit).order_by(Event.event_date.desc())
    result = await db.execute(query)
    return result.scalars().all()


async def get_event_by_id(db: AsyncSession, event_id: int) -> Optional[Event]:
    result = await db.execute(select(Event).where(Event.id == event_id))
    return result.scalar_one_or_none()


async def create_event(db: AsyncSession, event: EventCreate, created_by: int) -> Event:
    db_event = Event(
        **event.dict(),
        created_by=created_by
    )
    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)
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
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        return False

    await db.delete(event)
    await db.commit()
    return True


async def get_events_by_creator(db: AsyncSession, creator_id: int):
    result = await db.execute(
        select(Event).where(Event.created_by == creator_id).order_by(Event.created_at.desc())
    )
    return result.scalars().all()