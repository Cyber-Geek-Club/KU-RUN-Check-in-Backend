from pydantic import BaseModel
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

class EventParticipationRead(EventParticipationBase):
    id: int
    user_id: int
    join_code: str
    completion_code: Optional[str] = None
    status: ParticipationStatus
    proof_image_url: Optional[str] = None
    proof_submitted_at: Optional[datetime] = None
    checked_in_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    joined_at: datetime
    updated_at: datetime

    if ConfigDict:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True