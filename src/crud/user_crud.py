from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.user import User, Student, Officer, Staff, Organizer, UserRole
from src.schemas.user_schema import (
    UserCreate, UserUpdate,
    StudentCreate, OfficerCreate, StaffCreate, OrganizerCreate
)
from typing import Optional, Union
from datetime import datetime, timedelta, timezone
import bcrypt
import secrets


def hash_password(password: str) -> str:
    """Hash password using bcrypt directly."""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against bcrypt hash."""
    try:
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False


def generate_verification_token() -> str:
    """Generate a secure random token for email verification"""
    return secrets.token_urlsafe(32)


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """
    Get user by ID with all subclass columns eagerly loaded.
    Uses with_polymorphic with eager='joined' to ensure all joined-inheritance
    columns are loaded in the same query, preventing MissingGreenlet errors.
    """
    from sqlalchemy.orm import with_polymorphic
    # Use '*' to load all subclasses and set flat=True for proper joined loading
    UserPoly = with_polymorphic(User, '*', flat=True)
    result = await db.execute(
        select(UserPoly).where(UserPoly.id == user_id)
    )
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_verification_token(db: AsyncSession, token: str) -> Optional[User]:
    result = await db.execute(
        select(User).where(User.verification_token == token)
    )
    return result.scalar_one_or_none()


async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100):
    """
    Get all users with pagination and all subclass columns eagerly loaded.
    """
    from sqlalchemy.orm import with_polymorphic
    UserPoly = with_polymorphic(User, '*', flat=True)
    result = await db.execute(
        select(UserPoly).offset(skip).limit(limit)
    )
    return result.scalars().all()


async def create_user(db: AsyncSession, user: UserCreate) -> User:
    """Legacy create_user - for backward compatibility"""
    hashed_password = hash_password(user.password)
    verification_token = generate_verification_token()

    db_user = User(
        email=user.email,
        password_hash=hashed_password,
        title=user.title,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        is_verified=False,
        verification_token=verification_token,
        verification_token_expires=datetime.now(timezone.utc) + timedelta(hours=24)
    )

    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def create_student(db: AsyncSession, student: StudentCreate) -> Student:
    """สร้างนักศึกษาใหม่"""
    hashed_password = hash_password(student.password)
    verification_token = generate_verification_token()

    db_student = Student(
        email=student.email,
        password_hash=hashed_password,
        title=student.title,
        first_name=student.first_name,
        last_name=student.last_name,
        role=UserRole.STUDENT,
        nisit_id=student.nisit_id,
        major=student.major,
        faculty=student.faculty,
        is_verified=False,
        verification_token=verification_token,
        verification_token_expires=datetime.now(timezone.utc) + timedelta(hours=24)
    )

    db.add(db_student)
    await db.commit()
    await db.refresh(db_student)
    return db_student


async def create_officer(db: AsyncSession, officer: OfficerCreate) -> Officer:
    """สร้างเจ้าหน้าที่ใหม่"""
    hashed_password = hash_password(officer.password)
    verification_token = generate_verification_token()

    db_officer = Officer(
        email=officer.email,
        password_hash=hashed_password,
        title=officer.title,
        first_name=officer.first_name,
        last_name=officer.last_name,
        role=UserRole.OFFICER,
        department=officer.department,
        is_verified=False,
        verification_token=verification_token,
        verification_token_expires=datetime.now(timezone.utc) + timedelta(hours=24)
    )

    db.add(db_officer)
    await db.commit()
    await db.refresh(db_officer)
    return db_officer


async def create_staff(db: AsyncSession, staff: StaffCreate) -> Staff:
    """สร้างพนักงานใหม่"""
    hashed_password = hash_password(staff.password)
    verification_token = generate_verification_token()

    db_staff = Staff(
        email=staff.email,
        password_hash=hashed_password,
        title=staff.title,
        first_name=staff.first_name,
        last_name=staff.last_name,
        role=UserRole.STAFF,
        department=staff.department,
        is_verified=False,
        verification_token=verification_token,
        verification_token_expires=datetime.now(timezone.utc) + timedelta(hours=24)
    )

    db.add(db_staff)
    await db.commit()
    await db.refresh(db_staff)
    return db_staff


async def create_organizer(db: AsyncSession, organizer: OrganizerCreate) -> Organizer:
    """สร้างผู้จัดงานใหม่ (ไม่มีข้อมูลเพิ่มเติม)"""
    hashed_password = hash_password(organizer.password)
    verification_token = generate_verification_token()

    db_organizer = Organizer(
        email=organizer.email,
        password_hash=hashed_password,
        title=organizer.title,
        first_name=organizer.first_name,
        last_name=organizer.last_name,
        role=UserRole.ORGANIZER,
        is_verified=False,
        verification_token=verification_token,
        verification_token_expires=datetime.now(timezone.utc) + timedelta(hours=24)
    )

    db.add(db_organizer)
    await db.commit()
    await db.refresh(db_organizer)
    return db_organizer


async def get_student_by_nisit_id(db: AsyncSession, nisit_id: str) -> Optional[Student]:
    """ค้นหานักศึกษาจาก nisit_id"""
    result = await db.execute(select(Student).where(Student.nisit_id == nisit_id))
    return result.scalar_one_or_none()


async def verify_user_email(db: AsyncSession, token: str) -> Optional[User]:
    """Verify user's email using verification token"""
    user = await get_user_by_verification_token(db, token)

    if not user:
        return None

    # Check if token has expired
    if user.verification_token_expires < datetime.now(timezone.utc):
        return None

    # Verify the user
    user.is_verified = True
    user.verification_token = None
    user.verification_token_expires = None

    await db.commit()
    return user


