from pydantic import BaseModel, EmailStr, field_validator, computed_field
from datetime import datetime
from typing import Optional, Union
from src.models.user import UserRole

try:
    from pydantic import ConfigDict
except ImportError:
    ConfigDict = None


# Base schemas
class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    title: Optional[str] = None


# ========== Student Schemas ==========
class StudentCreate(UserBase):
    password: str
    nisit_id: str  # Required for students
    major: str  # Required for students
    faculty: str  # Required for students


class StudentRead(UserBase):
    id: int
    role: UserRole
    nisit_id: str
    major: str
    faculty: str
    is_verified: bool
    is_locked: bool
    failed_login_attempts: int
    locked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    if ConfigDict:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True


class StudentUpdate(BaseModel):
    title: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    major: Optional[str] = None
    faculty: Optional[str] = None


# ========== Officer Schemas ==========
class OfficerCreate(UserBase):
    password: str
    department: str  # Required for officers


class OfficerRead(UserBase):
    id: int
    role: UserRole
    department: str
    is_verified: bool
    is_locked: bool
    failed_login_attempts: int
    locked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    if ConfigDict:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True


class OfficerUpdate(BaseModel):
    title: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    department: Optional[str] = None


# ========== Staff Schemas ==========
class StaffCreate(UserBase):
    password: str
    department: str  # Required for staff


class StaffRead(UserBase):
    id: int
    role: UserRole
    department: str
    is_verified: bool
    is_locked: bool
    failed_login_attempts: int
    locked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    if ConfigDict:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True


class StaffUpdate(BaseModel):
    title: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    department: Optional[str] = None


# ========== Organizer Schemas ==========
class OrganizerCreate(UserBase):
    password: str
    # Organizer ไม่มี fields เพิ่มเติม - เก็บแค่ข้อมูลพื้นฐาน


class OrganizerRead(UserBase):
    id: int
    role: UserRole
    is_verified: bool
    is_locked: bool
    failed_login_attempts: int
    locked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    if ConfigDict:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True


class OrganizerUpdate(BaseModel):
    title: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


# ========== Legacy/Generic Schemas (for backward compatibility) ==========

class UserCreate(UserBase):
    """Legacy schema - ใช้สำหรับ backward compatibility"""
    password: str
    role: UserRole
    # Student-specific fields
    nisit_id: Optional[str] = None
    major: Optional[str] = None
    faculty: Optional[str] = None
    # Officer-specific fields
    department: Optional[str] = None

    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_names(cls, v):
        if v:
            v = v.strip()
            if not v:
                raise ValueError('Name cannot be empty or whitespace')
        return v


class UserUpdate(BaseModel):
    title: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    major: Optional[str] = None
    faculty: Optional[str] = None
    department: Optional[str] = None


class UserRead(BaseModel):
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    title: Optional[str] = None
    role: UserRole
    nisit_id: Optional[str] = None
    major: Optional[str] = None
    faculty: Optional[str] = None
    department: Optional[str] = None
    is_verified: bool
    is_locked: bool
    failed_login_attempts: int
    locked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    @property
    def full_name(self) -> str:
        """Get full name from first and last name"""
        parts = []
        if self.title:
            parts.append(self.title)
        parts.append(self.first_name)
        parts.append(self.last_name)
        return " ".join(parts)

    if ConfigDict:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class PasswordReset(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str