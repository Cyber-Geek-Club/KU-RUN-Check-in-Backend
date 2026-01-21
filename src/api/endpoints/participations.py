import io
import csv
from datetime import datetime, timezone, date
from typing import List, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, case, select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.crud import  reward_lb_crud
from src.api.dependencies.auth import (
    get_db,
    get_current_user,
    require_staff_or_organizer,
    require_organizer
)
from src.crud import event_participation_crud, reward_crud, event_crud
from src.schemas.event_participation_schema import (
    EventParticipationCreate,
    EventParticipationRead,
    EventParticipationCheckIn,
    EventParticipationCheckOut,
    EventParticipationProofSubmit,
    EventParticipationVerify,
    EventParticipationCancel,
    UserStatistics
)
from src.models.user import User
from src.models.event import Event
from src.models.event_participation import ParticipationStatus, EventParticipation
from src.utils.image_hash import calculate_image_hash

router = APIRouter()

# ==========================================
# Standard Participation (One-time events)
# ==========================================

@router.post("/join", response_model=EventParticipationRead, status_code=status.HTTP_201_CREATED)
async def join_event(
        participation: EventParticipationCreate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Join an event with capacity check"""
    capacity = await event_crud.check_event_capacity(db, participation.event_id)

    if not capacity:
        raise HTTPException(status_code=404, detail="Event not found")

    if not capacity["can_join"]:
        msg = f"Event is full (Max: {capacity['max_participants']})" if capacity["is_full"] else "Event is not available"
        raise HTTPException(status_code=400, detail=msg)

    return await event_participation_crud.create_participation(db, participation, current_user.id)


@router.get("/user/{user_id}", response_model=List[EventParticipationRead])
async def get_user_participations(
        user_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    if current_user.id != user_id and current_user.role.value not in ['staff', 'organizer']:
        raise HTTPException(status_code=403, detail="Access denied")
    return await event_participation_crud.get_participations_by_user(db, user_id)


@router.get("/user/{user_id}/statistics", response_model=UserStatistics)
async def get_user_statistics(
        user_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    if current_user.id != user_id and current_user.role.value not in ['staff', 'organizer']:
        raise HTTPException(status_code=403, detail="Access denied")
    return await event_participation_crud.get_user_statistics(db, user_id)


# --- NOTE: get_participation moved to bottom to prevent route conflict ---


@router.post("/check-in", response_model=EventParticipationRead)
async def check_in(
        check_in_data: EventParticipationCheckIn,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_staff_or_organizer)
):
    participation = await event_participation_crud.check_in_participation(
        db, check_in_data.join_code, current_user.id
    )
    if not participation:
        raise HTTPException(status_code=400, detail="Invalid join code or already checked in")
    return participation


@router.post("/{participation_id}/submit-proof", response_model=EventParticipationRead)
async def submit_proof(
        participation_id: int,
        proof_data: EventParticipationProofSubmit,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Submit proof with duplicate detection"""
    image_hash = getattr(proof_data, 'image_hash', None)
    if not image_hash:
        image_hash = calculate_image_hash(proof_data.proof_image_url)

    participation = await event_participation_crud.submit_proof(
        db, participation_id, proof_data.proof_image_url, image_hash,
        proof_data.strava_link, proof_data.actual_distance_km
    )
    if not participation:
        raise HTTPException(status_code=400, detail="Invalid participation")
    return participation


@router.put("/{participation_id}/resubmit-proof", response_model=EventParticipationRead)
async def resubmit_proof(
        participation_id: int,
        proof_data: EventParticipationProofSubmit,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    image_hash = getattr(proof_data, 'image_hash', None)
    if not image_hash:
        image_hash = calculate_image_hash(proof_data.proof_image_url)

    participation = await event_participation_crud.resubmit_proof(
        db, participation_id, proof_data.proof_image_url, image_hash,
        proof_data.strava_link, proof_data.actual_distance_km
    )
    if not participation:
        raise HTTPException(status_code=400, detail="Failed to resubmit")
    return participation


@router.post("/verify", response_model=EventParticipationRead)
async def verify_completion(
        verify_data: EventParticipationVerify,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_staff_or_organizer)
):
    participation = await event_participation_crud.verify_completion(
        db, verify_data.participation_id, current_user.id,
        verify_data.approved, verify_data.rejection_reason
    )
    if not participation:
        raise HTTPException(status_code=400, detail="Invalid participation")

    if verify_data.approved:
        # 1. ตรวจสอบและแจก Reward ทั่วไป (Badge รายเดือน ฯลฯ)
        await reward_crud.check_and_award_rewards(db, participation.user_id)

        # 2. ✅ FIX: อัปเดต Leaderboard ของกิจกรรมนั้น (ถ้ามี)
        lb_config = await reward_lb_crud.get_leaderboard_config_by_event(db, participation.event_id)
        if lb_config:
            await reward_lb_crud.update_entry_progress(
                db,
                lb_config.id,
                participation.user_id,
                participation.event_id
            )
            
        # 3. ✅ Check & Verify for Single-Day Event Auto-Finalization
        event = await event_crud.get_event_by_id(db, participation.event_id)
        if event and (event.event_type == "single_day" or event.event_end_date.date() == event.event_date.date()):
            # Check if event has ended
            now = datetime.now(timezone.utc)
            if event.event_end_date and now >= event.event_end_date:
                # Trigger auto-finalize
                await reward_lb_crud.auto_finalize_single_day_rewards(db, event.id)

    return participation


@router.post("/{participation_id}/cancel", response_model=EventParticipationRead)
async def cancel_participation(
        participation_id: int,
        cancel_data: EventParticipationCancel,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    participation = await event_participation_crud.cancel_participation(
        db, participation_id, current_user.id, cancel_data.cancellation_reason
    )
    if not participation:
        raise HTTPException(status_code=400, detail="Cannot cancel this participation")
    return participation


@router.post("/{participation_id}/rejoin", response_model=EventParticipationRead)
async def rejoin_participation(
        participation_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    🔄 Rejoin a cancelled participation (max 5 times)
    """
    return await event_participation_crud.rejoin_participation(
        db, participation_id, current_user.id
    )


@router.get("/user/{user_id}/all-events-stats")
async def get_user_all_events_stats(
        user_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    if current_user.id != user_id and current_user.role.value not in ['staff', 'organizer']:
        raise HTTPException(status_code=403, detail="Access denied")
    return await event_participation_crud.get_user_all_events_stats(db, user_id)


# ==========================================
# 🆕 Daily Participation Logic
# ==========================================

@router.post("/join-daily", response_model=EventParticipationRead, status_code=status.HTTP_201_CREATED)
async def join_event_daily(
        participation: EventParticipationCreate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    🆕 ลงทะเบียนเข้าร่วมกิจกรรมแบบรายวัน
    """
    return await event_participation_crud.create_daily_participation(
        db, participation, current_user.id
    )


@router.post("/pre-register/{event_id}", status_code=status.HTTP_201_CREATED)
async def pre_register_multi_day_event(
        event_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    📝 ลงทะเบียนล่วงหน้าสำหรับกิจกรรมแบบหลายวัน
    ระบบจะสร้างรหัสอัตโนมัติทุกวันให้
    """
    return await event_participation_crud.pre_register_for_multi_day_event(
        db, current_user.id, event_id
    )


@router.get("/pre-register-status/{event_id}")
async def get_pre_registration_status(
        event_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    📊 ตรวจสอบสถานะการลงทะเบียนล่วงหน้า
    """
    return await event_participation_crud.get_user_pre_registration_status(
        db, current_user.id, event_id
    )


@router.delete("/pre-register/{event_id}")
async def cancel_pre_registration(
        event_id: int,
        reason: Optional[str] = None,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    ❌ ยกเลิกการลงทะเบียนล่วงหน้า
    """
    return await event_participation_crud.cancel_pre_registration(
        db, current_user.id, event_id, reason
    )


@router.get("/check-daily-limit/{event_id}")
async def check_daily_registration_limit_endpoint(
        event_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    🔍 ตรวจสอบว่าสามารถลงทะเบียนวันนี้ได้หรือไม่
    """
    return await event_participation_crud.check_daily_registration_limit(
        db, current_user.id, event_id
    )

@router.post("/check-in-daily", response_model=EventParticipationRead)
async def check_in_daily(
        check_in_data: EventParticipationCheckIn,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_staff_or_organizer)
):
    """
    🆕 Check-in ด้วยรหัสแบบใช้ครั้งเดียว
    """
    return await event_participation_crud.check_in_with_code(
        db, check_in_data.join_code, current_user.id
    )


@router.get("/daily-stats/{event_id}")
async def get_daily_checkin_stats(
        event_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    📊 ดูสถิติการ check-in รายวันของตัวเอง
    """
    return await event_participation_crud.get_user_daily_checkin_stats(
        db, current_user.id, event_id
    )


@router.get("/my-codes/{event_id}")
async def get_my_active_codes(
        event_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    📱 ดูรหัสที่ยังใช้งานได้ของตัวเอง
    """
    result = await db.execute(
        select(EventParticipation)
        .where(
            EventParticipation.user_id == current_user.id,
            EventParticipation.event_id == event_id
        )
        .order_by(EventParticipation.checkin_date.desc())
        .limit(30)
    )
    participations = result.scalars().all()

    codes = []
    for p in participations:
        codes.append({
            "date": p.checkin_date,
            "join_code": p.join_code,
            "status": p.status.value if hasattr(p.status, 'value') else p.status,
            "code_used": p.code_used,
            "code_expired": p.is_code_expired,
            "can_use": p.can_use_code,
            "expires_at": p.code_expires_at,
            "checked_in_at": p.checked_in_at
        })

    return {
        "event_id": event_id,
        "total_codes": len(codes),
        "codes": codes
    }


@router.get("/{participation_id}/checkout-code")
async def get_checkout_code(
        participation_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    🔑 ได้รับ checkout code หลังจากส่งหลักฐาน (status = proof_submitted)
    """
    result = await db.execute(
        select(EventParticipation)
        .where(
            EventParticipation.id == participation_id,
            EventParticipation.user_id == current_user.id
        )
    )
    
    participation = result.scalar_one_or_none()
    
    if not participation:
        raise HTTPException(
            status_code=404,
            detail="Participation not found"
        )
    
    # ✅ แสดง checkout code ก็ต่อเมื่อ status = proof_submitted
    # Note: Comparison is safe here, but attribute access below needs safety check
    if participation.status != ParticipationStatus.CHECKED_OUT:
        status_val = participation.status.value if hasattr(participation.status, 'value') else participation.status
        raise HTTPException(
            status_code=400,
            detail=f"Cannot get checkout code. Current status: {status_val}. Submit proof first."
        )
    
    return {
        "participation_id": participation_id,
        "event_id": participation.event_id,
        "checkout_code": participation.join_code,
        # ✅ FIXED: Safe access for status value
        "status": participation.status.value if hasattr(participation.status, 'value') else participation.status,
        "proof_submitted_at": participation.proof_submitted_at,
        "message": "✅ Checkout code is ready. Use this code to check out from the event."
    }


@router.post("/check-out", response_model=EventParticipationRead)
async def check_out(
        check_out_data: EventParticipationCheckOut,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_staff_or_organizer)
):
    """
    🆕 Check-out หลังจบกิจกรรม (Staff/Organizer only)
    """
    participation = await event_participation_crud.check_out_participation(
        db, check_out_data.join_code, current_user.id
    )
    if not participation:
        raise HTTPException(
            status_code=400,
            detail="Invalid code or not checked in yet"
        )
    return participation


# ==========================================
# 🎨 Frontend Helper Endpoints
# ==========================================

@router.get("/event/{event_id}/current-status")
async def get_event_current_status(
        event_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_staff_or_organizer)
):
    """
    📊 ดูสถานะปัจจุบันของงาน (Real-time Dashboard)
    """
    # นับตาม status
    result = await db.execute(
        select(
            func.count(EventParticipation.id).label('total'),
            func.sum(
                case((EventParticipation.status == ParticipationStatus.CHECKED_IN, 1), else_=0)
            ).label('currently_in'),
            func.sum(
                case((EventParticipation.status == ParticipationStatus.CHECKED_OUT, 1), else_=0)
            ).label('checked_out'),
            func.sum(
                case((EventParticipation.status == ParticipationStatus.COMPLETED, 1), else_=0)
            ).label('completed')
        )
        .where(
            EventParticipation.event_id == event_id,
            EventParticipation.status != ParticipationStatus.CANCELLED
        )
    )

    stats = result.first()

    # นับแยกตาม status
    status_result = await db.execute(
        select(
            EventParticipation.status,
            func.count(EventParticipation.id)
        )
        .where(EventParticipation.event_id == event_id)
        .group_by(EventParticipation.status)
    )

    by_status = {row[0]: row[1] for row in status_result.all()}

    return {
        "event_id": event_id,
        "total_registered": stats.total or 0,
        "currently_in_event": stats.currently_in or 0,
        "checked_out": stats.checked_out or 0,
        "completed": stats.completed or 0,
        "by_status": by_status,
        "timestamp": datetime.now(timezone.utc)
    }


@router.get("/event/{event_id}/active-participants")
async def get_active_participants(
        event_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_staff_or_organizer)
):
    """
    👥 ดูรายชื่อคนที่อยู่ในงานตอนนี้
    """
    result = await db.execute(
        select(EventParticipation, User)
        .join(User, EventParticipation.user_id == User.id)
        .where(
            EventParticipation.event_id == event_id,
            EventParticipation.status == ParticipationStatus.CHECKED_IN
        )
        .order_by(EventParticipation.checked_in_at.asc())
    )

    participants = []
    for participation, user in result.all():
        participants.append({
            "participation_id": participation.id,
            "join_code": participation.join_code,
            "user_id": user.id,
            "full_name": f"{user.first_name} {user.last_name}",
            "email": user.email,
            "role": user.role.value,
            "checked_in_at": participation.checked_in_at,
            "duration_minutes": int((datetime.now(
                timezone.utc) - participation.checked_in_at).total_seconds() / 60) if participation.checked_in_at else 0
        })

    return {
        "event_id": event_id,
        "total_active": len(participants),
        "participants": participants
    }


@router.post("/event/{event_id}/check-out-all")
async def check_out_all_participants(
        event_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_organizer)
):
    """
    🚪 Check-out คนทั้งหมดที่ยังอยู่ในงาน (Organizer only)
    """
    result = await db.execute(
        select(EventParticipation)
        .where(
            EventParticipation.event_id == event_id,
            EventParticipation.status == ParticipationStatus.CHECKED_IN
        )
    )

    participations = result.scalars().all()

    checked_out_count = 0
    for participation in participations:
        participation.status = ParticipationStatus.CHECKED_OUT
        participation.checked_out_by = current_user.id
        participation.checked_out_at = datetime.now(timezone.utc)
        checked_out_count += 1

    await db.commit()

    return {
        "event_id": event_id,
        "checked_out_count": checked_out_count,
        "message": f"Checked out {checked_out_count} participants"
    }


@router.get("/code/{join_code}/info")
async def get_code_info(
        join_code: str,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_staff_or_organizer)
):
    """
    🔍 ตรวจสอบข้อมูลจากรหัส (ก่อน check-in/check-out)
    """
    result = await db.execute(
        select(EventParticipation, User, Event)
        .join(User, EventParticipation.user_id == User.id)
        .join(Event, EventParticipation.event_id == Event.id)
        .where(EventParticipation.join_code == join_code)
    )

    row = result.first()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="รหัสไม่ถูกต้อง"
        )

    participation, user, event = row

    # ตรวจสอบว่าสามารถทำอะไรได้บ้าง
    can_check_in = participation.status == ParticipationStatus.JOINED
    can_check_out = participation.status == ParticipationStatus.CHECKED_IN
    can_complete = participation.status == ParticipationStatus.CHECKED_IN

    return {
        "join_code": join_code,
        "valid": True,
        "participation_id": participation.id,

        # User info
        "user": {
            "id": user.id,
            "full_name": f"{user.first_name} {user.last_name}",
            "email": user.email,
            "role": user.role.value
        },

        # Event info
        "event": {
            "id": event.id,
            "title": event.title,
            "date": event.event_date
        },

        # Current status
        "status": participation.status.value if hasattr(participation.status, 'value') else participation.status,
        "checked_in_at": participation.checked_in_at,
        "checked_out_at": participation.checked_out_at,

        # Available actions
        "actions": {
            "can_check_in": can_check_in,
            "can_check_out": can_check_out,
            "can_complete": can_complete
        }
    }


@router.get("/my-active-events")
async def get_my_active_events(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    📱 ดูงานที่ตัวเองกำลังเข้าร่วมอยู่
    """
    result = await db.execute(
        select(EventParticipation, Event)
        .join(Event, EventParticipation.event_id == Event.id)
        .where(
            EventParticipation.user_id == current_user.id,
            EventParticipation.status.in_([
                ParticipationStatus.JOINED,
                ParticipationStatus.CHECKED_IN
            ])
        )
        .order_by(EventParticipation.joined_at.desc())
    )

    active_events = []
    for participation, event in result.all():
        active_events.append({
            "participation_id": participation.id,
            "join_code": participation.join_code,
            "status": participation.status.value if hasattr(participation.status, 'value') else participation.status,
            "joined_at": participation.joined_at,
            "checked_in_at": participation.checked_in_at,
            "event": {
                "id": event.id,
                "title": event.title,
                "event_date": event.event_date,
                "location": event.location,
                "banner_image_url": event.banner_image_url
            }
        })

    return {
        "total": len(active_events),
        "active_events": active_events
    }


# ==========================================
# 📊 Report & Export Endpoints
# ==========================================

@router.get("/event/{event_id}/report")
async def get_event_report(
        event_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_staff_or_organizer)
):
    """
    📋 สรุปรายงานงาน (สำหรับแสดงผล)
    """
    # Get event info
    event = await event_crud.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Count by status
    status_result = await db.execute(
        select(
            EventParticipation.status,
            func.count(EventParticipation.id)
        )
        .where(EventParticipation.event_id == event_id)
        .group_by(EventParticipation.status)
    )
    by_status = {row[0]: row[1] for row in status_result.all()}

    # Average duration (check-in to check-out)
    duration_result = await db.execute(
        select(
            func.avg(
                func.extract('epoch', EventParticipation.checked_out_at - EventParticipation.checked_in_at)
            )
        )
        .where(
            EventParticipation.event_id == event_id,
            EventParticipation.checked_out_at.isnot(None),
            EventParticipation.checked_in_at.isnot(None)
        )
    )
    avg_duration_seconds = duration_result.scalar() or 0

    # Peak hour (hour with most check-ins)
    peak_hour_result = await db.execute(
        select(
            func.extract('hour', EventParticipation.checked_in_at).label('hour'),
            func.count(EventParticipation.id).label('count')
        )
        .where(
            EventParticipation.event_id == event_id,
            EventParticipation.checked_in_at.isnot(None)
        )
        .group_by(func.extract('hour', EventParticipation.checked_in_at))
        .order_by(func.count(EventParticipation.id).desc())
        .limit(1)
    )
    peak_hour = peak_hour_result.first()

    return {
        "event": {
            "id": event.id,
            "title": event.title,
            "date": event.event_date,
            "location": event.location
        },
        "summary": {
            "total_registered": sum(by_status.values()),
            "completed": by_status.get(ParticipationStatus.COMPLETED, 0),
            "checked_out": by_status.get(ParticipationStatus.CHECKED_OUT, 0),
            "currently_in": by_status.get(ParticipationStatus.CHECKED_IN, 0),
            "cancelled": by_status.get(ParticipationStatus.CANCELLED, 0)
        },
        "by_status": by_status,
        "metrics": {
            "average_duration_minutes": int(avg_duration_seconds / 60) if avg_duration_seconds else 0,
            "peak_check_in_hour": int(peak_hour[0]) if peak_hour else None,
            "peak_check_in_count": int(peak_hour[1]) if peak_hour else 0
        },
        "generated_at": datetime.now(timezone.utc)
    }


@router.get("/event/{event_id}/export-csv")
async def export_event_csv(
        event_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_organizer)
):
    """
    📥 Export ข้อมูลเป็น CSV (Organizer only)
    """
    # Get all participations
    result = await db.execute(
        select(EventParticipation, User)
        .join(User, EventParticipation.user_id == User.id)
        .where(EventParticipation.event_id == event_id)
        .order_by(EventParticipation.joined_at)
    )

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        'ID',
        'Join Code',
        'Full Name',
        'Email',
        'Role',
        'Status',
        'Joined At',
        'Checked In At',
        'Checked Out At',
        'Duration (minutes)',
        'Completed At',
        'Distance (km)',
        'Strava Link'
    ])

    # Data
    for participation, user in result.all():
        duration = None
        if participation.checked_in_at and participation.checked_out_at:
            duration = int((participation.checked_out_at - participation.checked_in_at).total_seconds() / 60)

        writer.writerow([
            participation.id,
            participation.join_code,
            f"{user.first_name} {user.last_name}",
            user.email,
            user.role.value,
            participation.status.value if hasattr(participation.status, 'value') else participation.status,
            participation.joined_at.isoformat() if participation.joined_at else '',
            participation.checked_in_at.isoformat() if participation.checked_in_at else '',
            participation.checked_out_at.isoformat() if participation.checked_out_at else '',
            duration or '',
            participation.completed_at.isoformat() if participation.completed_at else '',
            float(participation.actual_distance_km) if participation.actual_distance_km else '',
            participation.strava_link or ''
        ])

    # Get event for filename
    event = await event_crud.get_event_by_id(db, event_id)
    filename = f"event_{event_id}_{event.title.replace(' ', '_')}.csv"

    # Return as download
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.get("/event/{event_id}/timeline")
async def get_event_timeline(
        event_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_staff_or_organizer)
):
    """
    ⏱️ Timeline ของงาน (check-in/check-out timeline)
    """
    result = await db.execute(
        select(EventParticipation, User)
        .join(User, EventParticipation.user_id == User.id)
        .where(
            EventParticipation.event_id == event_id,
            EventParticipation.checked_in_at.isnot(None)
        )
        .order_by(EventParticipation.checked_in_at)
    )

    timeline = []
    for participation, user in result.all():
        # Check-in event
        timeline.append({
            "type": "check_in",
            "timestamp": participation.checked_in_at,
            "user_name": f"{user.first_name} {user.last_name}",
            "join_code": participation.join_code
        })

        # Check-out event
        if participation.checked_out_at:
            timeline.append({
                "type": "check_out",
                "timestamp": participation.checked_out_at,
                "user_name": f"{user.first_name} {user.last_name}",
                "join_code": participation.join_code
            })

    # Sort by timestamp
    timeline.sort(key=lambda x: x["timestamp"])

    return {
        "event_id": event_id,
        "total_events": len(timeline),
        "timeline": timeline
    }


# ==========================================
# ✅ Validation & Helper Endpoints
# ==========================================

@router.post("/validate-code")
async def validate_join_code(
        join_code: str,
        action: str,  # "check_in" or "check_out" or "complete"
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_staff_or_organizer)
):
    """
    ✅ ตรวจสอบความถูกต้องของรหัสก่อนดำเนินการ
    """
    # Get participation
    result = await db.execute(
        select(EventParticipation, User)
        .join(User, EventParticipation.user_id == User.id)
        .where(EventParticipation.join_code == join_code)
    )

    row = result.first()

    if not row:
        return {
            "valid": False,
            "message": "❌ รหัสไม่ถูกต้อง",
            "error_code": "INVALID_CODE"
        }

    participation, user = row
    current_status = participation.status.value if hasattr(participation.status, 'value') else participation.status

    if action == "check_in":
        if current_status != "joined":
            return {
                "valid": False,
                "message": f"❌ สถานะปัจจุบันคือ '{current_status}' - ไม่สามารถ check-in ได้",
                "current_status": current_status,
                "error_code": "ALREADY_CHECKED_IN"
            }

    elif action == "check_out":
        # ✅ FIX: เพิ่ม proof_submitted ให้เป็นสถานะที่ยอมรับได้
        # จากเดิม: if current_status != "checked_in":
        if current_status not in ["checked_in", "proof_submitted"]:
            return {
                "valid": False,
                "message": f"❌ สถานะปัจจุบันคือ '{current_status}' - ต้อง check-in ก่อน",
                "current_status": current_status,
                "error_code": "NOT_CHECKED_IN"
            }

    elif action == "complete":
        if current_status not in ["checked_in", "checked_out"]:
            return {
                "valid": False,
                "message": f"❌ สถานะปัจจุบันคือ '{current_status}' - ต้อง check-in ก่อน",
                "current_status": current_status,
                "error_code": "NOT_ELIGIBLE"
            }

    # Valid
    return {
        "valid": True,
        "message": f"✅ พร้อมสำหรับ {action}",
        "current_status": current_status,
        "user_info": {
            "id": user.id,
            "full_name": f"{user.first_name} {user.last_name}",
            "email": user.email,
            "role": user.role.value
        },
        "participation_info": {
            "id": participation.id,
            "event_id": participation.event_id,
            "joined_at": participation.joined_at,
            "checked_in_at": participation.checked_in_at,
            "checked_out_at": participation.checked_out_at
        }
    }


