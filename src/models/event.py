from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from src.models.base import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Event details
    event_date = Column(DateTime(timezone=True), nullable=False)
    event_end_date = Column(DateTime(timezone=True), nullable=True)
    location = Column(String(500), nullable=True)
    distance_km = Column(Integer, nullable=True)
    max_participants = Column(Integer, nullable=True)

    # Event image/banner
    banner_image_url = Column(Text, nullable=True)
    # Status
    is_active = Column(Boolean, default=True)
    is_published = Column(Boolean, default=False)

    # Created by staff
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationships with CASCADE DELETE
    creator = relationship("User", foreign_keys=[created_by])
    participations = relationship(
        "EventParticipation",
        back_populates="event",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    @property
    def participant_count(self) -> int:
        """นับจำนวนผู้เข้าร่วมที่ยังไม่ได้ cancel"""
        if not self.participations:
            return 0

        from src.models.event_participation import ParticipationStatus

        active_participants = [
            p for p in self.participations
            if p.status != ParticipationStatus.CANCELLED
        ]
        return len(active_participants)

    @property
    def remaining_slots(self) -> int:
        """คำนวณที่ว่างที่เหลือ"""
        if self.max_participants is None:
            return -1
        return max(0, self.max_participants - self.participant_count)

    @property
    def is_full(self) -> bool:
        """ตรวจสอบว่างานเต็มหรือไม่"""
        if self.max_participants is None:
            return False
        return self.participant_count >= self.max_participants