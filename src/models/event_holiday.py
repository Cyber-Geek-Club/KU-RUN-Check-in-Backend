# src/models/event_holiday.py
from sqlalchemy import Column, Integer, String, Date, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone, date

from src.models.base import Base


class EventHoliday(Base):
    """วันหยุดของกิจกรรม - สำหรับกิจกรรมหลายวันที่มีวันหยุดระหว่างกิจกรรม"""
    __tablename__ = "event_holidays"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Holiday date
    holiday_date = Column(Date, nullable=False, index=True)
    
    # Optional: Holiday name/reason
    holiday_name = Column(String(255), nullable=True)  # เช่น "วันหยุดนักขัตฤกษ์"
    description = Column(Text, nullable=True)
    
    # Who added this holiday
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    event = relationship("Event", back_populates="holidays")
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<EventHoliday(event_id={self.event_id}, date={self.holiday_date}, name={self.holiday_name})>"
    
    @property
    def is_past(self) -> bool:
        """ตรวจสอบว่าวันหยุดนี้ผ่านไปแล้วหรือไม่"""
        return self.holiday_date < date.today()