@router.get("/search")
async def search_participations(
        query: str,
        event_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 20,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_staff_or_organizer)
):
    """
    🔍 ค้นหาผู้เข้าร่วม
    """
    # Build query
    search_query = select(EventParticipation, User, Event) \
        .join(User, EventParticipation.user_id == User.id) \
        .join(Event, EventParticipation.event_id == Event.id)

    # Add search condition
    search_query = search_query.where(
        or_(
            User.first_name.ilike(f"%{query}%"),
            User.last_name.ilike(f"%{query}%"),
            User.email.ilike(f"%{query}%"),
            EventParticipation.join_code.ilike(f"%{query}%")
        )
    )

    # Filter by event
    if event_id:
        search_query = search_query.where(EventParticipation.event_id == event_id)

    # Filter by status
    if status:
        search_query = search_query.where(EventParticipation.status == status)

    search_query = search_query.limit(limit)

    result = await db.execute(search_query)

    results = []
    for participation, user, event in result.all():
        results.append({
            "participation_id": participation.id,
            "join_code": participation.join_code,
            "status": participation.status.value if hasattr(participation.status, 'value') else participation.status,
            "user": {
                "id": user.id,
                "full_name": f"{user.first_name} {user.last_name}",
                "email": user.email,
                "role": user.role.value
            },
            "event": {
                "id": event.id,
                "title": event.title,
                "date": event.event_date
            },
            "timestamps": {
                "joined_at": participation.joined_at,
                "checked_in_at": participation.checked_in_at,
                "checked_out_at": participation.checked_out_at
            }
        })

    return {
        "query": query,
        "total_found": len(results),
        "results": results
    }


