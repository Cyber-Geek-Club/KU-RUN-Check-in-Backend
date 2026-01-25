# src/crud/event_participation_crud.py

from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import func, extract, case, and_
from src.models.event_participation import EventParticipation, ParticipationStatus
from src.models.event import Event, EventType  # Added EventType import
from src.schemas.event_participation_schema import EventParticipationCreate
from src.crud import notification_crud
from datetime import datetime, timezone, date, timedelta
from typing import Optional, Dict, List
from decimal import Decimal
import random
import string
from fastapi import HTTPException, status

from src.utils.image_hash import are_images_similar, get_hash_similarity_score
import pytz

BANGKOK_TZ = pytz.timezone('Asia/Bangkok')

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
    # Check if user already has an active participation
    existing_query = await db.execute(
        select(EventParticipation)
        .where(
            EventParticipation.user_id == user_id,
            EventParticipation.event_id == participation.event_id
        )
        .order_by(EventParticipation.joined_at.desc())
    )
    existing_participations = existing_query.scalars().all()

    # Check for active (non-cancelled) participation
    for existing in existing_participations:
        if existing.status != ParticipationStatus.CANCELLED:
            raise HTTPException(
                status_code=400,
                detail="คุณได้สมัครกิจกรรมนี้แล้ว"
            )

    # If user has a cancelled participation, reactivate it
    if existing_participations:
        cancelled_participation = existing_participations[0]  # Most recent

        # Generate new join code
        join_code = generate_join_code()
        while await get_participation_by_join_code(db, join_code):
            join_code = generate_join_code()

        # Reset the participation
        cancelled_participation.status = ParticipationStatus.JOINED
        cancelled_participation.join_code = join_code
        cancelled_participation.joined_at = datetime.now(timezone.utc)
        cancelled_participation.cancellation_reason = None
        cancelled_participation.cancelled_at = None

        await db.commit()
        await db.refresh(cancelled_participation)

        # Get event details for notification
        event = await db.execute(select(Event).where(Event.id == participation.event_id))
        event_obj = event.scalar_one_or_none()

        # 🔔 Notify: Registered
        if event_obj:
            await notification_crud.notify_event_joined(
                db, user_id, participation.event_id, cancelled_participation.id, event_obj.title
            )

        return cancelled_participation

    # Create new participation if no existing record
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

    # 🔔 Notify: Registered
    if event_obj:
        await notification_crud.notify_event_joined(
            db, user_id, participation.event_id, db_participation.id, event_obj.title
        )

    return db_participation


async def check_duplicate_proof_image(
        db: AsyncSession,
        image_hash: str,
        current_user_id: int,
        current_participation_id: Optional[int] = None
) -> Optional[Dict]:
    """Check if image hash already exists in the system"""
    if not image_hash:
        return None

    # Get all participations with proof images
    result = await db.execute(
        select(EventParticipation)
        .where(
            EventParticipation.proof_image_hash.isnot(None),
            EventParticipation.status.in_([
                ParticipationStatus.PROOF_SUBMITTED,
                ParticipationStatus.COMPLETED
            ])
        )
    )
    participations = result.scalars().all()

    # Check for similar images
    for participation in participations:
        # Skip if it's the same participation (for resubmit)
        if current_participation_id and participation.id == current_participation_id:
            continue

        # Check if hashes are similar
        if are_images_similar(image_hash, participation.proof_image_hash, threshold=5):
            similarity = get_hash_similarity_score(image_hash, participation.proof_image_hash)

            return {
                "is_duplicate": True,
                "participation_id": participation.id,
                "user_id": participation.user_id,
                "event_id": participation.event_id,
                "is_same_user": participation.user_id == current_user_id,
                "similarity_score": similarity,
                "submitted_at": participation.proof_submitted_at
            }

    return None


