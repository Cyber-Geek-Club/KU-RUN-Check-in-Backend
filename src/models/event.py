from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from src.models.base import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Event details
    event_date = Column(DateTime, nullable=False)
    event_end_date = Column(DateTime, nullable=True)
    location = Column(String(500), nullable=True)
    distance_km = Column(Integer, nullable=True)  # ระยะทางวิ่ง (กิโลเมตร)
    max_participants = Column(Integer, nullable=True)
    
    # Event image/banner
    banner_image_url = Column(String(500), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_published = Column(Boolean, default=False)
    
    # Created by staff
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    participations = relationship("EventParticipation", back_populates="event")
