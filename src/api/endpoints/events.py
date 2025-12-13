from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.dependencies import (
    get_db,
    require_organizer,
    get_current_user,
    require_staff_or_organizer
)
from src.crud import event_crud
from src.schemas.event_schema import (
    EventCreate,
    EventUpdate,
    EventRead,
    EventWithParticipants,
    ParticipantStats
)
from src.models.user import User
from typing import List, Optional

router = APIRouter()


@router.get("/", response_model=List[EventRead])
async def get_events(
        skip: int = 0,
        limit: int = 100,
        is_published: Optional[bool] = None,
        include_stats: bool = Query(False, description="Include participant statistics"),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get all events
    Requires: Any authenticated user

    - **include_stats**: ถ้าเป็น true จะรวมข้อมูลจำนวนผู้เข้าร่วมและสถิติด้วย
    """
    return await event_crud.get_events(db, skip, limit, is_published, include_stats)


@router.get("/{event_id}", response_model=EventRead)
async def get_event(
        event_id: int,
        include_stats: bool = Query(False, description="Include participant statistics"),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get event by ID
    Requires: Any authenticated user

    - **include_stats**: ถ้าเป็น true จะรวมข้อมูลจำนวนผู้เข้าร่วมและสถิติด้วย
    """
    event = await event_crud.get_event_by_id(db, event_id, include_stats)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    return event


@router.get("/{event_id}/stats", response_model=ParticipantStats)
async def get_event_stats(
        event_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get participant statistics for an event
    Requires: Any authenticated user

    ดึงสถิติผู้เข้าร่วมของงาน (จำนวนทั้งหมด, แยกตาม status และ role)
    """
    # Check if event exists
    event = await event_crud.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    return await event_crud.get_event_participant_stats(db, event_id)


@router.get("/{event_id}/participants", response_model=EventWithParticipants)
async def get_event_with_participants(
        event_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_staff_or_organizer)
):
    """
    Get event with full participant list
    Requires: Staff or Organizer role

    ดึงข้อมูลงานพร้อมรายชื่อผู้เข้าร่วมทั้งหมด (เฉพาะ staff/organizer)
    """
    # Get event with stats
    event = await event_crud.get_event_by_id(db, event_id, include_stats=True)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    # Get participant list
    participants = await event_crud.get_event_participants(db, event_id)

    # Return combined data
    event_dict = {
        "id": event.id,
        "title": event.title,
        "description": event.description,
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
        "participant_count": event.participant_count,
        "participant_stats": event.participant_stats,
        "participants": participants
    }

    return event_dict


@router.post("/", response_model=EventRead, status_code=status.HTTP_201_CREATED)
async def create_event(
        event: EventCreate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_organizer)
):
    """
    Create new event
    Requires: Organizer role
    """
    return await event_crud.create_event(db, event, current_user.id)


@router.put("/{event_id}", response_model=EventRead)
async def update_event(
        event_id: int,
        event_data: EventUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_organizer)
):
    """
    Update event
    Requires: Organizer role
    """
    event = await event_crud.update_event(db, event_id, event_data)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    return event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
        event_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_organizer)
):
    """
    Delete event
    Requires: Organizer role
    """
    deleted = await event_crud.delete_event(db, event_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    return None


@router.get("/user/{user_id}", response_model=List[EventRead])
async def get_events_by_creator(
        user_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_organizer)
):
    """
    Get events created by specific user
    Requires: Organizer role
    """
    return await event_crud.get_events_by_creator(db, user_id)