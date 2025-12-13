from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.dependencies import get_db, get_current_user
from src.crud import notification_crud
from src.schemas.notification_schema import (
    NotificationRead,
    NotificationMarkRead,
    NotificationStats,
    UnreadCount
)
from src.models.user import User
from typing import List

router = APIRouter()


@router.get("/", response_model=List[NotificationRead])
async def get_notifications(
        skip: int = 0,
        limit: int = 50,
        unread_only: bool = False,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get user notifications

    - **skip**: จำนวนรายการที่จะข้าม (สำหรับ pagination)
    - **limit**: จำนวนรายการสูงสุดที่จะดึง
    - **unread_only**: ดึงเฉพาะรายการที่ยังไม่อ่าน
    """
    return await notification_crud.get_user_notifications(
        db, current_user.id, skip, limit, unread_only
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


@router.get("/stats", response_model=NotificationStats)
async def get_notification_stats(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get notification statistics

    ดึงสถิติการแจ้งเตือน (ทั้งหมด, ยังไม่อ่าน, อ่านแล้ว)
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