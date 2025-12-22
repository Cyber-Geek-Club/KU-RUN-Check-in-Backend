from pydantic import BaseModel
from datetime import datetime
from typing import Optional

try:
    from pydantic import ConfigDict
except ImportError:
    ConfigDict = None

class EventBase(BaseModel):
    title: str
    description: Optional[str] = None
    event_date: datetime
    event_end_date: Optional[datetime] = None
    location: Optional[str] = None
    distance_km: Optional[int] = None
    max_participants: Optional[int] = None
    banner_image_url: Optional[str] = None

class EventCreate(EventBase):
    pass

class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    event_date: Optional[datetime] = None
    event_end_date: Optional[datetime] = None
    location: Optional[str] = None
    distance_km: Optional[int] = None
    max_participants: Optional[int] = None
    banner_image_url: Optional[str] = None
    is_active: Optional[bool] = None
    is_published: Optional[bool] = None

class EventRead(EventBase):
    id: int
    is_active: bool
    is_published: bool
    created_by: int
    created_at: datetime
    updated_at: datetime

    if ConfigDict:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True


class LeaderboardEntry(BaseModel):
    """รายการผู้ผ่านเส้นชัยในตารางอันดับ"""
    rank: int
    user_id: int
    first_name: str
    last_name: str
    full_name: str
    role: str
    completion_code: str
    completed_at: datetime
    participation_id: int

    if ConfigDict:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True