async def check_in_participation(db: AsyncSession, join_code: str, staff_id: int) -> Optional[EventParticipation]:
    participation = await get_participation_by_join_code(db, join_code)
    if not participation or participation.status != ParticipationStatus.JOINED:
        return None

    participation.status = ParticipationStatus.CHECKED_IN
    participation.checked_in_by = staff_id
    participation.checked_in_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(participation)

    # 🔔 Notify: Check-in Success
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
        image_hash: str,
        strava_link: Optional[str] = None,
        actual_distance_km: Optional[Decimal] = None
) -> Optional[EventParticipation]:
    """Submit proof with duplicate check"""
    participation = await get_participation_by_id(db, participation_id)
    if not participation or participation.status != ParticipationStatus.CHECKED_IN:
        return None

    # Check for duplicate images
    duplicate_check = await check_duplicate_proof_image(
        db, image_hash, participation.user_id, participation_id
    )

    if duplicate_check and duplicate_check["is_duplicate"]:
        # If different user submitted similar image - reject
        if not duplicate_check["is_same_user"]:
            participation.status = ParticipationStatus.REJECTED
            participation.rejection_reason = (
                f"ภาพซ้ำกับการส่งครั้งก่อน (Similarity: {duplicate_check['similarity_score']}/64). "
                f"กรุณาส่งภาพจริงของคุณเอง"
            )
            participation.rejected_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(participation)

            if participation.event:
                await notification_crud.notify_completion_rejected(
                    db, participation.user_id, participation.event_id,
                    participation.id, participation.event.title,
                    participation.rejection_reason
                )
            return participation

    # Update participation
    participation.proof_image_url = proof_image_url
    participation.proof_image_hash = image_hash
    participation.strava_link = strava_link
    participation.actual_distance_km = actual_distance_km
    participation.proof_submitted_at = datetime.now(timezone.utc)
    participation.status = ParticipationStatus.PROOF_SUBMITTED

    await db.commit()
    await db.refresh(participation)

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
        image_hash: str,
        strava_link: Optional[str] = None,
        actual_distance_km: Optional[Decimal] = None
) -> Optional[EventParticipation]:
    """Resubmit proof after rejection"""
    participation = await get_participation_by_id(db, participation_id)

    if not participation or participation.status != ParticipationStatus.REJECTED:
        return None

    duplicate_check = await check_duplicate_proof_image(
        db, image_hash, participation.user_id, participation_id
    )

    if duplicate_check and duplicate_check["is_duplicate"] and not duplicate_check["is_same_user"]:
        participation.rejection_reason = (
            f"ภาพซ้ำกับการส่งของผู้ใช้อื่น (Similarity: {duplicate_check['similarity_score']}/64). "
            f"กรุณาส่งภาพจริงของคุณเอง"
        )
        participation.rejected_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(participation)
        return participation

    participation.proof_image_url = proof_image_url
    participation.proof_image_hash = image_hash
    participation.strava_link = strava_link
    participation.actual_distance_km = actual_distance_km
    participation.proof_submitted_at = datetime.now(timezone.utc)
    participation.status = ParticipationStatus.PROOF_SUBMITTED
    participation.rejection_reason = None
    participation.rejected_by = None
    participation.rejected_at = None

    await db.commit()
    await db.refresh(participation)

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
        completion_code = generate_completion_code()
        participation.completion_code = completion_code
        participation.status = ParticipationStatus.CHECKED_OUT  # หรือ COMPLETED ตาม Business Logic
        # ถ้าตาม Code เดิมเป็น CHECKED_OUT ควร set checked_out_at ด้วย
        participation.completed_by = staff_id
        participation.completed_at = datetime.now(timezone.utc)
        participation.checked_out_at = datetime.now(timezone.utc) # ✅ Add consistency

        await db.commit()
        await db.refresh(participation)

        if participation.event:
            await notification_crud.notify_completion_approved(
                db, participation.user_id, participation.event_id,
                participation.id, participation.event.title, completion_code
            )
        
        # ✅ Fix: เรียกตรวจสอบรางวัลหลัง Commit (เฉพาะกรณี Approved)
        try:
            from src.crud.reward_crud import check_and_award_rewards
            await check_and_award_rewards(db, participation.user_id)
        except Exception as e:
            print(f"⚠️ Error checking rewards after verification: {e}")

    else:
        participation.status = ParticipationStatus.REJECTED
        participation.rejection_reason = rejection_reason
        participation.rejected_by = staff_id
        participation.rejected_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(participation)

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
    """Cancel participation"""
    participation = await get_participation_by_id(db, participation_id)

    if not participation or participation.user_id != user_id:
        return None

    if participation.status in [ParticipationStatus.COMPLETED, ParticipationStatus.REJECTED]:
        return None

    participation.status = ParticipationStatus.CANCELLED
    participation.cancellation_reason = cancellation_reason
    participation.cancelled_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(participation)

    return participation


