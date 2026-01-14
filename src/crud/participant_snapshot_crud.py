"""
CRUD operations for Participant Snapshots
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict
from datetime import datetime, timezone
import math

from src.models.participant_snapshot import ParticipantSnapshot, ParticipantSnapshotEntry
from src.models.event_participation import EventParticipation
from src.models.user import User
from src.schemas.participant_snapshot_schema import (
    ParticipantSnapshotCreate,
    SnapshotListResponse,
    SnapshotEntriesResponse,
    ParticipantSnapshotSummary,
    ParticipantSnapshotEntryRead
)
from fastapi import HTTPException, status


# ========================================
# Snapshot CRUD
# ========================================

async def create_snapshot(
    db: AsyncSession,
    event_id: int,
    created_by: Optional[int] = None,
    description: Optional[str] = None
) -> ParticipantSnapshot:
    """
    สร้าง snapshot ใหม่และเก็บข้อมูล participants ปัจจุบัน
    """
    # สร้าง snapshot
    snapshot = ParticipantSnapshot(
        event_id=event_id,
        created_by=created_by,
        description=description
    )
    
    db.add(snapshot)
    await db.flush()  # Get snapshot.id
    
    # ดึงข้อมูล participants ปัจจุบัน
    result = await db.execute(
        select(EventParticipation)
        .options(selectinload(EventParticipation.user))
        .where(EventParticipation.event_id == event_id)
        .order_by(EventParticipation.joined_at.desc())
    )
    participations = result.scalars().all()
    
    # สร้าง entries
    entry_count = 0
    for p in participations:
        # เตรียม metadata
        metadata = {
            "join_code": p.join_code,
            "completion_code": p.completion_code,
        }
        
        # เพิ่มข้อมูลเพิ่มเติมถ้ามี
        if p.checkin_date:
            metadata["checkin_date"] = p.checkin_date.isoformat()
        if p.proof_image_url:
            metadata["proof_image_url"] = p.proof_image_url
        if p.strava_link:
            metadata["strava_link"] = p.strava_link
        if p.actual_distance_km:
            metadata["actual_distance_km"] = float(p.actual_distance_km)
        
        entry = ParticipantSnapshotEntry(
            snapshot_id=snapshot.id,
            participation_id=p.id,
            user_id=p.user_id,
            user_name=p.user.full_name if p.user else "Unknown",
            user_email=p.user.email if p.user else None,
            action=p.status.value if hasattr(p.status, 'value') else p.status,
            status=p.status.value if hasattr(p.status, 'value') else p.status,
            joined_at=p.joined_at,
            checked_in_at=p.checked_in_at,
            completed_at=p.completed_at,
            metadata=metadata
        )
        
        db.add(entry)
        entry_count += 1
    
    # อัพเดท entry_count
    snapshot.entry_count = entry_count
    
    await db.commit()
    await db.refresh(snapshot)
    
    return snapshot


async def get_snapshots_by_event(
    db: AsyncSession,
    event_id: int,
    page: int = 1,
    page_size: int = 20
) -> SnapshotListResponse:
    """
    ดึง list ของ snapshots สำหรับ event
    """
    # นับจำนวนทั้งหมด
    count_result = await db.execute(
        select(func.count(ParticipantSnapshot.id))
        .where(ParticipantSnapshot.event_id == event_id)
    )
    total = count_result.scalar() or 0
    
    # คำนวณ pagination
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    offset = (page - 1) * page_size
    
    # ดึงข้อมูล
    result = await db.execute(
        select(ParticipantSnapshot)
        .where(ParticipantSnapshot.event_id == event_id)
        .order_by(desc(ParticipantSnapshot.snapshot_time))
        .offset(offset)
        .limit(page_size)
    )
    snapshots = result.scalars().all()
    
    # แปลงเป็น schema
    snapshot_summaries = [
        ParticipantSnapshotSummary(
            id=s.id,
            snapshot_id=s.snapshot_id,
            snapshot_time=s.snapshot_time,
            entry_count=s.entry_count,
            description=s.description
        )
        for s in snapshots
    ]
    
    return SnapshotListResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        snapshots=snapshot_summaries
    )


async def get_snapshot_by_id(
    db: AsyncSession,
    snapshot_id: str
) -> Optional[ParticipantSnapshot]:
    """
    ดึง snapshot ตาม snapshot_id
    """
    result = await db.execute(
        select(ParticipantSnapshot)
        .where(ParticipantSnapshot.snapshot_id == snapshot_id)
    )
    return result.scalar_one_or_none()


async def get_snapshot_entries(
    db: AsyncSession,
    snapshot_id: str,
    page: int = 1,
    page_size: int = 50
) -> SnapshotEntriesResponse:
    """
    ดึง entries ของ snapshot
    """
    # ตรวจสอบว่า snapshot มีอยู่จริง
    snapshot = await get_snapshot_by_id(db, snapshot_id)
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Snapshot not found"
        )
    
    # นับจำนวนทั้งหมด
    count_result = await db.execute(
        select(func.count(ParticipantSnapshotEntry.id))
        .where(ParticipantSnapshotEntry.snapshot_id == snapshot.id)
    )
    total = count_result.scalar() or 0
    
    # คำนวณ pagination
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    offset = (page - 1) * page_size
    
    # ดึงข้อมูล
    result = await db.execute(
        select(ParticipantSnapshotEntry)
        .where(ParticipantSnapshotEntry.snapshot_id == snapshot.id)
        .order_by(desc(ParticipantSnapshotEntry.created_at))
        .offset(offset)
        .limit(page_size)
    )
    entries = result.scalars().all()
    
    # แปลงเป็น schema
    entry_reads = [
        ParticipantSnapshotEntryRead(
            id=e.id,
            entry_id=e.entry_id,
            snapshot_id=e.snapshot_id,
            participation_id=e.participation_id,
            user_id=e.user_id,
            user_name=e.user_name,
            user_email=e.user_email,
            action=e.action,
            status=e.status,
            created_at=e.created_at,
            joined_at=e.joined_at,
            checked_in_at=e.checked_in_at,
            completed_at=e.completed_at,
            metadata=e.metadata
        )
        for e in entries
    ]
    
    return SnapshotEntriesResponse(
        snapshot_id=snapshot.snapshot_id,
        snapshot_time=snapshot.snapshot_time,
        total_entries=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        entries=entry_reads
    )


async def delete_snapshot(
    db: AsyncSession,
    snapshot_id: str
) -> bool:
    """
    ลบ snapshot (และ entries ทั้งหมดที่เกี่ยวข้อง)
    """
    snapshot = await get_snapshot_by_id(db, snapshot_id)
    if not snapshot:
        return False
    
    await db.delete(snapshot)
    await db.commit()
    
    return True
