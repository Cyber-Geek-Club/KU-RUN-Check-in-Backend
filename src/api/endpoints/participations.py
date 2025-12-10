from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.db_config import SessionLocal
from src.crud import event_participation_crud, reward_crud
from src.schemas.event_participation_schema import (
    EventParticipationCreate,
    EventParticipationRead,
    EventParticipationCheckIn,
    EventParticipationProofSubmit,
    EventParticipationVerify
)
from typing import List

router = APIRouter()


async def get_db():
    async with SessionLocal() as session:
        yield session


# TODO: Add authentication dependency to get current user
async def get_current_user_id():
    """Mock function - replace with actual JWT authentication"""
    return 1  # Mock user ID


@router.post("/join", response_model=EventParticipationRead, status_code=status.HTTP_201_CREATED)
async def join_event(
        participation: EventParticipationCreate,
        db: AsyncSession = Depends(get_db),
        current_user_id: int = Depends(get_current_user_id)
):
    """
    Join an event

    - **event_id**: ID ของงานที่ต้องการเข้าร่วม
    - Returns: ข้อมูล participation พร้อม join_code (5 หลัก)
    """
    return await event_participation_crud.create_participation(db, participation, current_user_id)


@router.get("/user/{user_id}", response_model=List[EventParticipationRead])
async def get_user_participations(user_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get all participations for a user

    ดึงข้อมูลการเข้าร่วมงานทั้งหมดของผู้ใช้
    """
    return await event_participation_crud.get_participations_by_user(db, user_id)


@router.get("/event/{event_id}", response_model=List[EventParticipationRead])
async def get_event_participations(event_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get all participations for an event

    ดึงข้อมูลผู้เข้าร่วมทั้งหมดในงาน (สำหรับ Staff)
    """
    return await event_participation_crud.get_participations_by_event(db, event_id)


@router.get("/{participation_id}", response_model=EventParticipationRead)
async def get_participation(participation_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get participation by ID

    ดึงข้อมูลการเข้าร่วมตาม ID
    """
    participation = await event_participation_crud.get_participation_by_id(db, participation_id)
    if not participation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participation not found"
        )
    return participation


@router.post("/check-in", response_model=EventParticipationRead)
async def check_in(
        check_in_data: EventParticipationCheckIn,
        db: AsyncSession = Depends(get_db),
        staff_id: int = Depends(get_current_user_id)
):
    """
    Check-in participant (Staff only)

    Staff ใช้ join_code (5 หลัก) เพื่อ check-in ผู้เข้าร่วม
    - Status จะเปลี่ยนจาก JOINED → CHECKED_IN
    """
    participation = await event_participation_crud.check_in_participation(
        db, check_in_data.join_code, staff_id
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
        current_user_id: int = Depends(get_current_user_id)
):
    """
    Submit proof of completion

    ผู้เข้าร่วมส่งหลักฐานการวิ่ง (รูปภาพ)
    - Status จะเปลี่ยนจาก CHECKED_IN → PROOF_SUBMITTED
    """
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
        staff_id: int = Depends(get_current_user_id)
):
    """
    Verify completion (Staff only)

    Staff ตรวจสอบหลักฐานและอนุมัติ/ปฏิเสธ
    - อนุมัติ: Status → COMPLETED, ได้ completion_code (10 ตัวอักษร)
    - ปฏิเสธ: Status → REJECTED
    - ระบบจะตรวจสอบและมอบรางวัลอัตโนมัติถ้าผ่าน
    """
    participation = await event_participation_crud.verify_completion(
        db,
        verify_data.participation_id,
        staff_id,
        verify_data.approved,
        verify_data.rejection_reason
    )
    if not participation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid participation or proof not submitted"
        )

    # Check and award rewards if completed
    if verify_data.approved:
        await reward_crud.check_and_award_rewards(db, participation.user_id)

    return participation


@router.delete("/{participation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_participation(
        participation_id: int,
        db: AsyncSession = Depends(get_db),
        current_user_id: int = Depends(get_current_user_id)
):
    """
    Cancel participation

    ยกเลิกการเข้าร่วมงาน
    - Status → CANCELLED
    """
    participation = await event_participation_crud.cancel_participation(
        db, participation_id, current_user_id
    )
    if not participation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participation not found or unauthorized"
        )
    return None