async def rejoin_participation(
        db: AsyncSession,
        participation_id: int,
        user_id: int
) -> Optional[EventParticipation]:
    """
    Rejoin a cancelled participation (max 5 times)
    """
    participation = await get_participation_by_id(db, participation_id)

    if not participation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ไม่พบการเข้าร่วมนี้"
        )

    if participation.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="คุณไม่มีสิทธิ์ในการดำเนินการนี้"
        )

    if participation.status not in [ParticipationStatus.CANCELLED, ParticipationStatus.EXPIRED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"สามารถ rejoin ได้เฉพาะสถานะ cancelled หรือ expired เท่านั้น (สถานะปัจจุบัน: {participation.status})"
        )

    # Check rejoin limit (max 5 times)
    # Reset rejoin count for EXPIRED? No, keep limit.
    if participation.rejoin_count >= 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"คุณได้ใช้สิทธิ์ rejoin ครบ 5 ครั้งแล้ว"
        )

    # Check if event is still available
    if participation.event:
        event = participation.event
        now = datetime.now(timezone.utc)
        
        # Check if event has ended
        event_end = event.event_end_date or event.event_date
        if event_end and now.date() > event_end.date():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="กิจกรรมนี้สิ้นสุดแล้ว ไม่สามารถ rejoin ได้"
            )

    # Generate new join code
    join_code = generate_join_code()
    while await get_participation_by_join_code(db, join_code):
        join_code = generate_join_code()

    # Calculate dates (BKK)
    now_bkk = datetime.now(BANGKOK_TZ)
    today = now_bkk.date()
    code_expires_at = BANGKOK_TZ.localize(datetime.combine(today, datetime.max.time()))

    # Reset participation and increment rejoin count
    participation.status = ParticipationStatus.JOINED
    participation.join_code = join_code
    participation.joined_at = datetime.now(timezone.utc)
    participation.checkin_date = today
    participation.code_expires_at = code_expires_at
    participation.code_used = False
    participation.rejoin_count += 1
    participation.cancellation_reason = None
    participation.cancelled_at = None
    
    # Reset other fields
    participation.checked_in_at = None
    participation.checked_in_by = None
    participation.checked_out_at = None
    participation.checked_out_by = None
    participation.proof_image_url = None
    participation.proof_image_hash = None
    participation.proof_submitted_at = None
    participation.strava_link = None
    participation.actual_distance_km = None
    participation.completed_at = None
    participation.completed_by = None
    participation.completion_code = None
    participation.completion_rank = None
    participation.rejection_reason = None
    participation.rejected_at = None
    participation.rejected_by = None

    await db.commit()
    await db.refresh(participation)

    # Notify user
    if participation.event:
        await notification_crud.notify_event_joined(
            db, user_id, participation.event_id,
            participation.id, participation.event.title
        )

    return participation


async def get_user_statistics(db: AsyncSession, user_id: int) -> Dict:
    """General user statistics"""
    
    # 1. Total Joined (นับทุกครั้งที่สมัคร ยกเว้น Cancel)
    # หมายเหตุ: EXPIRED ถือว่าเคย Join แต่ทำไม่สำเร็จ จึงยังคงนับรวมใน total_joined
    total_joined_result = await db.execute(
        select(func.count(EventParticipation.id))
        .where(
            EventParticipation.user_id == user_id,
            EventParticipation.status != ParticipationStatus.CANCELLED
        )
    )
    total_events_joined = total_joined_result.scalar() or 0

    # 2. Total Completed (นับเฉพาะความสำเร็จจริง)
    # ✅ เพิ่ม CHECKED_OUT และไม่นับ EXPIRED
    completed_result = await db.execute(
        select(func.count(EventParticipation.id))
        .where(
            EventParticipation.user_id == user_id,
            EventParticipation.status.in_([
                ParticipationStatus.COMPLETED, 
                ParticipationStatus.CHECKED_OUT
            ])
        )
    )
    total_events_completed = completed_result.scalar() or 0

    # ... (ส่วนคำนวณ Distance คงเดิม) ...

    # 4. Completion Rate
    completion_rate = 0.0
    if total_events_joined > 0:
        completion_rate = round((total_events_completed / total_events_joined) * 100, 2)

    return {
        "user_id": user_id,
        "total_events_joined": total_events_joined,
        "total_events_completed": total_events_completed,
        # ...
    }

