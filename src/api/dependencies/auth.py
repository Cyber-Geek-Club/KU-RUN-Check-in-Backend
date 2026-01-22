from fastapi import Depends, HTTPException, status
import logging
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.db_config import SessionLocal
from src.utils.token import verify_access_token
from src.crud import user_crud
from src.models.user import User, UserRole
from typing import Optional


logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/login")


async def get_db():
    """Database dependency"""
    async with SessionLocal() as session:
        yield session


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db)
) -> User:
    """
    Verify JWT token and return current user
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Debug: Log received token
    logger.info(f"[AUTH] Received token: {token[:30] if token else 'None'}...")

    # Verify token
    payload = verify_access_token(token)
    if payload is None:
        logger.warning(f"[AUTH] Token verification FAILED. Token: {token[:30] if token else 'None'}...")
        raise credentials_exception

    user_id: str = payload.get("sub")
    if user_id is None:
        logger.warning("Auth Failed: Token missing 'sub' claim")
        raise credentials_exception

    # Get user from database
    user = await user_crud.get_user_by_id(db, int(user_id))
    if user is None:
        logger.warning(f"Auth Failed: User ID {user_id} not found in DB")
        raise credentials_exception

    # Check if user is verified
    if not user.is_verified:
        logger.warning(f"Auth Failed: User {user_id} not verified")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified"
        )

    return user


async def get_current_active_user(
        current_user: User = Depends(get_current_user)
) -> User:
    """
    Ensure user is active and verified
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


def require_role(allowed_roles: list[UserRole]):
    """
    Dependency factory to check if user has required role
    Usage: Depends(require_role([UserRole.ORGANIZER, UserRole.STAFF]))
    """

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join([r.value for r in allowed_roles])}"
            )
        return current_user

    return role_checker


# Specific role dependencies
async def require_organizer(current_user: User = Depends(get_current_user)) -> User:
    """Only organizers can access"""
    if current_user.role != UserRole.ORGANIZER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only organizers can access this endpoint."
        )
    return current_user


async def require_staff_or_organizer(current_user: User = Depends(get_current_user)) -> User:
    """Staff or organizers can access"""
    if current_user.role not in [UserRole.STAFF, UserRole.ORGANIZER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Staff or organizer role required."
        )
    return current_user


async def require_student(current_user: User = Depends(get_current_user)) -> User:
    """Only students can access"""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Student role required."
        )
    return current_user