@router.get("/quick-stats")
async def get_quick_stats(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_staff_or_organizer)
):
    """
    📊 สถิติรวมทั้งระบบ (Quick Overview)
    """
    # Total events
    total_events = await db.execute(
        select(func.count(Event.id))
    )

    # Total participations
    total_participations = await db.execute(
        select(func.count(EventParticipation.id))
        .where(EventParticipation.status != ParticipationStatus.CANCELLED)
    )

    # Active events (happening now)
    now = datetime.now(timezone.utc)
    active_events = await db.execute(
        select(func.count(Event.id))
        .where(
            Event.is_active == True,
            Event.event_date <= now,
            or_(
                Event.event_end_date.is_(None),
                Event.event_end_date >= now
            )
        )
    )

    # Today's check-ins
    today_start = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=timezone.utc)
    today_checkins = await db.execute(
        select(func.count(EventParticipation.id))
        .where(
            EventParticipation.checked_in_at >= today_start
        )
    )

    # Currently in events (checked-in but not checked-out)
    currently_in = await db.execute(
        select(func.count(EventParticipation.id))
        .where(EventParticipation.status == ParticipationStatus.CHECKED_IN)
    )

    return {
        "total_events": total_events.scalar() or 0,
        "total_participations": total_participations.scalar() or 0,
        "active_events": active_events.scalar() or 0,
        "today_checkins": today_checkins.scalar() or 0,
        "currently_in_events": currently_in.scalar() or 0,
        "timestamp": datetime.now(timezone.utc)
    }