async def get_user_event_stats(
        db: AsyncSession,
        user_id: int,
        event_id: int
) -> Dict:
    """Statistics for a specific event"""
    # Get event info
    event = await db.execute(select(Event).where(Event.id == event_id))
    event_obj = event.scalar_one_or_none()

    if not event_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    # Get all participations for this user and event
    result = await db.execute(
        select(EventParticipation)
        .where(
            EventParticipation.user_id == user_id,
            EventParticipation.event_id == event_id
        )
        .order_by(EventParticipation.joined_at.desc())
    )
    participations = result.scalars().all()

    # Calculate stats
    total_registrations = len(participations)
    
    # นับสำเร็จเฉพาะ COMPLETED และ CHECKED_OUT
    completed_runs = sum(1 for p in participations if p.status in [
        ParticipationStatus.COMPLETED, 
        ParticipationStatus.CHECKED_OUT
    ])
    
    cancelled_runs = sum(1 for p in participations if p.status == ParticipationStatus.CANCELLED)
    expired_runs = sum(1 for p in participations if p.status == ParticipationStatus.EXPIRED) # แยก Stats ให้ชัดเจน

    completion_rate = 0.0
    if total_registrations > 0:
        completion_rate = round((completed_runs / total_registrations) * 100, 2)

    total_distance = Decimal('0.00')
    for p in participations:
        if p.actual_distance_km:
            total_distance += p.actual_distance_km

    participation_details = []
    for p in participations:
        participation_details.append({
            "participation_id": p.id,
            "join_code": p.join_code,
            "status": p.status.value,
            "joined_at": p.joined_at,
            "checked_in_at": p.checked_in_at,
            "completed_at": p.completed_at,
            "completion_rank": p.completion_rank,
            "actual_distance_km": p.actual_distance_km,
            "cancelled_at": p.cancelled_at,
            "cancellation_reason": p.cancellation_reason
        })

    return {
        "user_id": user_id,
        "event_id": event_id,
        "event_title": event_obj.title,
        "total_registrations": total_registrations,
        "completed_runs": completed_runs,
        "cancelled_runs": cancelled_runs,
        "completion_rate": completion_rate,
        "total_distance_km": total_distance,
        "participations": participation_details
    }


async def get_user_all_events_stats(
        db: AsyncSession,
        user_id: int
) -> Dict:
    """Statistics for all events aggregated"""

    # Get all participations with event info
    result = await db.execute(
        select(EventParticipation, Event)
        .join(Event, EventParticipation.event_id == Event.id)
        .where(EventParticipation.user_id == user_id)
        .order_by(EventParticipation.joined_at.desc())
    )
    participations = result.all()

    # Group by event
    events_data = {}
    for participation, event in participations:
        event_id = event.id

        if event_id not in events_data:
            events_data[event_id] = {
                "event_id": event_id,
                "event_title": event.title,
                "event_date": event.event_date,
                "registrations": 0,
                "completed": 0,
                "cancelled": 0,
                "total_distance_km": Decimal('0.00')
            }

        # Count participations
        events_data[event_id]["registrations"] += 1

        if participation.status == ParticipationStatus.COMPLETED:
            events_data[event_id]["completed"] += 1

        if participation.status == ParticipationStatus.CANCELLED:
            events_data[event_id]["cancelled"] += 1

        if participation.actual_distance_km:
            events_data[event_id]["total_distance_km"] += participation.actual_distance_km

    # Calculate completion rates
    for event_data in events_data.values():
        if event_data["registrations"] > 0:
            event_data["completion_rate"] = round(
                (event_data["completed"] / event_data["registrations"]) * 100, 2
            )
        else:
            event_data["completion_rate"] = 0.0

    # Calculate overall summary
    total_events = len(events_data)
    total_registrations = sum(e["registrations"] for e in events_data.values())
    total_completed = sum(e["completed"] for e in events_data.values())

    overall_completion_rate = 0.0
    if total_registrations > 0:
        overall_completion_rate = round((total_completed / total_registrations) * 100, 2)

    return {
        "user_id": user_id,
        "summary": {
            "total_events": total_events,
            "total_registrations": total_registrations,
            "total_completed": total_completed,
            "overall_completion_rate": overall_completion_rate
        },
        "events": sorted(
            events_data.values(),
            key=lambda x: x["event_date"],
            reverse=True
        )
    }


# ========================================
# 🆕 Daily Participation & Limit Logic
# ========================================

