from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
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


class EventParticipationProofSubmit(BaseModel):
    proof_image_url: str


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
    status: ParticipationStatus

    # Proof
    proof_image_url: Optional[str] = None
    proof_submitted_at: Optional[datetime] = None

    # Check-in
    checked_in_at: Optional[datetime] = None

    # Completion
    completed_at: Optional[datetime] = None

    # Rejection
    rejection_reason: Optional[str] = None
    rejected_at: Optional[datetime] = None

    # Cancellation
    cancellation_reason: Optional[str] = None
    cancelled_at: Optional[datetime] = None

    # Timestamps
    joined_at: datetime
    updated_at: datetime

    if ConfigDict:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True