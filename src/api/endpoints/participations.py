from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
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
from typing import List

router = APIRouter()


@router.post("/join", response_model=EventParticipationRead, status_code=status.HTTP_201_CREATED)
async def join_event(
        participation: EventParticipationCreate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Join an event with capacity check
    Requires: Any authenticated user
    """
    # ตรวจสอบความจุก่อน
    capacity = await event_crud.check_event_capacity(db, participation.event_id)

    if not capacity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    if not capacity["can_join"]:
        if capacity["is_full"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Event is full. Maximum participants: {capacity['max_participants']}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event is not available for registration"
            )

    return await event_participation_crud.create_participation(db, participation, current_user.id)


@router.get("/user/{user_id}", response_model=List[EventParticipationRead])
async def get_user_participations(
        user_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get all participations for a user"""
    if current_user.id != user_id and current_user.role.value not in ['staff', 'organizer']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own participations"
        )
    return await event_participation_crud.get_participations_by_user(db, user_id)


@router.get("/user/{user_id}/statistics", response_model=UserStatistics)
async def get_user_statistics(
        user_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get user running statistics
    Requires: User can view their own stats or staff/organizer can view any

    ดึงสถิติการวิ่งของผู้ใช้:
    - จำนวนงานที่ลงทะเบียนทั้งหมด
    - จำนวนงานที่วิ่งสำเร็จ
    - ระยะทางรวมที่วิ่ง (กม.)
    - เปอร์เซ็นต์ความสำเร็จ
    - จำนวนครั้งที่วิ่งสำเร็จในเดือนนี้
    """
    # Users can only view their own stats, unless they're staff/organizer
    if current_user.id != user_id and current_user.role.value not in ['staff', 'organizer']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own statistics"
        )

    return await event_participation_crud.get_user_statistics(db, user_id)


@router.get("/event/{event_id}", response_model=List[EventParticipationRead])
async def get_event_participations(
        event_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_staff_or_organizer)
):
    """Get all participations for an event (Staff/Organizer only)"""
    return await event_participation_crud.get_participations_by_event(db, event_id)


@router.get("/{participation_id}", response_model=EventParticipationRead)
async def get_participation(
        participation_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get participation by ID"""
    participation = await event_participation_crud.get_participation_by_id(db, participation_id)
    if not participation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participation not found"
        )

    if participation.user_id != current_user.id and current_user.role.value not in ['staff', 'organizer']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return participation


@router.post("/check-in", response_model=EventParticipationRead)
async def check_in(
        check_in_data: EventParticipationCheckIn,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_staff_or_organizer)
):
    """Check-in participant using join_code (Staff/Organizer only)"""
    participation = await event_participation_crud.check_in_participation(
        db, check_in_data.join_code, current_user.id
    )
    if not participation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid join code or already checked in"
        )
    return participation


@router.post("/{participation_id}/submit-proof", response_model=EventParticipationRead)
async def submit_proof(
        participation_id: int,
        proof_data: EventParticipationProofSubmit,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Submit proof of completion with optional Strava link and actual distance
    Requires: Own participation

    ส่งหลักฐานการวิ่ง:
    - รูปภาพ (จำเป็น)
    - ลิงก์ Strava (ไม่บังคับ)
    - ระยะทางจริงที่วิ่ง กม. (ไม่บังคับ)
    """
    participation = await event_participation_crud.get_participation_by_id(db, participation_id)
    if not participation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participation not found"
        )

    if participation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only submit proof for your own participation"
        )

    participation = await event_participation_crud.submit_proof(
        db,
        participation_id,
        proof_data.proof_image_url,
        proof_data.strava_link,
        proof_data.actual_distance_km
    )
    if not participation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid participation or not checked in"
        )
    return participation


@router.put("/{participation_id}/resubmit-proof", response_model=EventParticipationRead)
async def resubmit_proof(
        participation_id: int,
        proof_data: EventParticipationProofSubmit,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Resubmit proof after rejection with updated info
    Requires: Own participation with REJECTED status
    """
    participation = await event_participation_crud.get_participation_by_id(db, participation_id)
    if not participation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participation not found"
        )

    if participation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only resubmit proof for your own participation"
        )

    if participation.status != ParticipationStatus.REJECTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot resubmit proof. Current status: {participation.status.value}"
        )

    participation = await event_participation_crud.resubmit_proof(
        db,
        participation_id,
        proof_data.proof_image_url,
        proof_data.strava_link,
        proof_data.actual_distance_km
    )

    if not participation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to resubmit proof"
        )

    return participation


@router.post("/verify", response_model=EventParticipationRead)
async def verify_completion(
        verify_data: EventParticipationVerify,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_staff_or_organizer)
):
    """Verify completion (approve/reject) - Staff/Organizer only"""
    participation = await event_participation_crud.verify_completion(
        db,
        verify_data.participation_id,
        current_user.id,
        verify_data.approved,
        verify_data.rejection_reason
    )
    if not participation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid participation or proof not submitted"
        )

    # ตรวจสอบและมอบรางวัลถ้าอนุมัติ
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
    """Cancel participation with reason"""
    participation = await event_participation_crud.cancel_participation(
        db, participation_id, current_user.id, cancel_data.cancellation_reason
    )

    if not participation:
        existing = await event_participation_crud.get_participation_by_id(db, participation_id)

        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Participation not found"
            )

        if existing.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only cancel your own participation"
            )

        if existing.status in [ParticipationStatus.COMPLETED, ParticipationStatus.REJECTED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel participation with status: {existing.status.value}"
            )

    return participation


@router.delete("/{participation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_participation(
        participation_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_staff_or_organizer)
):
    """Delete participation (Staff/Organizer only)"""
    participation = await event_participation_crud.get_participation_by_id(db, participation_id)

    if not participation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participation not found"
        )

    await db.delete(participation)
    await db.commit()

    return None