async def check_daily_registration_limit(
        db: AsyncSession,
        user_id: int,
        event_id: int
) -> dict:
    """
    🔍 ตรวจสอบว่าผู้ใช้สามารถลงทะเบียนวันนี้ได้หรือไม่ (Daily Reset & Auto-Expire Logic)
    
    Rules:
    1. Checkin Date: Must match TODAY (Bangkok Time).
    2. Daily Limit: User can have only 1 active record per day.
    3. Max Quota: Check global quota excluding EXPIRED records.
    """
    
    # Get event info
    event_result = await db.execute(select(Event).where(Event.id == event_id))
    event = event_result.scalar_one_or_none()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    # ✅ ใช้ Timezone Asia/Bangkok สำหรับวันที่ปัจจุบัน
    now_bkk = datetime.now(BANGKOK_TZ)
    today = now_bkk.date()

    # ตรวจสอบช่วงเวลากิจกรรม (Date Range)
    event_start_date = event.event_date.date()
    event_end_date = event.event_end_date.date() if event.event_end_date else event_start_date

    if today < event_start_date:
        return {
            "can_register": False,
            "reason": f"กิจกรรมยังไม่เริ่ม (เริ่มวันที่ {event_start_date})",
            "today_registration": None,
            "total_checkins": 0
        }

    if today > event_end_date:
        return {
            "can_register": False,
            "reason": f"กิจกรรมสิ้นสุดแล้ว (สิ้นสุดวันที่ {event_end_date})",
            "today_registration": None,
            "total_checkins": 0
        }

    # 🆕 Logic สำหรับ Multi-day (และ Single day ก็ใช้ Logic เดียวกันได้เพื่อความ Consistent)

    # 1. ตรวจสอบว่าวันนี้ลงทะเบียนแล้วหรือยัง (One time per day)
    # เราเช็คเฉพาะ checkin_date == today และ status ไม่ใช่ CANCELLED
    # หมายเหตุ: ถ้า status เป็น EXPIRED (ของวันนี้) ก็ถือว่าลงไปแล้วและหมดสิทธิ์วันนี้
    today_registration_result = await db.execute(
        select(EventParticipation)
        .where(
            and_(
                EventParticipation.user_id == user_id,
                EventParticipation.event_id == event_id,
                EventParticipation.checkin_date == today,  # 🔑 เช็คเฉพาะวันนี้
                # อนุญาตให้ลงใหม่ได้ถ้า status เป็น CANCELLED หรือ EXPIRED
                EventParticipation.status.notin_([
                    ParticipationStatus.CANCELLED,
                    ParticipationStatus.EXPIRED
                ])
            )
        )
    )
    existing_today = today_registration_result.scalars().first()

    if existing_today:
        return {
            "can_register": False,
            "reason": f"คุณได้ลงทะเบียนวันนี้แล้ว (สถานะ: {existing_today.status})",
            "today_registration": existing_today
        }

    # 2. ตรวจสอบจำนวนครั้งทั้งหมด (Total check-in limit)
    # ⚠️ กฎ: นับทุกสถานะ ยกเว้น EXPIRED (แต่รวม CANCELLED ตามนโยบาย)
    total_checkins = 0
    if hasattr(event, 'max_checkins_per_user') and event.max_checkins_per_user:
        total_checkins_result = await db.execute(
            select(func.count(EventParticipation.id))
            .where(
                and_(
                    EventParticipation.user_id == user_id,
                    EventParticipation.event_id == event_id,
                    EventParticipation.status != ParticipationStatus.EXPIRED  # 🔑 Exclude EXPIRED
                )
            )
        )
        total_checkins = total_checkins_result.scalar() or 0

        if total_checkins >= event.max_checkins_per_user:
            return {
                "can_register": False,
                "reason": f"คุณใช้สิทธิ์ครบ {event.max_checkins_per_user} ครั้งแล้ว (ใช้งานไปแล้ว {total_checkins} ครั้ง)",
                "today_registration": None,
                "total_checkins": total_checkins
            }

    return {
        "can_register": True,
        "reason": "สามารถลงทะเบียนวันนี้ได้",
        "today_registration": None,
        "total_checkins": total_checkins
    }

