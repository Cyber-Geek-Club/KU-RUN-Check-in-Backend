from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.dependencies import (
    get_db,
    require_organizer,
    get_current_user
)
from src.crud import event_crud
from src.schemas.event_schema import EventCreate, EventUpdate, EventRead
from src.models.user import User
from typing import List, Optional

router = APIRouter()


@router.get("/", response_model=List[EventRead])
async def get_events(
    skip: int = 0,
    limit: int = 100,
    is_published: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all events
    Requires: Any authenticated user
    """
    return await event_crud.get_events(db, skip, limit, is_published)


@router.get("/{event_id}", response_model=EventRead)
async def get_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get event by ID
    Requires: Any authenticated user
    """
    event = await event_crud.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    return event


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