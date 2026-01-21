from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime, date  # ✅ เพิ่ม import date
from typing import Optional
from decimal import Decimal
from src.models.event_participation import ParticipationStatus

try:
    from pydantic import ConfigDict
except ImportError:
    ConfigDict = None


class EventParticipationBase(BaseModel):
    event_id: int


class EventParticipationCreate(EventParticipationBase):
    pass


class EventParticipationCheckIn(BaseModel):
    join_code: str


class EventParticipationCheckOut(BaseModel):
    """🆕 Schema สำหรับ Check-out"""
    join_code: str


class EventParticipationProofSubmit(BaseModel):
    """ส่งหลักฐานการวิ่ง"""
    proof_image_url: str
    image_hash: Optional[str] = Field(None, description="Perceptual hash for duplicate detection")
    strava_link: Optional[str] = Field(None, description="Strava activity link (optional)")
    actual_distance_km: Optional[Decimal] = Field(
        None,
        ge=0,
        le=9999.99,
        description="Actual distance ran in kilometers (optional)"
    )


class EventParticipationVerify(BaseModel):
    participation_id: int
    approved: bool
    rejection_reason: Optional[str] = None


class EventParticipationCancel(BaseModel):
    """Schema สำหรับยกเลิกการเข้าร่วม"""
    cancellation_reason: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="เหตุผลในการยกเลิก (จำเป็น)",
        examples=[
            "มีธุระส่วนตัวฉุกเฉิน",
            "ติดภารกิจ",
            "สุขภาพไม่พร้อม",
            "เปลี่ยนใจ"
        ]
    )


class EventParticipationRead(EventParticipationBase):
    id: int
    user_id: int
    join_code: str
    completion_code: Optional[str] = None
    completion_rank: Optional[int] = None
    status: ParticipationStatus

    # 🆕 Daily check-in fields (เพิ่มส่วนนี้)
    checkin_date: Optional[date] = None
    code_expires_at: Optional[datetime] = None

    # Proof
    proof_image_url: Optional[str] = None
    proof_image_hash: Optional[str] = None
    proof_submitted_at: Optional[datetime] = None

    # Strava & Distance tracking
    strava_link: Optional[str] = None
    actual_distance_km: Optional[Decimal] = None

    # Check-in
    checked_in_at: Optional[datetime] = None

    # 🆕 Check-out
    checked_out_at: Optional[datetime] = None

    # Completion
    completed_at: Optional[datetime] = None

    # Rejection
    rejection_reason: Optional[str] = None
    rejected_at: Optional[datetime] = None

    # Cancellation
    cancellation_reason: Optional[str] = None
    cancelled_at: Optional[datetime] = None

    # Rejoin tracking
    rejoin_count: int = 0

    # Timestamps
    joined_at: datetime
    updated_at: datetime

    if ConfigDict:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True


class UserStatistics(BaseModel):
    """สถิติการวิ่งของผู้ใช้"""
    user_id: int
    total_events_joined: int
    total_events_completed: int
    total_distance_km: Decimal
    completion_rate: float
    current_month_completions: int

    if ConfigDict:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True