from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict

from src.api.dependencies.auth import (
    get_db,
    get_current_user,
    require_staff_or_organizer
)
from src.crud import event_participation_crud, reward_crud, event_crud
from src.schemas.event_participation_schema import (
    EventParticipationCreate,
    EventParticipationRead,
    EventParticipationCheckIn,
    EventParticipationProofSubmit,
    EventParticipationVerify,
    EventParticipationCancel,
    UserStatistics
)
from src.models.user import User
from src.models.event_participation import ParticipationStatus

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


@router.get("/{participation_id}", response_model=EventParticipationRead)
async def get_participation(
        participation_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    participation = await event_participation_crud.get_participation_by_id(db, participation_id)
    if not participation:
        raise HTTPException(status_code=404, detail="Participation not found")

    if participation.user_id != current_user.id and current_user.role.value not in ['staff', 'organizer']:
        raise HTTPException(status_code=403, detail="Access denied")

    return participation


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
    # ... (Logic identical to your input, kept brief for clarity)
    image_hash = getattr(proof_data, 'image_hash', None)
    if not image_hash:
        from src.utils.image_hash import calculate_image_hash
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
        from src.utils.image_hash import calculate_image_hash
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
        await reward_crud.check_and_award_rewards(db, participation.user_id)
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

    สำหรับกิจกรรมที่อนุญาตให้ลงทะเบียนได้หลายครั้ง (1 ครั้งต่อวัน)
    """
    return await event_participation_crud.create_daily_participation(
        db, participation, current_user.id
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
    from sqlalchemy.future import select
    from src.models.event_participation import EventParticipation

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