# src/models/uploaded_image.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from src.models.base import Base


class ImageCategory(str, enum.Enum):
    """ประเภทของรูปภาพ"""
    EVENT = "events"           # รูป banner กิจกรรม
    PROOF = "proofs"           # รูปหลักฐานการวิ่ง
    REWARD = "rewards"         # รูป badge รางวัล


class UploadedImage(Base):
    """ตารางเก็บข้อมูลรูปภาพที่อัพโหลด"""
    __tablename__ = "uploaded_images"

    id = Column(Integer, primary_key=True, index=True)
    
    # File information
    filename = Column(String(255), nullable=False)              # ชื่อไฟล์ที่บันทึก (uuid.ext)
    original_filename = Column(String(255), nullable=True)      # ชื่อไฟล์ต้นฉบับ
    file_path = Column(Text, nullable=False, unique=True)       # path เต็ม เช่น /uploads/events/xxx.jpg
    file_size = Column(BigInteger, nullable=True)               # ขนาดไฟล์ (bytes)
    mime_type = Column(String(100), nullable=True)              # เช่น image/jpeg, image/png
    
    # Category
    category = Column(String(50), nullable=False, index=True)   # events, proofs, rewards
    
    # Hash for duplicate detection
    image_hash = Column(String(64), nullable=True, index=True)  # perceptual hash
    
    # Uploaded by
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Reference to related entity (optional)
    # event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    # participation_id = Column(Integer, ForeignKey("event_participations.id"), nullable=True)
    # reward_id = Column(Integer, ForeignKey("rewards.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    uploader = relationship("User", foreign_keys=[uploaded_by])
    
    def __repr__(self):
        return f"<UploadedImage(id={self.id}, filename={self.filename}, category={self.category})>"
