from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from src.models.notification import NotificationType, NotificationChannel, NotificationStatus

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

    # 🆕 Delivery tracking
    channel: NotificationChannel
    status: NotificationStatus
    is_sent: bool
    sent_at: Optional[datetime] = None
    send_attempts: int
    last_error: Optional[str] = None

    # Read tracking
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime

    if ConfigDict:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True


class NotificationCreate(BaseModel):
    """Schema สำหรับสร้างการแจ้งเตือน"""
    user_id: int
    type: NotificationType
    title: str
    message: str
    event_id: Optional[int] = None
    participation_id: Optional[int] = None
    reward_id: Optional[int] = None
    channel: NotificationChannel = NotificationChannel.IN_APP


class NotificationMarkRead(BaseModel):
    """Schema สำหรับทำเครื่องหมายว่าอ่านแล้ว"""
    notification_ids: List[int]


class NotificationMarkSent(BaseModel):
    """Schema สำหรับทำเครื่องหมายว่าส่งแล้ว"""
    notification_ids: List[int]
    success: bool = True
    error_message: Optional[str] = None


class NotificationStats(BaseModel):
    """Schema สำหรับสถิติการแจ้งเตือน"""
    total: int
    unread: int
    read: int
    pending: int  # 🆕 รอส่ง
    sent: int  # 🆕 ส่งแล้ว
    failed: int  # 🆕 ส่งไม่สำเร็จ


class UnreadCount(BaseModel):
    """Schema สำหรับจำนวนการแจ้งเตือนที่ยังไม่อ่าน"""
    unread_count: int


class UnsentCount(BaseModel):
    """Schema สำหรับจำนวนการแจ้งเตือนที่ยังไม่ได้ส่ง"""
    unsent_count: int


class NotificationSendRequest(BaseModel):
    """Schema สำหรับขอส่งการแจ้งเตือน"""
    notification_id: int
    channel: Optional[NotificationChannel] = None  # Override default channel


class BulkNotificationSendRequest(BaseModel):
    """Schema สำหรับส่งการแจ้งเตือนหลายรายการ"""
    notification_ids: List[int]
    channel: Optional[NotificationChannel] = None