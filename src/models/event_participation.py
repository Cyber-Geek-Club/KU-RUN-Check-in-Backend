from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from src.models.base import Base


class ParticipationStatus(str, enum.Enum):
    JOINED = "joined"           # ลงทะเบียนแล้ว รอวันงาน
    CHECKED_IN = "checked_in"   # Check-in แล้ว เริ่มวิ่ง
    PROOF_SUBMITTED = "proof_submitted"  # ส่งหลักฐานแล้ว รอตรวจสอบ
    COMPLETED = "completed"     # วิ่งเสร็จสมบูรณ์
    REJECTED = "rejected"       # ถูกปฏิเสธ (ทุจริต)
    CANCELLED = "cancelled"     # ยกเลิก


class EventParticipation(Base):
    __tablename__ = "event_participations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    
    # Unique codes
    join_code = Column(String(5), unique=True, nullable=False, index=True)  # 5-digit code for check-in
    completion_code = Column(String(10), unique=True, nullable=True)  # Code after proof approved
    
    # Status tracking
    status = Column(SQLEnum(ParticipationStatus), default=ParticipationStatus.JOINED)
    
    # Proof submission
    proof_image_url = Column(String(500), nullable=True)
    proof_submitted_at = Column(DateTime, nullable=True)
    
    # Staff verification
    checked_in_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Staff who checked in
    checked_in_at = Column(DateTime, nullable=True)
    
    completed_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Staff who verified completion
    completed_at = Column(DateTime, nullable=True)
    
    # Rejection reason (for anti-cheating)
    rejection_reason = Column(Text, nullable=True)
    rejected_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    
    # Timestamps
    joined_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="participations", foreign_keys=[user_id])
    event = relationship("Event", back_populates="participations")
    staff_checked_in = relationship("User", foreign_keys=[checked_in_by])
    staff_completed = relationship("User", foreign_keys=[completed_by])
    staff_rejected = relationship("User", foreign_keys=[rejected_by])