async def create_daily_participation(
        db: AsyncSession,
        participation: EventParticipationCreate,
        user_id: int
) -> EventParticipation:
    """
    🆕 สร้าง participation แบบรายวัน
    """
    # 🔒 Lock User Row to prevent race conditions (duplicates)
    await db.execute(
        select(User.id).where(User.id == user_id).with_for_update()
    )

    # ตรวจสอบว่าลงทะเบียนได้หรือไม่ (จะเช็ค Date Range และ Limit ให้)
    check_result = await check_daily_registration_limit(
        db, user_id, participation.event_id
    )

    if not check_result["can_register"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=check_result["reason"]
        )

    # Get event info
    event_result = await db.execute(
        select(Event).where(Event.id == participation.event_id)
    )
    event = event_result.scalar_one_or_none()

    # Generate unique join code
    join_code = generate_join_code()
    while await get_participation_by_join_code(db, join_code):
        join_code = generate_join_code()

    # กำหนดวันหมดอายุ (สิ้นสุดของวันนี้ BKK)
    now_bkk = datetime.now(BANGKOK_TZ)
    today = now_bkk.date()
    
    code_expires_at = BANGKOK_TZ.localize(
        datetime.combine(today, datetime.max.time())
    )

    # สร้าง participation
    db_participation = EventParticipation(
        user_id=user_id,
        event_id=participation.event_id,
        join_code=join_code,
        status=ParticipationStatus.JOINED,
        checkin_date=today,
        code_used=False,
        code_expires_at=code_expires_at
    )

    db.add(db_participation)
    await db.commit()
    await db.refresh(db_participation)

    # แจ้งเตือน
    if event:
        await notification_crud.notify_event_joined(
            db, user_id, participation.event_id,
            db_participation.id, event.title
        )

    return db_participation


async def check_in_with_code(
        db: AsyncSession,
        join_code: str,
        staff_id: int
) -> EventParticipation:
    """
    🆕 Check-in ด้วยรหัส
    """
    participation = await get_participation_by_join_code(db, join_code)

    if not participation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ไม่พบรหัสนี้ในระบบ"
        )

    if participation.status != ParticipationStatus.JOINED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"รหัสนี้มีสถานะ {participation.status.value if hasattr(participation.status, 'value') else participation.status} แล้ว"
        )

    if hasattr(participation, 'code_used') and participation.code_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="รหัสนี้ถูกใช้ไปแล้ว"
        )

    if hasattr(participation, 'is_code_expired') and participation.is_code_expired:
        participation.status = ParticipationStatus.EXPIRED
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="รหัสนี้หมดอายุแล้ว"
        )

    # Check-in สำเร็จ
    participation.status = ParticipationStatus.CHECKED_IN
    participation.checked_in_by = staff_id
    participation.checked_in_at = datetime.now(timezone.utc)

    if hasattr(participation, 'code_used'):
        participation.code_used = True

    await db.commit()
    await db.refresh(participation)

    # แจ้งเตือน
    if participation.event:
        await notification_crud.notify_check_in_success(
            db, participation.user_id, participation.event_id,
            participation.id, participation.event.title
        )

    return participation


async def get_user_daily_checkin_stats(
        db: AsyncSession,
        user_id: int,
        event_id: int
) -> dict:
    """
    📊 สถิติการ check-in รายวัน
    """
    result = await db.execute(
        select(EventParticipation)
        .where(
            EventParticipation.user_id == user_id,
            EventParticipation.event_id == event_id
        )
        .order_by(EventParticipation.checkin_date.desc())
    )
    participations = result.scalars().all()

    total_registered = len(participations)
    total_checked_in = sum(
        1 for p in participations
        if p.status in [ParticipationStatus.CHECKED_IN, ParticipationStatus.COMPLETED]
    )
    total_expired = sum(
        1 for p in participations
        if p.status == ParticipationStatus.EXPIRED
    )

    # คำนวณ streak
    current_streak = 0
    sorted_dates = sorted([p.checkin_date for p in participations if p.checkin_date], reverse=True)

    if sorted_dates:
        expected_date = datetime.now(timezone.utc).date()
        for check_date in sorted_dates:
            if check_date == expected_date:
                current_streak += 1
                expected_date -= timedelta(days=1)
            elif check_date < expected_date:
                # ถ้าวันล่าสุดที่ check คือเมื่อวาน (หรือไกลกว่า) ก็หลุด streak
                break

    calendar = []
    for p in participations:
        calendar.append({
            "date": p.checkin_date,
            "join_code": p.join_code,
            "status": p.status.value if hasattr(p.status, 'value') else p.status,
            "checked_in_at": p.checked_in_at,
            "code_used": getattr(p, 'code_used', False),
            "code_expired": getattr(p, 'is_code_expired', False)
        })

    return {
        "user_id": user_id,
        "event_id": event_id,
        "total_days_registered": total_registered,
        "total_days_checked_in": total_checked_in,
        "total_days_expired": total_expired,
        "current_streak": current_streak,
        "checkin_calendar": calendar
    }


