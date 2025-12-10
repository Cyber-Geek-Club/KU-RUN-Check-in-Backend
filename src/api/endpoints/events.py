from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.db_config import SessionLocal
from src.crud import event_crud
from src.schemas.event_schema import EventCreate, EventUpdate, EventRead
from typing import List, Optional

router = APIRouter()

async def get_db():
    async with SessionLocal() as session:
        yield session

# TODO: Add authentication dependency to get current user
async def get_current_user_id():
    """Mock function - replace with actual JWT authentication"""
    return 1  # Mock user ID

@router.get("/", response_model=List[EventRead])
async def get_events(
    skip: int = 0,
    limit: int = 100,
    is_published: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get all events"""
    return await event_crud.get_events(db, skip, limit, is_published)

@router.get("/{event_id}", response_model=EventRead)
async def get_event(event_id: int, db: AsyncSession = Depends(get_db)):
    """Get event by ID"""
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
    current_user_id: int = Depends(get_current_user_id)
):
    """Create new event (staff/organizer only)"""
    return await event_crud.create_event(db, event, current_user_id)

@router.put("/{event_id}", response_model=EventRead)
async def update_event(
    event_id: int,
    event_data: EventUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update event"""
    event = await event_crud.update_event(db, event_id, event_data)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    return event

@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(event_id: int, db: AsyncSession = Depends(get_db)):
    """Delete event"""
    deleted = await event_crud.delete_event(db, event_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    return None

@router.get("/user/{user_id}", response_model=List[EventRead])
async def get_events_by_creator(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get events created by specific user"""
    return await event_crud.get_events_by_creator(db, user_id)