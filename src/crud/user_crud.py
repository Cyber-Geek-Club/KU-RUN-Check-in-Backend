from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.user import User
from src.schemas.user_schema import UserCreate, UserUpdate
from typing import Optional
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
    result = await db.execute(select(User).where(User.id == user_id))
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
    result = await db.execute(select(User).offset(skip).limit(limit))
    return result.scalars().all()


async def create_user(db: AsyncSession, user: UserCreate) -> User:
    hashed_password = hash_password(user.password)
    verification_token = generate_verification_token()

    db_user = User(
        email=user.email,
        password_hash=hashed_password,
        name=user.name,
        role=user.role,
        nisit_id=user.nisit_id,
        major=user.major,
        faculty=user.faculty,
        department=user.department,
        is_verified=False,  # Email verification required
        verification_token=verification_token,
        verification_token_expires=datetime.now(timezone.utc) + timedelta(hours=24)
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


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
    await db.refresh(user)
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
    await db.refresh(user)
    return user


async def update_user(db: AsyncSession, user_id: int, user_data: UserUpdate) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return None

    for key, value in user_data.dict(exclude_unset=True).items():
        setattr(user, key, value)

    await db.commit()
    await db.refresh(user)
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
    await db.refresh(user)
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
    await db.refresh(user)
    return user