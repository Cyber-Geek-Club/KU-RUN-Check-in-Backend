from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.database.db_config import SessionLocal
from src.crud import user_crud
from src.schemas.user_schema import (
    UserCreate, UserUpdate, UserRead, UserLogin,
    PasswordReset, PasswordResetConfirm
)
from src.models.user import User
from src.services.email_service import send_verification_email, send_password_reset_email
from typing import List

router = APIRouter()


async def get_db():
    async with SessionLocal() as session:
        yield session


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Register a new user and send verification email

    สมัครสมาชิกใหม่และส่งอีเมลยืนยัน
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

    # Create user
    new_user = await user_crud.create_user(db, user)

    # Send verification email
    email_sent = send_verification_email(
        new_user.email,
        new_user.verification_token,
        new_user.name
    )

    if not email_sent:
        print(f"Warning: Failed to send verification email to {new_user.email}")

    return new_user


@router.get("/verify-email")
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    """
    Verify user's email using token from email

    ยืนยันอีเมลด้วย token ที่ได้รับทางอีเมล
    """
    user = await user_crud.verify_user_email(db, token)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )

    return {
        "message": "Email verified successfully",
        "user_id": user.id,
        "email": user.email
    }


@router.post("/resend-verification")
async def resend_verification(email: str, db: AsyncSession = Depends(get_db)):
    """
    Resend verification email

    ส่งอีเมลยืนยันใหม่อีกครั้ง
    """
    user = await user_crud.resend_verification_email(db, email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found or already verified"
        )

    # Send new verification email
    email_sent = send_verification_email(
        user.email,
        user.verification_token,
        user.name
    )

    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email"
        )

    return {"message": "Verification email sent"}


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
            detail="Email not verified. Please check your email for verification link."
        )

    # TODO: Generate JWT token
    return {
        "message": "Login successful",
        "user_id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role
    }


@router.post("/forgot-password")
async def forgot_password(request: PasswordReset, db: AsyncSession = Depends(get_db)):
    """
    Request password reset

    ขอรีเซ็ตรหัสผ่าน
    """
    user = await user_crud.request_password_reset(db, request.email)

    # Always return success to prevent email enumeration
    if user:
        email_sent = send_password_reset_email(
            user.email,
            user.reset_token,
            user.name
        )
        if not email_sent:
            print(f"Warning: Failed to send password reset email to {user.email}")

    return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/reset-password")
async def reset_password(request: PasswordResetConfirm, db: AsyncSession = Depends(get_db)):
    """
    Reset password using token

    รีเซ็ตรหัสผ่านด้วย token
    """
    user = await user_crud.reset_password(db, request.token, request.new_password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    return {"message": "Password reset successfully"}


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