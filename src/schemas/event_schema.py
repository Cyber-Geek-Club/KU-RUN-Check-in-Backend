from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from datetime import datetime


class EventType(str, Enum):
    SINGLE_DAY = "single_day"
    MULTI_DAY = "multi_day"


class EventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    event_type: EventType
    location: str
    start_time: datetime
    end_time: datetime
    allow_daily_checkin: bool
    capacity: int


class EventRead(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    event_type: EventType = EventType.SINGLE_DAY
    location: str
    start_time: datetime
    end_time: datetime
    allow_daily_checkin: bool = False
    capacity: int
    participant_count: int = 0
    remaining_slots: int = -1
    is_full: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EventSummary(BaseModel):
    id: int
    title: str
    event_type: EventType = EventType.SINGLE_DAY
    location: str
    start_time: datetime
    end_time: datetime
    allow_daily_checkin: bool = False
    participant_count: int = 0
    remaining_slots: int = -1
    is_full: bool = False

    class Config:
        from_attributes = True


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    event_type: Optional[EventType] = None
    location: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    allow_daily_checkin: Optional[bool] = None
    capacity: Optional[int] = None
