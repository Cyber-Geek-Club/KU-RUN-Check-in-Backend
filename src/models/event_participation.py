from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
# ❌ ลบบรรทัดนี้: from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from src.models.base import Base


class NotificationType(str, enum.Enum):
    EVENT_JOINED = "event_joined"
    EVENT_REMINDER = "event_reminder"
    CHECK_IN_SUCCESS = "check_in_success"
    PROOF_SUBMITTED = "proof_submitted"
    COMPLETION_APPROVED = "completion_approved"
    COMPLETION_REJECTED = "completion_rejected"
    REWARD_EARNED = "reward_earned"
    EVENT_UPDATED = "event_updated"
    EVENT_CANCELLED = "event_cancelled"


class NotificationChannel(str, enum.Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    PUSH = "push"
    SMS = "sms"


class NotificationStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    READ = "read"


class Notification(Base):
    """ตารางแจ้งเตือน"""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Notification details
    type = Column(String(50), nullable=False)  # ✅ เปลี่ยนจาก SQLEnum
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    # Related entities
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=True)
    participation_id = Column(Integer, ForeignKey("event_participations.id", ondelete="CASCADE"), nullable=True)
    reward_id = Column(Integer, ForeignKey("rewards.id", ondelete="SET NULL"), nullable=True)

    # ✅ เปลี่ยนเป็น String แทน ENUM
    channel = Column(String(20), default='in_app', nullable=False)
    status = Column(String(20), default='pending', nullable=False)

    # Sent tracking
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)

    # Delivery attempts and errors
    send_attempts = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)

    # Read tracking
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="notifications")
    event = relationship("Event")
    participation = relationship("EventParticipation")
    reward = relationship("Reward")