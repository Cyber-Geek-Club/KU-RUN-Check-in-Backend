from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.dependencies import get_db, get_current_user, require_organizer
from src.crud import notification_crud
from src.services.notification_service import notification_service
from src.schemas.notification_schema import (
    NotificationRead,
    NotificationMarkRead,
    NotificationMarkSent,
    NotificationStats,
    UnreadCount,
    UnsentCount,
    NotificationSendRequest,
    BulkNotificationSendRequest
)
from src.models.user import User
from typing import List

router = APIRouter()


@router.get("/", response_model=List[NotificationRead])
async def get_notifications(
        skip: int = 0,
        limit: int = 50,
        unread_only: bool = False,
        unsent_only: bool = False,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get user notifications

    - **skip**: จำนวนรายการที่จะข้าม (สำหรับ pagination)
    - **limit**: จำนวนรายการสูงสุดที่จะดึง
    - **unread_only**: ดึงเฉพาะรายการที่ยังไม่อ่าน
    - **unsent_only**: ดึงเฉพาะรายการที่ยังไม่ได้ส่ง
    """
    return await notification_crud.get_user_notifications(
        db, current_user.id, skip, limit, unread_only, unsent_only
    )


@router.get("/unread-count", response_model=UnreadCount)
async def get_unread_count(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get unread notification count

    ดึงจำนวนการแจ้งเตือนที่ยังไม่ได้อ่าน (สำหรับแสดง badge)
    """
    count = await notification_crud.get_unread_count(db, current_user.id)
    return {"unread_count": count}


@router.get("/unsent-count", response_model=UnsentCount)
async def get_unsent_count(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get unsent notification count

    ดึงจำนวนการแจ้งเตือนที่ยังไม่ได้ส่ง (status = PENDING)
    """
    count = await notification_crud.get_unsent_count(db, current_user.id)
    return {"unsent_count": count}


@router.get("/stats", response_model=NotificationStats)
async def get_notification_stats(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get notification statistics

    ดึงสถิติการแจ้งเตือน (ทั้งหมด, ยังไม่อ่าน, อ่านแล้ว, รอส่ง, ส่งแล้ว, ส่งไม่สำเร็จ)
    """
    return await notification_crud.get_notification_stats(db, current_user.id)


@router.post("/mark-read")
async def mark_notifications_as_read(
        data: NotificationMarkRead,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Mark notifications as read

    ทำเครื่องหมายว่าอ่านแล้ว (รับ list ของ notification IDs)
    """
    count = await notification_crud.mark_as_read(
        db, data.notification_ids, current_user.id
    )
    return {
        "success": True,
        "marked_count": count,
        "message": f"Marked {count} notification(s) as read"
    }


@router.post("/mark-all-read")
async def mark_all_notifications_as_read(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Mark all notifications as read

    ทำเครื่องหมายทั้งหมดว่าอ่านแล้ว
    """
    count = await notification_crud.mark_all_as_read(db, current_user.id)
    return {
        "success": True,
        "marked_count": count,
        "message": f"Marked all {count} notification(s) as read"
    }


@router.post("/send/{notification_id}")
async def send_notification(
        notification_id: int,
        background_tasks: BackgroundTasks,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Send a specific notification immediately

    ส่งการแจ้งเตือนทันที (ใช้สำหรับทดสอบหรือส่งใหม่)
    """
    # Get notification
    notification = await notification_crud.get_notification_by_id(db, notification_id)

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )

    # Check ownership
    if notification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only send your own notifications"
        )

    # Send notification in background
    background_tasks.add_task(notification_service.send_notification, db, notification)

    return {
        "success": True,
        "message": f"Notification {notification_id} is being sent",
        "notification_id": notification_id
    }


@router.post("/send-pending")
async def send_pending_notifications(
        background_tasks: BackgroundTasks,
        limit: int = 50,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_organizer)
):
    """
    Send all pending notifications (Organizer only)

    ส่งการแจ้งเตือนทั้งหมดที่รอส่ง (เฉพาะ organizer)
    """
    # Send in background
    background_tasks.add_task(
        notification_service.send_pending_notifications,
        db,
        limit
    )

    return {
        "success": True,
        "message": f"Processing up to {limit} pending notifications in background"
    }


@router.post("/retry-failed")
async def retry_failed_notifications(
        background_tasks: BackgroundTasks,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_organizer)
):
    """
    Retry sending failed notifications (Organizer only)

    ส่งการแจ้งเตือนที่ล้มเหลวใหม่อีกครั้ง (เฉพาะ organizer)
    """
    background_tasks.add_task(
        notification_service.retry_failed_notifications,
        db
    )

    return {
        "success": True,
        "message": "Retrying failed notifications in background"
    }


@router.post("/mark-sent")
async def mark_notifications_as_sent(
        data: NotificationMarkSent,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_organizer)
):
    """
    Mark notifications as sent (Organizer only - for manual operations)

    ทำเครื่องหมายว่าส่งแล้ว (เฉพาะ organizer - สำหรับดำเนินการด้วยมือ)
    """
    count = await notification_crud.mark_as_sent(
        db,
        data.notification_ids,
        success=data.success,
        error_message=data.error_message
    )

    return {
        "success": True,
        "marked_count": count,
        "message": f"Marked {count} notification(s) as {'sent' if data.success else 'failed'}"
    }


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
        notification_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Delete notification

    ลบการแจ้งเตือน
    """
    deleted = await notification_crud.delete_notification(
        db, notification_id, current_user.id
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )

    return None