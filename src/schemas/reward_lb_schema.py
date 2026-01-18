"""
Reward Leaderboard Schemas
Save as: src/schemas/reward_lb_schema.py
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime
from typing import Optional, List, Dict, Any


# ========== Reward Tier Configuration ==========

class RewardTier(BaseModel):
    """Single reward tier configuration"""
    tier: int = Field(..., ge=1, description="Tier number (1, 2, 3...)")
    min_rank: int = Field(..., ge=1, description="Minimum rank (1 = first place)")
    max_rank: int = Field(..., ge=1, description="Maximum rank")
    reward_id: int = Field(..., description="Reward ID to give")
    reward_name: Optional[str] = Field(None, description="Reward name (for display)")
    quantity: int = Field(..., ge=1, description="Number of rewards available")
    required_completions: Optional[int] = Field(None, ge=1, description="Required completions for this tier (overrides config default)")

    @field_validator('max_rank')
    @classmethod
    def validate_max_rank(cls, v, info):
        if 'min_rank' in info.data and v < info.data['min_rank']:
            raise ValueError('max_rank must be >= min_rank')
        return v


# ========== Leaderboard Config Schemas ==========

class LeaderboardConfigBase(BaseModel):
    """Base leaderboard configuration"""
    event_id: int
    name: str = Field(..., max_length=255, description="Config name")
    description: Optional[str] = None
    required_completions: int = Field(30, ge=1, le=365, description="Required runs (e.g., 30)")
    max_reward_recipients: int = Field(200, ge=1, description="Max people who can receive rewards")
    reward_tiers: List[RewardTier] = Field(..., min_length=1, description="Reward tier list")
    starts_at: datetime = Field(..., description="When leaderboard tracking starts")
    ends_at: datetime = Field(..., description="When leaderboard tracking ends")

    @field_validator('ends_at')
    @classmethod
    def validate_dates(cls, v, info):
        if 'starts_at' in info.data and v <= info.data['starts_at']:
            raise ValueError('ends_at must be after starts_at')
        return v


class LeaderboardConfigCreate(LeaderboardConfigBase):
    """Create new leaderboard configuration"""

    @field_validator('reward_tiers')
    @classmethod
    def validate_reward_tiers(cls, v):
        if not v:
            raise ValueError('At least one reward tier is required')

        # Check tier numbers are sequential
        tier_numbers = sorted([t.tier for t in v])
        expected = list(range(1, len(v) + 1))
        if tier_numbers != expected:
            raise ValueError(f'Tier numbers must be sequential: {expected}')

        # Check for rank overlaps
        tiers_sorted = sorted(v, key=lambda x: x.min_rank)
        for i in range(len(tiers_sorted) - 1):
            if tiers_sorted[i].max_rank >= tiers_sorted[i + 1].min_rank:
                raise ValueError(f'Tier ranks overlap: Tier {tiers_sorted[i].tier} and {tiers_sorted[i + 1].tier}')

        return v


class LeaderboardConfigUpdate(BaseModel):
    """Update leaderboard configuration"""
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    required_completions: Optional[int] = Field(None, ge=1, le=365)
    max_reward_recipients: Optional[int] = Field(None, ge=1)
    reward_tiers: Optional[List[RewardTier]] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    is_active: Optional[bool] = None

    @field_validator('reward_tiers')
    @classmethod
    def validate_reward_tiers(cls, v):
        if v is None:
            return v

        if not v:
            raise ValueError('At least one reward tier is required')

        # Check tier numbers are sequential
        tier_numbers = sorted([t.tier for t in v])
        expected = list(range(1, len(v) + 1))
        if tier_numbers != expected:
            raise ValueError(f'Tier numbers must be sequential: {expected}')

        # Check for rank overlaps
        tiers_sorted = sorted(v, key=lambda x: x.min_rank)
        for i in range(len(tiers_sorted) - 1):
            if tiers_sorted[i].max_rank >= tiers_sorted[i + 1].min_rank:
                raise ValueError(f'Tier ranks overlap: Tier {tiers_sorted[i].tier} and {tiers_sorted[i + 1].tier}')

        return v


class LeaderboardConfigRead(LeaderboardConfigBase):
    """Read leaderboard configuration"""
    id: int
    is_active: bool
    finalized_at: Optional[datetime] = None
    created_by: int
    created_at: datetime
    updated_at: datetime

    # Computed fields
    total_reward_slots: Optional[int] = Field(None, description="Total reward slots available")
    total_qualified: Optional[int] = Field(None, description="Number of people who qualified")
    total_rewarded: Optional[int] = Field(None, description="Number of people rewarded")
    is_finalized: Optional[bool] = Field(None, description="Is leaderboard finalized?")

    model_config = ConfigDict(from_attributes=True)


# ========== Leaderboard Entry Schemas ==========

class LeaderboardEntryBase(BaseModel):
    """Base leaderboard entry"""
    config_id: int
    user_id: int


class LeaderboardEntryRead(LeaderboardEntryBase):
    """Read leaderboard entry"""
    id: int
    total_completions: int
    completed_event_participations: List[int] = []
    rank: Optional[int] = None
    qualified_at: Optional[datetime] = None
    reward_id: Optional[int] = None
    reward_tier: Optional[int] = None
    rewarded_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    # User info (joined)
    user_full_name: Optional[str] = None
    user_email: Optional[str] = None
    user_role: Optional[str] = None

    # Reward info (joined)
    reward_name: Optional[str] = None
    reward_description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class LeaderboardEntryWithDetails(LeaderboardEntryRead):
    """Entry with full user and reward details"""
    user: Optional[Dict[str, Any]] = None
    reward: Optional[Dict[str, Any]] = None
    event_details: Optional[List[Dict[str, Any]]] = None


# ========== Public User View ==========

class UserLeaderboardStatus(BaseModel):
    """User's status in a leaderboard"""
    config_id: int
    event_id: int
    event_name: str
    required_completions: int
    current_completions: int
    progress_percentage: float
    rank: Optional[int] = None
    qualified: bool
    qualified_at: Optional[datetime] = None
    reward_tier: Optional[int] = None
    reward_name: Optional[str] = None
    rewarded_at: Optional[datetime] = None
    is_finalized: bool
    can_still_qualify: bool


