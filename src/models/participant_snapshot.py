"""
Participant Snapshot Models
เก็บประวัติการดึงข้อมูล participants ของ event แต่ละครั้ง
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid

from src.models.base import Base


class ParticipantSnapshot(Base):
    """
    Snapshot ของ participants ในแต่ละครั้งที่ดึงข้อมูล
    """
    __tablename__ = "participant_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Snapshot metadata
    snapshot_time = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    entry_count = Column(Integer, default=0)  # จำนวน entries ใน snapshot นี้
    
    # Optional metadata
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # ใครสร้าง snapshot (ถ้าเป็น manual)
    description = Column(String(500), nullable=True)  # คำอธิบายเพิ่มเติม
    
    # Relationships
    event = relationship("Event", foreign_keys=[event_id])
    creator = relationship("User", foreign_keys=[created_by])
    entries = relationship(
        "ParticipantSnapshotEntry", 
        back_populates="snapshot",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ParticipantSnapshotEntry.created_at.desc()"
    )


class ParticipantSnapshotEntry(Base):
    """
    รายละเอียดแต่ละ participant ใน snapshot
    """
    __tablename__ = "participant_snapshot_entries"

    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    snapshot_id = Column(Integer, ForeignKey("participant_snapshots.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Participant info (ข้อมูลเก็บ snapshot ณ เวลานั้น)
    participation_id = Column(Integer, nullable=True)  # อ้างอิง EventParticipation (อาจเป็น null ถ้าถูกลบไปแล้ว)
    user_id = Column(Integer, nullable=False)
    user_name = Column(String(255), nullable=False)
    user_email = Column(String(255), nullable=True)
    
    # Action/Status ณ เวลานั้น
    action = Column(String(50), nullable=False)  # joined, checked_in, completed, cancelled, etc.
    status = Column(String(50), nullable=False)  # participation status
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    joined_at = Column(DateTime(timezone=True), nullable=True)
    checked_in_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Additional metadata (JSON)
    entry_metadata = Column(JSON, nullable=True)  # เก็บข้อมูลเพิ่มเติม เช่น join_code, proof_image_url, etc.
    
    # Relationships
    snapshot = relationship("ParticipantSnapshot", back_populates="entries")
