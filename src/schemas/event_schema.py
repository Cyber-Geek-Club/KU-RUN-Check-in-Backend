from pydantic import BaseModel, computed_field, field_validator
from datetime import datetime
from typing import Optional, Dict, List
from src.models.event import EventType

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

    # 🆕 Daily check-in fields
    event_type: Optional[EventType] = EventType.SINGLE_DAY
    allow_daily_checkin: Optional[bool] = False
    max_checkins_per_user: Optional[int] = None

    @field_validator('banner_image_url', mode='before')
    @classmethod
    def validate_banner_url(cls, v):
        """Validate image URL - only validate on input (mode='before')"""
        # Convert empty string to None
        if v == '' or (isinstance(v, str) and not v.strip()):
            return None

        # Allow None
        if v is None:
            return None

        # Check if it's a base64 data URL
        if v.startswith('data:image'):
            raise ValueError(
                'Base64 images are not supported. Please upload the image using '
                'POST /api/images/upload endpoint first, then use the returned URL.'
            )

        # Check length (only for VARCHAR columns, not needed if using TEXT)
        if len(v) > 500:
            raise ValueError(
                f'Image URL too long ({len(v)} chars). Maximum 500 characters. '
                'Please upload the image using POST /api/images/upload endpoint.'
            )

        return v


class EventCreate(EventBase):
    """Schema for creating a new event"""
    pass


class EventUpdate(BaseModel):
    """Schema for updating an event"""
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

    # 🆕 Daily check-in fields
    event_type: Optional[EventType] = None
    allow_daily_checkin: Optional[bool] = None
    max_checkins_per_user: Optional[int] = None

    @field_validator('banner_image_url', mode='before')
    @classmethod
    def validate_banner_url(cls, v):
        """Validate image URL - only validate on input"""
        # Convert empty string to None
        if v == '' or (isinstance(v, str) and not v.strip()):
            return None

        if v is None:
            return None

        # Check if it's a base64 data URL
        if v.startswith('data:image'):
            raise ValueError(
                'Base64 images are not supported. Please upload the image first.'
            )

        return v


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

    # 🆕 Daily check-in fields (แสดงค่าจริงจากฐานข้อมูล)
    event_type: EventType
    allow_daily_checkin: bool
    max_checkins_per_user: Optional[int] = None

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
    event_end_date: Optional[datetime] = None
    location: Optional[str] = None

    # 🆕 Daily check-in info
    event_type: EventType
    allow_daily_checkin: bool
    max_checkins_per_user: Optional[int] = None

    # Participant info
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