class UserRewardSummary(BaseModel):
    """Summary of user's rewards"""
    total_leaderboards: int
    completed_leaderboards: int
    rewards_received: int
    pending_leaderboards: int
    leaderboards: List[UserLeaderboardStatus]


# ========== User Event Status Tracking ==========

class UserEventStatusDetail(BaseModel):
    """Detailed status of a user in an event"""
    user_id: int
    user_full_name: str
    user_email: str
    event_id: int
    event_name: str

    # Participation stats
    total_participations: int = 0
    completed_participations: int = 0
    checked_in_count: int = 0
    proof_submitted_count: int = 0
    rejected_count: int = 0
    cancelled_count: int = 0

    # Progress tracking
    total_distance_km: Optional[float] = None
    first_participation_at: Optional[datetime] = None
    last_participation_at: Optional[datetime] = None

    # Leaderboard status (if applicable)
    leaderboard_config_id: Optional[int] = None
    leaderboard_rank: Optional[int] = None
    leaderboard_qualified: bool = False
    leaderboard_reward_name: Optional[str] = None

    # Tier progress (for multi-tier events)
    tier_progress: Optional[List[Dict[str, Any]]] = None


class UserEventStatusList(BaseModel):
    """List of user event statuses"""
    total_users: int
    event_id: int
    event_name: str
    users: List[UserEventStatusDetail]


class EventUsersSummary(BaseModel):
    """Summary of all users in an event"""
    event_id: int
    event_name: str
    total_participants: int
    by_status: Dict[str, int]
    by_tier: Optional[Dict[str, int]] = None
    completion_rate: float


# ========== Organizer View ==========

class LeaderboardSummary(BaseModel):
    """Summary statistics for organizers"""
    config_id: int
    event_id: int
    event_name: str
    total_participants: int
    qualified_participants: int
    rewarded_participants: int
    remaining_slots: int
    is_finalized: bool
    finalized_at: Optional[datetime] = None


class LeaderboardFullView(LeaderboardConfigRead):
    """Full leaderboard view with entries"""
    entries: List[LeaderboardEntryRead] = []
    summary: Optional[Dict[str, Any]] = None


# ========== Actions ==========

class FinalizeLeaderboardRequest(BaseModel):
    """Request to finalize leaderboard"""
    config_id: int
    confirm: bool = Field(..., description="Must be true to confirm")


class RecalculateRanksRequest(BaseModel):
    """Request to recalculate ranks"""
    config_id: int
    force: bool = Field(False, description="Force recalculation even if finalized")


class ExportLeaderboardRequest(BaseModel):
    """Request to export leaderboard"""
    config_id: int
    format: str = Field("csv", pattern="^(csv|excel|json)$")
    include_details: bool = Field(True, description="Include participation details")