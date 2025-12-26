from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import func, extract
from src.models.event_participation import EventParticipation, ParticipationStatus
from src.models.event import Event
from src.schemas.event_participation_schema import EventParticipationCreate
from src.crud import notification_crud
from datetime import datetime, timezone
from typing import Optional, Dict
from decimal import Decimal
import random
import string


def generate_join_code() -> str:
    """Generate unique 5-digit code"""
    return ''.join(random.choices(string.digits, k=5))


def generate_completion_code() -> str:
    """Generate unique 10-character code"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))


async def get_participations_by_user(db: AsyncSession, user_id: int):
    result = await db.execute(
        select(EventParticipation)
        .where(EventParticipation.user_id == user_id)
        .order_by(EventParticipation.joined_at.desc())
    )
    return result.scalars().all()


async def get_participations_by_event(db: AsyncSession, event_id: int):
    result = await db.execute(
        select(EventParticipation)
        .where(EventParticipation.event_id == event_id)
        .order_by(EventParticipation.joined_at.desc())
    )
    return result.scalars().all()


async def get_participation_by_id(db: AsyncSession, participation_id: int) -> Optional[EventParticipation]:
    result = await db.execute(
        select(EventParticipation)
        .options(selectinload(EventParticipation.event))
        .where(EventParticipation.id == participation_id)
    )
    return result.scalar_one_or_none()


async def get_participation_by_join_code(db: AsyncSession, join_code: str) -> Optional[EventParticipation]:
    result = await db.execute(
        select(EventParticipation)
        .options(selectinload(EventParticipation.event))
        .where(EventParticipation.join_code == join_code)
    )
    return result.scalar_one_or_none()


async def create_participation(db: AsyncSession, participation: EventParticipationCreate,
                               user_id: int) -> EventParticipation:
    # Generate unique join code
    join_code = generate_join_code()
    while await get_participation_by_join_code(db, join_code):
        join_code = generate_join_code()

    # Get event details for notification
    event = await db.execute(select(Event).where(Event.id == participation.event_id))
    event_obj = event.scalar_one_or_none()

    db_participation = EventParticipation(
        user_id=user_id,
        event_id=participation.event_id,
        join_code=join_code,
        status=ParticipationStatus.JOINED
    )
    db.add(db_participation)
    await db.commit()
    await db.refresh(db_participation)

    # 🔔 สร้างการแจ้งเตือน: ลงทะเบียนสำเร็จ
    if event_obj:
        await notification_crud.notify_event_joined(
            db, user_id, participation.event_id, db_participation.id, event_obj.title
        )

    return db_participation


async def check_in_participation(db: AsyncSession, join_code: str, staff_id: int) -> Optional[EventParticipation]:
    participation = await get_participation_by_join_code(db, join_code)
    if not participation or participation.status != ParticipationStatus.JOINED:
        return None

    participation.status = ParticipationStatus.CHECKED_IN
    participation.checked_in_by = staff_id
    participation.checked_in_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(participation)

    # 🔔 สร้างการแจ้งเตือน: Check-in สำเร็จ
    if participation.event:
        await notification_crud.notify_check_in_success(
            db, participation.user_id, participation.event_id,
            participation.id, participation.event.title
        )

    return participation


async def submit_proof(
        db: AsyncSession,
        participation_id: int,
        proof_image_url: str,
        strava_link: Optional[str] = None,
        actual_distance_km: Optional[Decimal] = None
) -> Optional[EventParticipation]:
    """ส่งหลักฐานการวิ่ง พร้อม Strava link และระยะทางจริง"""
    participation = await get_participation_by_id(db, participation_id)
    if not participation or participation.status != ParticipationStatus.CHECKED_IN:
        return None

    participation.proof_image_url = proof_image_url
    participation.strava_link = strava_link
    participation.actual_distance_km = actual_distance_km
    participation.proof_submitted_at = datetime.now(timezone.utc)
    participation.status = ParticipationStatus.PROOF_SUBMITTED

    await db.commit()
    await db.refresh(participation)

    # 🔔 สร้างการแจ้งเตือน: ส่งหลักฐานแล้ว
    if participation.event:
        await notification_crud.notify_proof_submitted(
            db, participation.user_id, participation.event_id,
            participation.id, participation.event.title
        )

    return participation


async def resubmit_proof(
        db: AsyncSession,
        participation_id: int,
        proof_image_url: str,
        strava_link: Optional[str] = None,
        actual_distance_km: Optional[Decimal] = None
) -> Optional[EventParticipation]:
    """ส่งหลักฐานใหม่หลังจากถูกปฏิเสธ"""
    participation = await get_participation_by_id(db, participation_id)

    # ตรวจสอบว่าต้องเป็น status REJECTED เท่านั้น
    if not participation or participation.status != ParticipationStatus.REJECTED:
        return None

    # อัปเดตหลักฐานใหม่
    participation.proof_image_url = proof_image_url
    participation.strava_link = strava_link
    participation.actual_distance_km = actual_distance_km
    participation.proof_submitted_at = datetime.now(timezone.utc)
    participation.status = ParticipationStatus.PROOF_SUBMITTED

    # ล้างข้อมูลการปฏิเสธ
    participation.rejection_reason = None
    participation.rejected_by = None
    participation.rejected_at = None

    await db.commit()
    await db.refresh(participation)

    # 🔔 สร้างการแจ้งเตือน: ส่งหลักฐานใหม่แล้ว
    if participation.event:
        await notification_crud.notify_proof_resubmitted(
            db, participation.user_id, participation.event_id,
            participation.id, participation.event.title
        )

    return participation


async def verify_completion(db: AsyncSession, participation_id: int, staff_id: int, approved: bool,
                            rejection_reason: Optional[str] = None) -> Optional[EventParticipation]:
    participation = await get_participation_by_id(db, participation_id)
    if not participation or participation.status != ParticipationStatus.PROOF_SUBMITTED:
        return None

    if approved:
        # Generate completion code
        completion_code = generate_completion_code()
        participation.completion_code = completion_code
        participation.status = ParticipationStatus.COMPLETED
        participation.completed_by = staff_id
        participation.completed_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(participation)

        # 🔔 สร้างการแจ้งเตือน: อนุมัติหลักฐาน
        if participation.event:
            await notification_crud.notify_completion_approved(
                db, participation.user_id, participation.event_id,
                participation.id, participation.event.title, completion_code
            )
    else:
        participation.status = ParticipationStatus.REJECTED
        participation.rejection_reason = rejection_reason
        participation.rejected_by = staff_id
        participation.rejected_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(participation)

        # 🔔 สร้างการแจ้งเตือน: ปฏิเสธหลักฐาน
        if participation.event:
            await notification_crud.notify_completion_rejected(
                db, participation.user_id, participation.event_id,
                participation.id, participation.event.title,
                rejection_reason or "ไม่ระบุเหตุผล"
            )

    return participation


async def cancel_participation(
        db: AsyncSession,
        participation_id: int,
        user_id: int,
        cancellation_reason: str
) -> Optional[EventParticipation]:
    """ยกเลิกการเข้าร่วมงาน พร้อมบันทึกเหตุผล"""
    participation = await get_participation_by_id(db, participation_id)

    # ตรวจสอบว่ามี participation และเป็นของ user นั้น
    if not participation or participation.user_id != user_id:
        return None

    # ตรวจสอบว่ายังสามารถยกเลิกได้ (ยังไม่ completed หรือ rejected)
    if participation.status in [ParticipationStatus.COMPLETED, ParticipationStatus.REJECTED]:
        return None

    # อัปเดตสถานะเป็น cancelled พร้อมเหตุผล
    participation.status = ParticipationStatus.CANCELLED
    participation.cancellation_reason = cancellation_reason
    participation.cancelled_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(participation)

    return participation


# 🆕 ========== User Statistics Functions ==========

async def get_user_statistics(db: AsyncSession, user_id: int) -> Dict:
    """ดึงสถิติการวิ่งของผู้ใช้"""

    # 1. จำนวนงานที่ลงทะเบียนทั้งหมด (ไม่นับที่ถูก cancel)
    total_joined_result = await db.execute(
        select(func.count(EventParticipation.id))
        .where(
            EventParticipation.user_id == user_id,
            EventParticipation.status != ParticipationStatus.CANCELLED
        )
    )
    total_events_joined = total_joined_result.scalar() or 0

    # 2. จำนวนงานที่วิ่งสำเร็จ (COMPLETED)
    completed_result = await db.execute(
        select(func.count(EventParticipation.id))
        .where(
            EventParticipation.user_id == user_id,
            EventParticipation.status == ParticipationStatus.COMPLETED
        )
    )
    total_events_completed = completed_result.scalar() or 0

    # 3. ระยะทางรวมที่วิ่ง (กม.)
    distance_result = await db.execute(
        select(func.sum(EventParticipation.actual_distance_km))
        .where(
            EventParticipation.user_id == user_id,
            EventParticipation.status == ParticipationStatus.COMPLETED,
            EventParticipation.actual_distance_km.isnot(None)
        )
    )
    total_distance = distance_result.scalar()
    total_distance_km = Decimal(total_distance) if total_distance else Decimal('0.00')

    # 4. คำนวณ completion rate
    completion_rate = 0.0
    if total_events_joined > 0:
        completion_rate = round((total_events_completed / total_events_joined) * 100, 2)

    # 5. จำนวนครั้งที่วิ่งสำเร็จในเดือนนี้
    now = datetime.now(timezone.utc)
    current_month = now.month
    current_year = now.year

    month_completed_result = await db.execute(
        select(func.count(EventParticipation.id))
        .where(
            EventParticipation.user_id == user_id,
            EventParticipation.status == ParticipationStatus.COMPLETED,
            extract('month', EventParticipation.completed_at) == current_month,
            extract('year', EventParticipation.completed_at) == current_year
        )
    )
    current_month_completions = month_completed_result.scalar() or 0

    return {
        "user_id": user_id,
        "total_events_joined": total_events_joined,
        "total_events_completed": total_events_completed,
        "total_distance_km": total_distance_km,
        "completion_rate": completion_rate,
        "current_month_completions": current_month_completions
    }