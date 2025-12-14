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
    EventParticipationVerify
)
from src.models.user import User
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

    **ระบบจะตรวจสอบความจุก่อนอนุญาตให้ join**

    - ตรวจสอบว่างานเต็มหรือไม่
    - ตรวจสอบว่างาน active และ published หรือไม่
    - สร้าง join_code (5 หลัก) อัตโนมัติ
    - ส่งการแจ้งเตือนอัตโนมัติ
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

    # สร้าง participation
    return await event_participation_crud.create_participation(db, participation, current_user.id)


@router.get("/user/{user_id}", response_model=List[EventParticipationRead])
async def get_user_participations(
        user_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get all participations for a user
    Requires: User can only view their own or staff/organizer can view any

    ดึงข้อมูลการเข้าร่วมงานทั้งหมดของผู้ใช้
    """
    if current_user.id != user_id and current_user.role.value not in ['staff', 'organizer']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own participations"
        )
    return await event_participation_crud.get_participations_by_user(db, user_id)


@router.get("/event/{event_id}", response_model=List[EventParticipationRead])
async def get_event_participations(
        event_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_staff_or_organizer)
):
    """
    Get all participations for an event
    Requires: Staff or Organizer role

    ดึงข้อมูลผู้เข้าร่วมทั้งหมดในงาน (สำหรับ Staff)
    """
    return await event_participation_crud.get_participations_by_event(db, event_id)


@router.get("/{participation_id}", response_model=EventParticipationRead)
async def get_participation(
        participation_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get participation by ID
    Requires: Own participation or staff/organizer

    ดึงข้อมูลการเข้าร่วมตาม ID
    """
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
    """
    Check-in participant
    Requires: Staff or Organizer role

    Staff ใช้ join_code (5 หลัก) เพื่อ check-in ผู้เข้าร่วม
    - Status จะเปลี่ยนจาก JOINED → CHECKED_IN
    - ส่งการแจ้งเตือนอัตโนมัติ
    """
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
    Submit proof of completion
    Requires: Own participation

    ผู้เข้าร่วมส่งหลักฐานการวิ่ง (รูปภาพ)
    - Status จะเปลี่ยนจาก CHECKED_IN → PROOF_SUBMITTED
    - ส่งการแจ้งเตือนอัตโนมัติ
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
        db, participation_id, proof_data.proof_image_url
    )
    if not participation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid participation or not checked in"
        )
    return participation


@router.post("/verify", response_model=EventParticipationRead)
async def verify_completion(
        verify_data: EventParticipationVerify,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_staff_or_organizer)
):
    """
    Verify completion
    Requires: Staff or Organizer role

    Staff ตรวจสอบหลักฐานและอนุมัติ/ปฏิเสธ
    - อนุมัติ: Status → COMPLETED, ได้ completion_code (10 ตัวอักษร)
    - ปฏิเสธ: Status → REJECTED
    - ระบบจะตรวจสอบและมอบรางวัลอัตโนมัติถ้าผ่าน
    - ส่งการแจ้งเตือนอัตโนมัติ
    """
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


@router.delete("/{participation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_participation(
        participation_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Cancel participation
    Requires: Own participation

    ยกเลิกการเข้าร่วมงาน
    - Status → CANCELLED
    """
    participation = await event_participation_crud.cancel_participation(
        db, participation_id, current_user.id
    )
    if not participation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participation not found or unauthorized"
        )
    return None