# src/models/event.py
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from src.models.base import Base


class EventType(str, enum.Enum):
    """ประเภทของกิจกรรม"""
    SINGLE_DAY = "single_day"
    MULTI_DAY = "multi_day"


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Event type
    event_type = Column(
        SQLEnum(EventType),
        default=EventType.SINGLE_DAY,
        nullable=False
    )

    # Event details
    event_date = Column(DateTime(timezone=True), nullable=False)
    event_end_date = Column(DateTime(timezone=True), nullable=True)
    location = Column(String(500), nullable=True)
    distance_km = Column(Integer, nullable=True)
    max_participants = Column(Integer, nullable=True)

    # Multi-day settings
    allow_daily_checkin = Column(Boolean, default=False)
    max_checkins_per_user = Column(Integer, nullable=True)
    
    # Holiday settings
    # Note: วันหยุดจะถูกเก็บในตาราง event_holidays แยกต่างหาก

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

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    participations = relationship(
        "EventParticipation",
        back_populates="event",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    
    # Leaderboard relationship
    leaderboard_config = relationship(
        "RewardLeaderboardConfig",
        back_populates="event",
        uselist=False,  # One-to-one relationship
        cascade="all, delete-orphan"
    )
    
    # Holidays relationship
    holidays = relationship(
        "EventHoliday",
        back_populates="event",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="EventHoliday.holiday_date"
    )

    @property
    def is_multi_day(self) -> bool:
        """ตรวจสอบว่าเป็นกิจกรรมหลายวันหรือไม่"""
        return self.event_type == EventType.MULTI_DAY

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
    
    @property
    def total_days(self) -> int:
        """คำนวณจำนวนวันทั้งหมดของกิจกรรม"""
        if not self.is_multi_day or not self.event_end_date:
            return 1
        delta = self.event_end_date.date() - self.event_date.date()
        return delta.days + 1
    
    @property
    def holiday_count(self) -> int:
        """นับจำนวนวันหยุด"""
        if not self.holidays:
            return 0
        return len(self.holidays)
    
    @property
    def working_days_count(self) -> int:
        """คำนวณจำนวนวันทำการ (ไม่รวมวันหยุด)"""
        return self.total_days - self.holiday_count