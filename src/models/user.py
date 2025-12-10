from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from src.models.base import Base


class UserRole(str, enum.Enum):
    STUDENT = "student"
    OFFICER = "officer"
    STAFF = "staff"
    ORGANIZER = "organizer"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False)

    # Name fields
    title = Column(String(50), nullable=True)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    
    # Student-specific fields
    nisit_id = Column(String(20), unique=True, nullable=True)
    major = Column(String(255), nullable=True)
    faculty = Column(String(255), nullable=True)

    # Officer-specific fields
    department = Column(String(255), nullable=True)

    # Verification
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String(255), nullable=True)
    verification_token_expires = Column(DateTime, nullable=True)

    # Password reset
    reset_token = Column(String(255), nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships - specify foreign_keys to resolve ambiguity
    participations = relationship(
        "EventParticipation",
        back_populates="user",
        foreign_keys="EventParticipation.user_id"
    )
    user_rewards = relationship("UserReward", back_populates="user")
    password_reset_logs = relationship("PasswordResetLog", back_populates="user")