"""
API Endpoints for Participant Snapshots
"""
from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from src.api.dependencies.auth import (
    get_db,
    get_current_user,
    require_staff_or_organizer
)
from src.crud import participant_snapshot_crud
from src.schemas.participant_snapshot_schema import (
    ParticipantSnapshotRead,
    SnapshotListResponse,
    SnapshotEntriesResponse
)
from src.models.user import User

router = APIRouter()


# ========================================
# Snapshot Endpoints
# ========================================

@router.get(
    "/events/{event_id}/participants/history",
    response_model=SnapshotListResponse,
    summary="Get participant snapshots history"
)
async def get_participant_snapshots(
    event_id: int = Path(..., description="Event ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_or_organizer)
):
    """
    📚 ดึง list ของ participant snapshots สำหรับ event
    
    - **event_id**: ID ของ event
    - **page**: หน้าที่ต้องการ (เริ่มจาก 1)
    - **page_size**: จำนวนรายการต่อหน้า (max 100)
    
    Returns:
    - List ของ snapshots พร้อม pagination info
    """
    return await participant_snapshot_crud.get_snapshots_by_event(
        db, event_id, page, page_size
    )


@router.get(
    "/events/{event_id}/participants/history/{snapshot_id}/entries",
    response_model=SnapshotEntriesResponse,
    summary="Get snapshot entries"
)
async def get_snapshot_entries(
    event_id: int = Path(..., description="Event ID"),
    snapshot_id: str = Path(..., description="Snapshot ID (UUID)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_or_organizer)
):
    """
    📋 ดึง entries ของ snapshot
    
    - **event_id**: ID ของ event
    - **snapshot_id**: UUID ของ snapshot
    - **page**: หน้าที่ต้องการ (เริ่มจาก 1)
    - **page_size**: จำนวนรายการต่อหน้า (max 200)
    
    Returns:
    - List ของ participant entries พร้อม pagination info
    """
    return await participant_snapshot_crud.get_snapshot_entries(
        db, snapshot_id, page, page_size
    )


@router.post(
    "/events/{event_id}/participants/snapshots",
    response_model=ParticipantSnapshotRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new snapshot"
)
async def create_participant_snapshot(
    event_id: int = Path(..., description="Event ID"),
    description: Optional[str] = Query(None, description="Snapshot description"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_or_organizer)
):
    """
    📸 สร้าง snapshot ใหม่ของ participants
    
    - **event_id**: ID ของ event
    - **description**: คำอธิบาย snapshot (optional)
    
    Returns:
    - Snapshot ที่สร้างขึ้น พร้อม snapshot_id และ entry_count
    """
    snapshot = await participant_snapshot_crud.create_snapshot(
        db, 
        event_id=event_id, 
        created_by=current_user.id,
        description=description
    )
    
    return ParticipantSnapshotRead(
        id=snapshot.id,
        snapshot_id=snapshot.snapshot_id,
        event_id=snapshot.event_id,
        snapshot_time=snapshot.snapshot_time,
        entry_count=snapshot.entry_count,
        created_by=snapshot.created_by,
        description=snapshot.description
    )


@router.delete(
    "/events/{event_id}/participants/history/{snapshot_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a snapshot"
)
async def delete_participant_snapshot(
    event_id: int = Path(..., description="Event ID"),
    snapshot_id: str = Path(..., description="Snapshot ID (UUID)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_or_organizer)
):
    """
    🗑️ ลบ snapshot
    
    - **event_id**: ID ของ event
    - **snapshot_id**: UUID ของ snapshot
    
    Note: จะลบ entries ทั้งหมดที่เกี่ยวข้องด้วย (cascade delete)
    """
    deleted = await participant_snapshot_crud.delete_snapshot(db, snapshot_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Snapshot not found"
        )
    
    return None
