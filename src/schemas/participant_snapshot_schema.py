"""
Schemas for Participant Snapshots
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Any
from datetime import datetime


# ========================================
# Snapshot Schemas
# ========================================

class ParticipantSnapshotBase(BaseModel):
    """Base schema for snapshot"""
    event_id: int
    description: Optional[str] = None


class ParticipantSnapshotCreate(ParticipantSnapshotBase):
    """Schema for creating a new snapshot"""
    created_by: Optional[int] = None


class ParticipantSnapshotRead(ParticipantSnapshotBase):
    """Schema for reading snapshot info"""
    id: int
    snapshot_id: str
    snapshot_time: datetime
    entry_count: int
    created_by: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ParticipantSnapshotSummary(BaseModel):
    """Summary info for snapshot list"""
    id: int
    snapshot_id: str
    snapshot_time: datetime
    entry_count: int
    description: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


# ========================================
# Entry Schemas
# ========================================

class ParticipantSnapshotEntryBase(BaseModel):
    """Base schema for snapshot entry"""
    participation_id: Optional[int] = None
    user_id: int
    user_name: str
    user_email: Optional[str] = None
    action: str
    status: str


class ParticipantSnapshotEntryCreate(ParticipantSnapshotEntryBase):
    """Schema for creating entry"""
    snapshot_id: int
    joined_at: Optional[datetime] = None
    checked_in_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Optional[dict] = None


class ParticipantSnapshotEntryRead(ParticipantSnapshotEntryBase):
    """Schema for reading entry"""
    id: int
    entry_id: str
    snapshot_id: int
    created_at: datetime
    joined_at: Optional[datetime] = None
    checked_in_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


# ========================================
# Response Schemas with Pagination
# ========================================

class SnapshotListResponse(BaseModel):
    """Response for snapshot list with pagination"""
    total: int
    page: int
    page_size: int
    total_pages: int
    snapshots: List[ParticipantSnapshotSummary]


class SnapshotEntriesResponse(BaseModel):
    """Response for snapshot entries with pagination"""
    snapshot_id: str
    snapshot_time: datetime
    total_entries: int
    page: int
    page_size: int
    total_pages: int
    entries: List[ParticipantSnapshotEntryRead]
