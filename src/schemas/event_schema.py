from pydantic import BaseModel, computed_field
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
    by_status: Dict[str, int]
    by_role: Dict[str, int]


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
    """Schema สำหรับอ่านข้อมูล Event พร้อมจำนวนผู้เข้าร่วมอัตโนมัติ"""
    id: int
    is_active: bool
    is_published: bool
    created_by: int
    created_at: datetime
    updated_at: datetime

    # ข้อมูลผู้เข้าร่วม - แสดงอัตโนมัติเสมอ
    participant_count: int
    remaining_slots: int  # ที่ว่างที่เหลือ (-1 = ไม่จำกัด)
    is_full: bool  # งานเต็มหรือไม่

    # สถิติละเอียด (optional - ต้องขอเพิ่ม)
    participant_stats: Optional[ParticipantStats] = None

    if ConfigDict:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True


class EventWithParticipants(EventRead):
    """Event พร้อมรายชื่อผู้เข้าร่วมทั้งหมด"""
    participants: List[ParticipantInfo] = []


class EventSummary(BaseModel):
    """สรุปข้อมูลงานแบบย่อ (สำหรับ list view)"""
    id: int
    title: str
    event_date: datetime
    location: Optional[str] = None
    participant_count: int
    max_participants: Optional[int] = None
    remaining_slots: int
    is_full: bool
    is_published: bool

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