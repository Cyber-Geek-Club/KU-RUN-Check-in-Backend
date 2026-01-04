from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum as SQLEnum
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
    """Channels through which notifications can be sent"""
    IN_APP = "in_app"  # In-app notification (default)
    EMAIL = "email"  # Email notification
    PUSH = "push"  # Push notification
    SMS = "sms"  # SMS notification


class NotificationStatus(str, enum.Enum):
    """Status of notification delivery"""
    PENDING = "pending"  # Created but not sent
    SENT = "sent"  # Successfully sent
    FAILED = "failed"  # Failed to send
    READ = "read"  # Read by user


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

    # 🆕 Delivery tracking
    channel = Column(SQLEnum(NotificationChannel), default=NotificationChannel.IN_APP, nullable=False)
    status = Column(SQLEnum(NotificationStatus), default=NotificationStatus.PENDING, nullable=False)

    # 🆕 Sent tracking
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)

    # 🆕 Delivery attempts and errors
    send_attempts = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)

    # Read tracking (existing)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="notifications")
    event = relationship("Event")
    participation = relationship("EventParticipation")
    reward = relationship("Reward")