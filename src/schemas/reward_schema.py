from pydantic import BaseModel
from datetime import datetime
from typing import Optional

try:
    from pydantic import ConfigDict
except ImportError:
    ConfigDict = None

# Reward schemas
class RewardBase(BaseModel):
    name: str
    description: Optional[str] = None
    badge_image_url: Optional[str] = None
    required_completions: int = 3
    time_period_days: int = 30

class RewardCreate(RewardBase):
    pass

class RewardUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    badge_image_url: Optional[str] = None
    required_completions: Optional[int] = None
    time_period_days: Optional[int] = None

class RewardRead(RewardBase):
    id: int
    created_at: datetime
    updated_at: datetime

    if ConfigDict:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True

# UserReward schemas
class UserRewardRead(BaseModel):
    id: int
    user_id: int
    reward_id: int
    earned_at: datetime
    earned_month: int
    earned_year: int

    if ConfigDict:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True