async def resend_verification_email(db: AsyncSession, email: str) -> Optional[User]:
    """Generate new verification token for user"""
    user = await get_user_by_email(db, email)

    if not user or user.is_verified:
        return None

    # Generate new token
    user.verification_token = generate_verification_token()
    user.verification_token_expires = datetime.now(timezone.utc) + timedelta(hours=24)

    await db.commit()
    return user


async def update_user(db: AsyncSession, user_id: int, user_data: UserUpdate) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return None

    for key, value in user_data.model_dump(exclude_unset=True).items():
        setattr(user, key, value)

    await db.commit()
    return user


async def delete_user(db: AsyncSession, user_id: int) -> bool:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return False

    await db.delete(user)
    await db.commit()
    return True


async def request_password_reset(db: AsyncSession, email: str) -> Optional[User]:
    """Generate password reset token"""
    user = await get_user_by_email(db, email)
    if not user:
        return None

    user.reset_token = generate_verification_token()
    user.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)

    await db.commit()
    return user


async def reset_password(db: AsyncSession, token: str, new_password: str) -> Optional[User]:
    """Reset password using reset token"""
    result = await db.execute(
        select(User).where(User.reset_token == token)
    )
    user = result.scalar_one_or_none()

    if not user or user.reset_token_expires < datetime.now(timezone.utc):
        return None

    user.password_hash = hash_password(new_password)
    user.reset_token = None
    user.reset_token_expires = None

    await db.commit()
    return user


async def increment_failed_login(db: AsyncSession, user: User) -> User:
    """Increment failed login attempts and lock account if threshold reached"""
    user.failed_login_attempts += 1

    # Lock account if failed attempts reach 10
    if user.failed_login_attempts >= 10:
        user.is_locked = True
        user.locked_at = datetime.now(timezone.utc)

    await db.commit()
    return user


async def reset_failed_login(db: AsyncSession, user: User) -> User:
    """Reset failed login attempts on successful login"""
    user.failed_login_attempts = 0
    await db.commit()
    return user


async def unlock_account(db: AsyncSession, user_id: int) -> Optional[User]:
    """Unlock a locked user account (for organizers)"""
    user = await get_user_by_id(db, user_id)
    if not user:
        return None

    user.is_locked = False
    user.failed_login_attempts = 0
    user.locked_at = None

    await db.commit()
    return user