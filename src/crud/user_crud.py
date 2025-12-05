from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.user import User
from src.schemas.user_schema import UserCreate, UserUpdate
from passlib.context import CryptContext
from typing import Optional

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(User).offset(skip).limit(limit))
    return result.scalars().all()


async def create_user(db: AsyncSession, user: UserCreate) -> User:
    hashed_password = hash_password(user.password)
    db_user = User(
        email=user.email,
        password_hash=hashed_password,
        name=user.name,
        role=user.role,
        nisit_id=user.nisit_id,
        major=user.major,
        faculty=user.faculty,
        department=user.department
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


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