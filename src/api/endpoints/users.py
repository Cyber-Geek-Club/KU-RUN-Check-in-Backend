from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.database.db_config import SessionLocal
from src.crud import user_crud
from src.schemas.user_schema import UserCreate, UserUpdate, UserRead, UserLogin
from src.models.user import User
from typing import List

router = APIRouter()


async def get_db():
    async with SessionLocal() as session:
        yield session


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Register a new user

    สมัครสมาชิกใหม่ (นิสิต, เจ้าหน้าที่, Staff, Organizer)
    """
    # Check if email already exists
    existing_user = await user_crud.get_user_by_email(db, user.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check if nisit_id already exists (for students)
    if user.nisit_id:
        result = await db.execute(
            select(User).where(User.nisit_id == user.nisit_id)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nisit ID already registered"
            )

    return await user_crud.create_user(db, user)


@router.post("/login")
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Login user

    เข้าสู่ระบบ
    """
    user = await user_crud.get_user_by_email(db, credentials.email)
    if not user or not user_crud.verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified"
        )

    # TODO: Generate JWT token
    return {
        "message": "Login successful",
        "user_id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role
    }


@router.get("/", response_model=List[UserRead])
async def get_users(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """
    Get all users (admin only)

    ดึงข้อมูลผู้ใช้ทั้งหมด
    """
    return await user_crud.get_users(db, skip, limit)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get user by ID

    ดึงข้อมูลผู้ใช้ตาม ID
    """
    user = await user_crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.put("/{user_id}", response_model=UserRead)
async def update_user(user_id: int, user_data: UserUpdate, db: AsyncSession = Depends(get_db)):
    """
    Update user information

    แก้ไขข้อมูลผู้ใช้
    """
    user = await user_crud.update_user(db, user_id, user_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """
    Delete user

    ลบผู้ใช้
    """
    deleted = await user_crud.delete_user(db, user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return None