async def check_out_participation(db: AsyncSession, join_code: str, staff_id: int) -> Optional[EventParticipation]:
    """
    🆕 Check-out participant หลังจบกิจกรรม
    """
    participation = await get_participation_by_join_code(db, join_code)

    if not participation:
        return None

    # ตรวจสอบ status ที่สามารถ check-out ได้
    if participation.status not in [ParticipationStatus.CHECKED_IN, ParticipationStatus.PROOF_SUBMITTED, ParticipationStatus.CHECKED_OUT]:
        return None

    # ปรับ Logic การเปลี่ยนสถานะ
    if participation.status == ParticipationStatus.PROOF_SUBMITTED:
        participation.status = ParticipationStatus.COMPLETED
        participation.completed_at = datetime.now(timezone.utc)
        participation.completed_by = staff_id
    elif participation.status == ParticipationStatus.CHECKED_OUT:
        participation.status = ParticipationStatus.COMPLETED
        participation.completed_at = datetime.now(timezone.utc)
        participation.completed_by = staff_id
    else:
        # กรณี CHECKED_IN -> CHECKED_OUT
        participation.status = ParticipationStatus.CHECKED_OUT
        participation.checked_out_at = datetime.now(timezone.utc) # ✅ Ensure timestamp is set
        participation.checked_out_by = staff_id

    await db.commit()
    await db.refresh(participation)

    # 🔔 Notify: Check-out Success
    if participation.event:
        await notification_crud.notify_check_out_success(
            db, participation.user_id, participation.event_id,
            participation.id, participation.event.title
        )

    # ✅ Fix: เรียกตรวจสอบรางวัลหลัง Commit สำเร็จแล้ว
    try:
        from src.crud.reward_crud import check_and_award_rewards
        await check_and_award_rewards(db, participation.user_id)
    except Exception as e:
        # Log error แต่ไม่ให้ User เห็น Error นี้เพราะ Check-out สำเร็จแล้ว
        print(f"⚠️ Error checking rewards for user {participation.user_id}: {e}")

    return participation


# ========================================
# 🆕 Pre-registration Functions
# ========================================

async def pre_register_for_multi_day_event(
        db: AsyncSession,
        user_id: int,
        event_id: int
) -> dict:
    """
    📝 ลงทะเบียนล่วงหน้าสำหรับกิจกรรมแบบหลายวัน
    ระบบจะสร้างรหัสอัตโนมัติทุกวันให้ผู้ใช้
    """
    # ✅ FIX: Update to use timezone-aware datetime consistently
    from src.models.event import Event

    event_result = await db.execute(
        select(Event).where(Event.id == event_id)
    )
    event = event_result.scalar_one_or_none()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ไม่พบกิจกรรมนี้"
        )

    if event.event_type != EventType.MULTI_DAY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="กิจกรรมนี้ไม่รองรับการลงทะเบียนล่วงหน้า"
        )

    # ใช้วันที่ปัจจุบันแบบ BKK
    now_bkk = datetime.now(BANGKOK_TZ)
    today = now_bkk.date()
    
    # แปลงเวลา Event เป็น BKK เพื่อความถูกต้อง
    event_start_dt = event.event_date.astimezone(BANGKOK_TZ) if event.event_date.tzinfo else event.event_date
    event_end_dt = event.event_end_date.astimezone(BANGKOK_TZ) if event.event_end_date and event.event_end_date.tzinfo else event.event_end_date

    event_start = event_start_dt.date()
    event_end = event_end_dt.date() if event_end_dt else event_start

    # Determine the first valid check-in date
    first_day = max(event_start, today)

    # ตรวจสอบว่าวันที่ต้องการลงทะเบียน (first_day) มีรหัสแล้วหรือยัง
    target_date_check = await db.execute(
        select(EventParticipation)
        .where(
            and_(
                EventParticipation.user_id == user_id,
                EventParticipation.event_id == event_id,
                EventParticipation.checkin_date == first_day,
                EventParticipation.status != ParticipationStatus.CANCELLED
            )
        )
    )

    if target_date_check.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"คุณได้ลงทะเบียนสำหรับวันที่ {first_day} แล้ว"
        )

    # ตรวจสอบจำนวนครั้งทั้งหมด (ถ้ามี limit)
    if event.max_checkins_per_user:
        total_count_result = await db.execute(
            select(func.count(EventParticipation.id))
            .where(
                EventParticipation.user_id == user_id,
                EventParticipation.event_id == event_id,
                EventParticipation.status != ParticipationStatus.CANCELLED
            )
        )
        total_count = total_count_result.scalar() or 0

        if total_count >= event.max_checkins_per_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"คุณลงทะเบียนครบ {event.max_checkins_per_user} ครั้งแล้ว"
            )

    if today > event_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="กิจกรรมนี้จบไปแล้ว ไม่สามารถลงทะเบียนได้"
        )

    join_code = generate_join_code()
    while await get_participation_by_join_code(db, join_code):
        join_code = generate_join_code()

    code_expires_at = BANGKOK_TZ.localize(
        datetime.combine(first_day, datetime.max.time())
    )

    new_participation = EventParticipation(
        user_id=user_id,
        event_id=event_id,
        join_code=join_code,
        status=ParticipationStatus.JOINED,
        checkin_date=first_day,
        code_used=False,
        code_expires_at=code_expires_at
    )

    db.add(new_participation)
    await db.commit()
    await db.refresh(new_participation)

    await notification_crud.notify_event_joined(
        db, user_id, event_id,
        new_participation.id, event.title
    )

    return {
        "success": True,
        "message": "ลงทะเบียนสำเร็จ! ระบบจะสร้างรหัสอัตโนมัติทุกวัน",
        "first_code": join_code,
        "first_date": first_day,
        "event_end_date": event_end
    }