@router.get("/event/{event_id}/proofs")
async def get_event_proofs(
        event_id: int,
        status: Optional[str] = None,  # "proof_submitted", "completed", "rejected"
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_staff_or_organizer)
):
    """
    📋 ดึงรายการ Proof ทั้งหมดของงาน (พร้อมรูปภาพ)
    Requires: Staff or Organizer role

    - **event_id**: ID ของงาน
    - **status**: กรองตาม status (optional)
      - "proof_submitted" - รอตรวจสอบ
      - "completed" - ผ่านแล้ว
      - "rejected" - ไม่ผ่าน

    **Returns:** รายการ proof พร้อม URL รูปภาพ
    """
    # Build query
    query = select(EventParticipation, User) \
        .join(User, EventParticipation.user_id == User.id) \
        .where(
        EventParticipation.event_id == event_id,
        EventParticipation.proof_image_url.isnot(None)  # มี proof เท่านั้น
    )

    # Filter by status
    if status:
        query = query.where(EventParticipation.status == status)
    else:
        # Default: ดึงเฉพาะที่ส่ง proof แล้ว
        query = query.where(
            EventParticipation.status.in_([
                'proof_submitted',
                'completed',
                'rejected'
            ])
        )

    query = query.order_by(EventParticipation.proof_submitted_at.desc())

    result = await db.execute(query)
    participations = result.all()

    # Format response
    proofs = []
    for participation, user in participations:
        # Safe value extraction
        def get_val(obj):
            return obj.value if hasattr(obj, 'value') else obj
        proofs.append({
            "participation_id": participation.id,
            "join_code": participation.join_code,
            "user": {
                "id": user.id,
                "full_name": f"{user.first_name} {user.last_name}",
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "role": get_val(user.role)
            },
            "status": get_val(participation.status),

            # 🖼️ Proof Image URL - ใช้ตัวนี้แสดงรูป
            "proof_image_url": participation.proof_image_url,
            "proof_image_hash": participation.proof_image_hash,
            "proof_submitted_at": participation.proof_submitted_at,

            # Strava & Distance
            "strava_link": participation.strava_link,
            "actual_distance_km": float(participation.actual_distance_km) if participation.actual_distance_km else None,

            # Timestamps
            "joined_at": participation.joined_at,
            "checked_in_at": participation.checked_in_at,
            "completed_at": participation.completed_at,

            # Rejection info
            "rejection_reason": participation.rejection_reason,
            "rejected_at": participation.rejected_at
        })

    return {
        "event_id": event_id,
        "total_proofs": len(proofs),
        "proofs": proofs
    }


