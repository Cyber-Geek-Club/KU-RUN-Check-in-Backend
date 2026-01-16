from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from src.models.base import Base


class UserRole(str, enum.Enum):
    STUDENT = "student"
    OFFICER = "officer"
    STAFF = "staff"
    ORGANIZER = "organizer"


class User(Base):
    """Base User table - ตาราง User หลักที่เก็บข้อมูลพื้นฐาน"""
    __tablename__ = "users"
    __mapper_args__ = {
        "polymorphic_identity": "user",
        "polymorphic_on": "role"
    }

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False)

    # Name fields - Split into first and last name
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
    verification_token_expires = Column(DateTime(timezone=True), nullable=True)

    # Password reset
    reset_token = Column(String(255), nullable=True)
    reset_token_expires = Column(DateTime(timezone=True), nullable=True)

    # Account locking
    failed_login_attempts = Column(Integer, default=0)
    is_locked = Column(Boolean, default=False)
    locked_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    participations = relationship(
        "EventParticipation",
        back_populates="user",
        foreign_keys="EventParticipation.user_id"
    )
    user_rewards = relationship("UserReward", back_populates="user")
    password_reset_logs = relationship("PasswordResetLog", back_populates="user")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


class Student(User):
    """Student table - ตารางเฉพาะนักศึกษา"""
    __tablename__ = "students"
    __mapper_args__ = {
        "polymorphic_identity": UserRole.STUDENT
    }

    id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    nisit_id = Column(String(20), unique=True, nullable=False, index=True)
    major = Column(String(255), nullable=False)
    faculty = Column(String(255), nullable=False)


class Officer(User):
    """Officer table - ตารางเฉพาะเจ้าหน้าที่"""
    __tablename__ = "officers"
    __mapper_args__ = {
        "polymorphic_identity": UserRole.OFFICER
    }

    id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    department = Column(String(255), nullable=False)


class Staff(User):
    """Staff table - ตารางเฉพาะพนักงาน"""
    __tablename__ = "staffs"
    __mapper_args__ = {
        "polymorphic_identity": UserRole.STAFF
    }

    id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    department = Column(String(255), nullable=False)


class Organizer(User):
    """Organizer table - ตารางเฉพาะผู้จัดงาน (ไม่มีข้อมูลเพิ่มเติม)"""
    __tablename__ = "organizers"
    __mapper_args__ = {
        "polymorphic_identity": UserRole.ORGANIZER
    }

    id = Column(Integer, ForeignKey("users.id"), primary_key=True)

    @property
    def name(self):
        """Get full name"""
        parts = []
        if self.title:
            parts.append(self.title)
        parts.append(self.first_name)
        parts.append(self.last_name)
        return " ".join(parts)