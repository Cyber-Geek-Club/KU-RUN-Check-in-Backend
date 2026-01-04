from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, func
from src.models.notification import Notification, NotificationType, NotificationChannel, NotificationStatus
from datetime import datetime, timezone
from typing import Optional, List


async def create_notification(
        db: AsyncSession,
        user_id: int,
        notification_type: NotificationType,
        title: str,
        message: str,
        channel: NotificationChannel = NotificationChannel.IN_APP,
        event_id: Optional[int] = None,
        participation_id: Optional[int] = None,
        reward_id: Optional[int] = None
) -> Notification:
    """สร้างการแจ้งเตือนใหม่"""
    notification = Notification(
        user_id=user_id,
        type=notification_type,
        title=title,
        message=message,
        channel=channel,
        status=NotificationStatus.PENDING,
        event_id=event_id,
        participation_id=participation_id,
        reward_id=reward_id
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    return notification


async def get_user_notifications(
        db: AsyncSession,
        user_id: int,
        skip: int = 0,
        limit: int = 50,
        unread_only: bool = False,
        unsent_only: bool = False
) -> List[Notification]:
    """ดึงการแจ้งเตือนของ user"""
    query = select(Notification).where(Notification.user_id == user_id)

    if unread_only:
        query = query.where(Notification.is_read == False)

    if unsent_only:
        query = query.where(Notification.is_sent == False)

    query = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


async def get_notification_by_id(
        db: AsyncSession,
        notification_id: int
) -> Optional[Notification]:
    """ดึงการแจ้งเตือนตาม ID"""
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    return result.scalar_one_or_none()


async def get_pending_notifications(
        db: AsyncSession,
        limit: int = 100
) -> List[Notification]:
    """ดึงการแจ้งเตือนที่รอส่ง (status = PENDING)"""
    result = await db.execute(
        select(Notification)
        .where(Notification.status == NotificationStatus.PENDING)
        .order_by(Notification.created_at.asc())
        .limit(limit)
    )
    return result.scalars().all()


async def mark_as_sent(
        db: AsyncSession,
        notification_ids: List[int],
        success: bool = True,
        error_message: Optional[str] = None
) -> int:
    """ทำเครื่องหมายว่าส่งแล้ว"""
    result = await db.execute(
        select(Notification).where(Notification.id.in_(notification_ids))
    )
    notifications = result.scalars().all()

    count = 0
    now = datetime.now(timezone.utc)

    for notif in notifications:
        notif.send_attempts += 1

        if success:
            notif.is_sent = True
            notif.sent_at = now
            notif.status = NotificationStatus.SENT
            notif.last_error = None
        else:
            notif.status = NotificationStatus.FAILED
            notif.last_error = error_message

        count += 1

    await db.commit()
    return count


async def mark_as_read(
        db: AsyncSession,
        notification_ids: List[int],
        user_id: int
) -> int:
    """ทำเครื่องหมายว่าอ่านแล้ว"""
    result = await db.execute(
        select(Notification).where(
            and_(
                Notification.id.in_(notification_ids),
                Notification.user_id == user_id,
                Notification.is_read == False
            )
        )
    )
    notifications = result.scalars().all()

    count = 0
    now = datetime.now(timezone.utc)

    for notif in notifications:
        notif.is_read = True
        notif.read_at = now

        # อัปเดต status เป็น READ ถ้าเคยส่งแล้ว
        if notif.status == NotificationStatus.SENT:
            notif.status = NotificationStatus.READ

        count += 1

    await db.commit()
    return count


async def mark_all_as_read(db: AsyncSession, user_id: int) -> int:
    """ทำเครื่องหมายทั้งหมดว่าอ่านแล้ว"""
    result = await db.execute(
        select(Notification).where(
            and_(
                Notification.user_id == user_id,
                Notification.is_read == False
            )
        )
    )
    notifications = result.scalars().all()

    count = 0
    now = datetime.now(timezone.utc)

    for notif in notifications:
        notif.is_read = True
        notif.read_at = now

        if notif.status == NotificationStatus.SENT:
            notif.status = NotificationStatus.READ

        count += 1

    await db.commit()
    return count


async def delete_notification(
        db: AsyncSession,
        notification_id: int,
        user_id: int
) -> bool:
    """ลบการแจ้งเตือน"""
    result = await db.execute(
        select(Notification).where(
            and_(
                Notification.id == notification_id,
                Notification.user_id == user_id
            )
        )
    )
    notification = result.scalar_one_or_none()

    if not notification:
        return False

    await db.delete(notification)
    await db.commit()
    return True


async def get_unread_count(db: AsyncSession, user_id: int) -> int:
    """นับจำนวนการแจ้งเตือนที่ยังไม่อ่าน"""
    result = await db.execute(
        select(func.count(Notification.id)).where(
            and_(
                Notification.user_id == user_id,
                Notification.is_read == False
            )
        )
    )
    return result.scalar() or 0


async def get_unsent_count(db: AsyncSession, user_id: int = None) -> int:
    """นับจำนวนการแจ้งเตือนที่ยังไม่ได้ส่ง"""
    query = select(func.count(Notification.id)).where(
        Notification.status == NotificationStatus.PENDING
    )

    if user_id:
        query = query.where(Notification.user_id == user_id)

    result = await db.execute(query)
    return result.scalar() or 0


async def get_notification_stats(db: AsyncSession, user_id: int) -> dict:
    """ดึงสถิติการแจ้งเตือน"""
    # Total count
    total_result = await db.execute(
        select(func.count(Notification.id)).where(Notification.user_id == user_id)
    )
    total = total_result.scalar() or 0

    # Unread count
    unread_result = await db.execute(
        select(func.count(Notification.id)).where(
            and_(
                Notification.user_id == user_id,
                Notification.is_read == False
            )
        )
    )
    unread = unread_result.scalar() or 0

    # Pending count (unsent)
    pending_result = await db.execute(
        select(func.count(Notification.id)).where(
            and_(
                Notification.user_id == user_id,
                Notification.status == NotificationStatus.PENDING
            )
        )
    )
    pending = pending_result.scalar() or 0

    # Sent count
    sent_result = await db.execute(
        select(func.count(Notification.id)).where(
            and_(
                Notification.user_id == user_id,
                Notification.status.in_([NotificationStatus.SENT, NotificationStatus.READ])
            )
        )
    )
    sent = sent_result.scalar() or 0

    # Failed count
    failed_result = await db.execute(
        select(func.count(Notification.id)).where(
            and_(
                Notification.user_id == user_id,
                Notification.status == NotificationStatus.FAILED
            )
        )
    )
    failed = failed_result.scalar() or 0

    return {
        "total": total,
        "unread": unread,
        "read": total - unread,
        "pending": pending,
        "sent": sent,
        "failed": failed
    }


# ========== Helper Functions for Creating Notifications ==========

async def notify_event_joined(
        db: AsyncSession,
        user_id: int,
        event_id: int,
        participation_id: int,
        event_title: str,
        channel: NotificationChannel = NotificationChannel.IN_APP
):
    """แจ้งเตือนเมื่อลงทะเบียนสำเร็จ"""
    return await create_notification(
        db=db,
        user_id=user_id,
        notification_type=NotificationType.EVENT_JOINED,
        title="ลงทะเบียนสำเร็จ! 🎉",
        message=f'คุณได้ลงทะเบียนเข้าร่วมงาน "{event_title}" เรียบร้อยแล้ว',
        channel=channel,
        event_id=event_id,
        participation_id=participation_id
    )


async def notify_check_in_success(
        db: AsyncSession,
        user_id: int,
        event_id: int,
        participation_id: int,
        event_title: str,
        channel: NotificationChannel = NotificationChannel.IN_APP
):
    """แจ้งเตือนเมื่อ check-in สำเร็จ"""
    return await create_notification(
        db=db,
        user_id=user_id,
        notification_type=NotificationType.CHECK_IN_SUCCESS,
        title="Check-in สำเร็จ! ✅",
        message=f'คุณได้ทำการ check-in งาน "{event_title}" เรียบร้อยแล้ว พร้อมที่จะวิ่งแล้ว!',
        channel=channel,
        event_id=event_id,
        participation_id=participation_id
    )


async def notify_proof_submitted(
        db: AsyncSession,
        user_id: int,
        event_id: int,
        participation_id: int,
        event_title: str,
        channel: NotificationChannel = NotificationChannel.IN_APP
):
    """แจ้งเตือนเมื่อส่งหลักฐานแล้ว"""
    return await create_notification(
        db=db,
        user_id=user_id,
        notification_type=NotificationType.PROOF_SUBMITTED,
        title="ส่งหลักฐานแล้ว 📸",
        message=f'คุณได้ส่งหลักฐานการวิ่งงาน "{event_title}" เรียบร้อยแล้ว รอการตรวจสอบจากเจ้าหน้าที่',
        channel=channel,
        event_id=event_id,
        participation_id=participation_id
    )


async def notify_proof_resubmitted(
        db: AsyncSession,
        user_id: int,
        event_id: int,
        participation_id: int,
        event_title: str,
        channel: NotificationChannel = NotificationChannel.IN_APP
):
    """แจ้งเตือนเมื่อส่งหลักฐานใหม่แล้ว (หลังจากถูกปฏิเสธ)"""
    return await create_notification(
        db=db,
        user_id=user_id,
        notification_type=NotificationType.PROOF_SUBMITTED,
        title="ส่งหลักฐานใหม่แล้ว 🔄",
        message=f'คุณได้ส่งหลักฐานใหม่สำหรับงาน "{event_title}" เรียบร้อยแล้ว รอการตรวจสอบจากเจ้าหน้าที่',
        channel=channel,
        event_id=event_id,
        participation_id=participation_id
    )


async def notify_completion_approved(
        db: AsyncSession,
        user_id: int,
        event_id: int,
        participation_id: int,
        event_title: str,
        completion_code: str,
        channel: NotificationChannel = NotificationChannel.IN_APP
):
    """แจ้งเตือนเมื่ออนุมัติหลักฐาน"""
    return await create_notification(
        db=db,
        user_id=user_id,
        notification_type=NotificationType.COMPLETION_APPROVED,
        title="ผ่านการตรวจสอบ! 🎊",
        message=f'หลักฐานของคุณผ่านการตรวจสอบแล้ว! คุณได้รับรหัสยืนยัน: {completion_code}',
        channel=channel,
        event_id=event_id,
        participation_id=participation_id
    )


async def notify_completion_rejected(
        db: AsyncSession,
        user_id: int,
        event_id: int,
        participation_id: int,
        event_title: str,
        reason: str,
        channel: NotificationChannel = NotificationChannel.IN_APP
):
    """แจ้งเตือนเมื่อปฏิเสธหลักฐาน"""
    return await create_notification(
        db=db,
        user_id=user_id,
        notification_type=NotificationType.COMPLETION_REJECTED,
        title="หลักฐานไม่ผ่าน ❌",
        message=f'หลักฐานงาน "{event_title}" ไม่ผ่านการตรวจสอบ เหตุผล: {reason}. คุณสามารถส่งหลักฐานใหม่ได้',
        channel=channel,
        event_id=event_id,
        participation_id=participation_id
    )


async def notify_reward_earned(
        db: AsyncSession,
        user_id: int,
        reward_id: int,
        reward_name: str,
        channel: NotificationChannel = NotificationChannel.IN_APP
):
    """แจ้งเตือนเมื่อได้รับรางวัล"""
    return await create_notification(
        db=db,
        user_id=user_id,
        notification_type=NotificationType.REWARD_EARNED,
        title="ได้รับรางวัล! 🏆",
        message=f'ยินดีด้วย! คุณได้รับรางวัล "{reward_name}"',
        channel=channel,
        reward_id=reward_id
    )