@router.get("/pending-proofs")
async def get_pending_proofs_all_events(
        limit: int = 50,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_staff_or_organizer)
):
    """
    🔍 ดึงรายการ Proof ที่รอตรวจสอบทั้งหมด (ทุกงาน)
    Requires: Staff or Organizer role

    ใช้สำหรับ Dashboard - แสดงรายการที่ต้อง verify
    """
    query = select(EventParticipation, User, Event) \
        .join(User, EventParticipation.user_id == User.id) \
        .join(Event, EventParticipation.event_id == Event.id) \
        .where(
        EventParticipation.status == 'proof_submitted',
        EventParticipation.proof_image_url.isnot(None)
    ) \
        .order_by(EventParticipation.proof_submitted_at.asc()) \
        .limit(limit)

    result = await db.execute(query)
    participations = result.all()

    pending = []
    for participation, user, event in participations:
        def get_val(obj):
            return obj.value if hasattr(obj, 'value') else obj

        pending.append({
            "participation_id": participation.id,
            "event": {
                "id": event.id,
                "title": event.title,
                "event_date": event.event_date
            },
            "user": {
                "id": user.id,
                "full_name": f"{user.first_name} {user.last_name}",
                "email": user.email,
                "role": get_val(user.role)
            },
            "proof_image_url": participation.proof_image_url,
            "proof_submitted_at": participation.proof_submitted_at,
            "strava_link": participation.strava_link,
            "actual_distance_km": float(participation.actual_distance_km) if participation.actual_distance_km else None,

            # Time waiting
            "waiting_minutes": int((datetime.now(
                timezone.utc) - participation.proof_submitted_at).total_seconds() / 60) if participation.proof_submitted_at else 0
        })

    return {
        "total_pending": len(pending),
        "pending_proofs": pending
    }

# ==========================================
# MOVED GENERIC GETTER TO BOTTOM (MUST BE LAST)
# ==========================================
# ⚠️ WARNING: This route MUST be at the very end of the file
# because it matches ANY path like /{participation_id}
# and will conflict with routes like /check-in, /check-in-daily, etc.

@router.get("/{participation_id}", response_model=EventParticipationRead)
async def get_participation(
        participation_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get specific participation by ID - MUST BE LAST ROUTE"""
    participation = await event_participation_crud.get_participation_by_id(db, participation_id)
    if not participation:
        raise HTTPException(status_code=404, detail="Participation not found")

    if participation.user_id != current_user.id and current_user.role.value not in ['staff', 'organizer']:
        raise HTTPException(status_code=403, detail="Access denied")

    return participation