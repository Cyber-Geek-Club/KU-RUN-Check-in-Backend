from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import Optional
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
    role: UserRole


class UserCreate(UserBase):
    password: str
    nisit_id: Optional[str] = None
    major: Optional[str] = None
    faculty: Optional[str] = None
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
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    title: Optional[str] = None
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
    created_at: datetime
    updated_at: datetime
    # Add computed full name field
    name: str

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