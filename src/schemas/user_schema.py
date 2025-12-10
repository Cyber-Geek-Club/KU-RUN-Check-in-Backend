from pydantic import BaseModel, EmailStr
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
    name: str
    role: UserRole

class UserCreate(UserBase):
    password: str
    nisit_id: Optional[str] = None
    major: Optional[str] = None
    faculty: Optional[str] = None
    department: Optional[str] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None
    major: Optional[str] = None
    faculty: Optional[str] = None
    department: Optional[str] = None

class UserRead(UserBase):
    id: int
    nisit_id: Optional[str] = None
    major: Optional[str] = None
    faculty: Optional[str] = None
    department: Optional[str] = None
    is_verified: bool
    created_at: datetime
    updated_at: datetime

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