async def get_user_pre_registration_status(
        db: AsyncSession,
        user_id: int,
        event_id: int
) -> dict:
    """
    📊 ตรวจสอบสถานะการลงทะเบียนล่วงหน้า
    """
    result = await db.execute(
        select(EventParticipation)
        .where(
            and_(
                EventParticipation.user_id == user_id,
                EventParticipation.event_id == event_id,
                EventParticipation.status != ParticipationStatus.CANCELLED
            )
        )
        .order_by(EventParticipation.checkin_date.desc())
    )
    participations = result.scalars().all()

    if not participations:
        return {
            "is_registered": False,
            "total_codes": 0,
            "active_codes": 0,
            "used_codes": 0,
            "expired_codes": 0
        }

    today = datetime.now(timezone.utc).date()
    active_codes = []
    used_codes = 0
    expired_codes = 0

    for p in participations:
        if p.status == ParticipationStatus.JOINED and not p.code_used:
            if p.checkin_date == today:
                active_codes.append({
                    "code": p.join_code,
                    "date": p.checkin_date,
                    "expires_at": p.code_expires_at
                })
        elif p.code_used or p.status in [ParticipationStatus.CHECKED_IN, ParticipationStatus.COMPLETED]:
            used_codes += 1
        elif p.status == ParticipationStatus.EXPIRED:
            expired_codes += 1

    return {
        "is_registered": True,
        "total_codes": len(participations),
        "active_codes": len(active_codes),
        "used_codes": used_codes,
        "expired_codes": expired_codes,
        "today_code": active_codes[0] if active_codes else None
    }


async def cancel_pre_registration(
        db: AsyncSession,
        user_id: int,
        event_id: int,
        reason: Optional[str] = None
) -> dict:
    """
    ❌ ยกเลิกการลงทะเบียนล่วงหน้า
    """
    result = await db.execute(
        select(EventParticipation)
        .where(
            and_(
                EventParticipation.user_id == user_id,
                EventParticipation.event_id == event_id,
                EventParticipation.status == ParticipationStatus.JOINED,
                EventParticipation.code_used == False
            )
        )
    )
    unused_participations = result.scalars().all()

    if not unused_participations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ไม่พบรหัสที่สามารถยกเลิกได้"
        )

    now = datetime.now(timezone.utc)
    cancelled_count = 0

    for p in unused_participations:
        p.status = ParticipationStatus.CANCELLED
        p.cancellation_reason = reason or "ยกเลิกโดยผู้ใช้"
        p.cancelled_at = now
        p.updated_at = now
        cancelled_count += 1

    await db.commit()

    return {
        "success": True,
        "message": f"ยกเลิกรหัสทั้งหมด {cancelled_count} รหัสแล้ว",
        "cancelled_count": cancelled_count
    }