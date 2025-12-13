from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, List

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


class ParticipantStats(BaseModel):
    """สถิติผู้เข้าร่วม"""
    total: int
    by_status: Dict[str, int]  # {"joined": 10, "checked_in": 5, ...}
    by_role: Dict[str, int]  # {"student": 45, "officer": 3, ...}


class ParticipantInfo(BaseModel):
    """ข้อมูลผู้เข้าร่วมแต่ละคน"""
    user_id: int
    first_name: str
    last_name: str
    role: str
    email: str
    status: str
    joined_at: datetime

    if ConfigDict:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True


class EventRead(EventBase):
    id: int
    is_active: bool
    is_published: bool
    created_by: int
    created_at: datetime
    updated_at: datetime
    participant_count: Optional[int] = None
    participant_stats: Optional[ParticipantStats] = None

    if ConfigDict:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True


class EventWithParticipants(EventRead):
    """Event พร้อมรายชื่อผู้เข้าร่วมทั้งหมด"""
    participants: List[ParticipantInfo] = []