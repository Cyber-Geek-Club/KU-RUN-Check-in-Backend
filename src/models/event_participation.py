# src/models/event_participation.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Numeric, Date, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone, date
import enum

from src.models.base import Base


class ParticipationStatus(str, enum.Enum):
    JOINED = "joined"                   # ลงทะเบียนแล้ว (รอ check-in)
    CHECKED_IN = "checked_in"           # Check-in แล้ว (ใช้รหัสแล้ว)
    PROOF_SUBMITTED = "proof_submitted"
    COMPLETED = "completed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"                 # 🆕 รหัสหมดอายุ (ไม่ได้ check-in ภายในวัน)


class EventParticipation(Base):
    __tablename__ = "event_participations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False
    )

    # Unique codes
    join_code = Column(String(5), unique=True, nullable=False, index=True)
    completion_code = Column(String(10), unique=True, nullable=True)

    status = Column(String(20), default="joined", nullable=False)

    # 🆕 Daily check-in tracking
    checkin_date = Column(Date, nullable=True, index=True)  # วันที่ check-in (YYYY-MM-DD)
    code_used = Column(Boolean, default=False)              # รหัสถูกใช้แล้วหรือยัง
    code_expires_at = Column(DateTime(timezone=True), nullable=True)  # รหัสหมดอายุเมื่อไหร่

    # Proof submission
    proof_image_url = Column(Text, nullable=True)
    proof_image_hash = Column(String(64), nullable=True, index=True)
    proof_submitted_at = Column(DateTime(timezone=True), nullable=True)

    # Strava & Distance
    strava_link = Column(Text, nullable=True)
    actual_distance_km = Column(Numeric(6, 2), nullable=True)

    # Staff verification
    checked_in_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    checked_in_at = Column(DateTime(timezone=True), nullable=True)

    completed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    completion_rank = Column(Integer, nullable=True, index=True)

    # Rejection
    rejection_reason = Column(Text, nullable=True)
    rejected_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)

    # Cancellation
    cancellation_reason = Column(Text, nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    joined_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="participations", foreign_keys=[user_id])
    event = relationship("Event", back_populates="participations")
    staff_checked_in = relationship("User", foreign_keys=[checked_in_by])
    staff_completed = relationship("User", foreign_keys=[completed_by])
    staff_rejected = relationship("User", foreign_keys=[rejected_by])

    @property
    def is_code_expired(self) -> bool:
        """ตรวจสอบว่ารหัสหมดอายุหรือไม่"""
        if not self.code_expires_at:
            return False
        return datetime.now(timezone.utc) > self.code_expires_at

    @property
    def can_use_code(self) -> bool:
        """ตรวจสอบว่ารหัสยังใช้ได้หรือไม่"""
        return (
            not self.code_used and
            not self.is_code_expired and
            self.status == ParticipationStatus.JOINED
        )