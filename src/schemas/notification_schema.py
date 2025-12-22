from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from src.models.notification import NotificationType

try:
    from pydantic import ConfigDict
except ImportError:
    ConfigDict = None


class NotificationRead(BaseModel):
    """Schema สำหรับอ่านการแจ้งเตือน"""
    id: int
    user_id: int
    type: NotificationType
    title: str
    message: str
    event_id: Optional[int] = None
    participation_id: Optional[int] = None
    reward_id: Optional[int] = None
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime

    if ConfigDict:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True


class NotificationMarkRead(BaseModel):
    """Schema สำหรับทำเครื่องหมายว่าอ่านแล้ว"""
    notification_ids: List[int]


class NotificationStats(BaseModel):
    """Schema สำหรับสถิติการแจ้งเตือน"""
    total: int
    unread: int
    read: int


class UnreadCount(BaseModel):
    """Schema สำหรับจำนวนการแจ้งเตือนที่ยังไม่อ่าน"""
    unread_count: int