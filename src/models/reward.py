from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from src.models.base import Base


class Reward(Base):
    """รางวัลหรือ Badge ที่ผู้ใช้จะได้รับ"""
    __tablename__ = "rewards"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    badge_image_url = Column(String(500), nullable=True)
    
    # Criteria for earning this reward
    required_completions = Column(Integer, default=3)  # จำนวนครั้งที่ต้องวิ่งสำเร็จ
    time_period_days = Column(Integer, default=30)  # ภายในกี่วัน (e.g., 30 = 1 เดือน)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user_rewards = relationship("UserReward", back_populates="reward")


class UserReward(Base):
    """รางวัลที่ผู้ใช้ได้รับ"""
    __tablename__ = "user_rewards"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reward_id = Column(Integer, ForeignKey("rewards.id"), nullable=False)
    
    # When the reward was earned
    earned_at = Column(DateTime, default=datetime.utcnow)
    
    # For monthly tracking
    earned_month = Column(Integer, nullable=False)  # 1-12
    earned_year = Column(Integer, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="user_rewards")
    reward = relationship("Reward", back_populates="user_rewards")
