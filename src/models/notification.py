from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from src.models.base import Base


class NotificationType(str, enum.Enum):
    EVENT_JOINED = "event_joined"  # เมื่อลงทะเบียนงานสำเร็จ
    EVENT_REMINDER = "event_reminder"  # แจ้งเตือนก่อนงาน 1 วัน
    CHECK_IN_SUCCESS = "check_in_success"  # Check-in สำเร็จ
    PROOF_SUBMITTED = "proof_submitted"  # ส่งหลักฐานแล้ว
    COMPLETION_APPROVED = "completion_approved"  # อนุมัติหลักฐาน
    COMPLETION_REJECTED = "completion_rejected"  # ปฏิเสธหลักฐาน
    REWARD_EARNED = "reward_earned"  # ได้รับรางวัล
    EVENT_UPDATED = "event_updated"  # งานมีการอัปเดต
    EVENT_CANCELLED = "event_cancelled"  # งานถูกยกเลิก


class Notification(Base):
    """ตารางแจ้งเตือน"""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Notification details
    type = Column(SQLEnum(NotificationType), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    # Related entities (optional)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=True)
    participation_id = Column(Integer, ForeignKey("event_participations.id", ondelete="CASCADE"), nullable=True)
    reward_id = Column(Integer, ForeignKey("rewards.id", ondelete="SET NULL"), nullable=True)

    # Status
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="notifications")
    event = relationship("Event")
    participation = relationship("EventParticipation")
    reward = relationship("Reward")