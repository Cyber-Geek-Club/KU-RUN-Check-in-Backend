import os
import uuid
from pathlib import Path
from typing import Optional
from fastapi import UploadFile, HTTPException, status, APIRouter, Form, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import aiofiles

from src.api.dependencies.auth import get_db, get_current_user, require_staff_or_organizer
from src.models.user import User

# สร้าง Router instance เพื่อให้ main.py เรียกใช้ได้
router = APIRouter()

# Configuration
UPLOAD_DIR = Path("uploads")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# Create upload directories
(UPLOAD_DIR / "events").mkdir(parents=True, exist_ok=True)
(UPLOAD_DIR / "proofs").mkdir(parents=True, exist_ok=True)
(UPLOAD_DIR / "rewards").mkdir(parents=True, exist_ok=True)


def validate_image_file(file: UploadFile) -> None:
    """Validate uploaded image file"""
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided"
        )

    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )


def generate_unique_filename(original_filename: str) -> str:
    """Generate unique filename to prevent collisions"""
    file_ext = Path(original_filename).suffix.lower()
    unique_id = uuid.uuid4().hex
    return f"{unique_id}{file_ext}"


def validate_subfolder(subfolder: str) -> None:
    """Validate subfolder to prevent directory traversal attacks"""
    allowed_subfolders = ["events", "proofs", "rewards"]
    if subfolder not in allowed_subfolders:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid subfolder. Allowed: {', '.join(allowed_subfolders)}"
        )


def validate_file_path(file_path: str) -> Path:
    """Validate and sanitize file path to prevent directory traversal"""
    if not file_path or not file_path.startswith("/uploads/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path"
        )

    # Remove leading slash and validate
    relative_path = file_path.lstrip("/")
    full_path = Path(relative_path)

    # Check if path is within uploads directory
    try:
        resolved_path = full_path.resolve()
        uploads_path = UPLOAD_DIR.resolve()

        if not str(resolved_path).startswith(str(uploads_path)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file path - directory traversal detected"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path"
        )

    return full_path


async def save_upload_file(
        file: UploadFile,
        subfolder: str = "events"
) -> str:
    """
    Save uploaded file to disk
    """
    validate_image_file(file)
    validate_subfolder(subfolder)

    # Generate unique filename
    filename = generate_unique_filename(file.filename)

    # Ensure directory exists (Safety check)
    save_path = UPLOAD_DIR / subfolder
    save_path.mkdir(parents=True, exist_ok=True)

    file_path = save_path / filename

    # Check file size while reading
    total_size = 0

    try:
        # Save file asynchronously
        async with aiofiles.open(file_path, 'wb') as f:
            while chunk := await file.read(8192):  # Read in 8KB chunks
                total_size += len(chunk)
                if total_size > MAX_FILE_SIZE:
                    # Delete partial file
                    await f.close()
                    file_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"File too large. Maximum size: {MAX_FILE_SIZE / (1024 * 1024)}MB"
                    )
                await f.write(chunk)
    except Exception as e:
        # Clean up on error
        file_path.unlink(missing_ok=True)
        # Re-raise HTTP exceptions
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save file: {str(e)}"
        )

    # Return relative path for database storage
    return f"/uploads/{subfolder}/{filename}"


async def delete_upload_file(file_path: str) -> bool:
    """Delete uploaded file from disk"""
    if not file_path:
        return False

    try:
        full_path = validate_file_path(file_path)

        if full_path.exists():
            full_path.unlink()
            return True
        return False
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting file {file_path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not delete file: {str(e)}"
        )


# --- API Endpoints ---

@router.post("/upload")
async def upload_image(
        file: UploadFile,
        subfolder: str = Form("events"),
        current_user: User = Depends(get_current_user)
):
    """
    Upload an image file
    Requires: Authenticated user

    - **file**: Image file to upload (jpg, jpeg, png, gif, webp)
    - **subfolder**: Destination folder (events, proofs, rewards)
    - **Returns**: URL path to the uploaded image
    """
    # Additional validation based on user role and subfolder
    if subfolder == "events" and current_user.role.value not in ['organizer', 'staff']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organizers and staff can upload event images"
        )

    if subfolder == "rewards" and current_user.role.value != 'organizer':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organizers can upload reward images"
        )

    # Proofs can be uploaded by any authenticated user (students uploading their completion proof)

    file_url = await save_upload_file(file, subfolder)
    return {
        "success": True,
        "url": file_url,
        "message": "Image uploaded successfully"
    }


@router.delete("/delete")
async def delete_image(
        file_path: str,
        current_user: User = Depends(require_staff_or_organizer)
):
    """
    Delete an uploaded image
    Requires: Staff or Organizer role

    - **file_path**: Path to the file to delete (e.g., /uploads/events/abc123.jpg)
    - **Returns**: Success status
    """
    deleted = await delete_upload_file(file_path)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    return {
        "success": True,
        "message": "Image deleted successfully",
        "deleted_path": file_path
    }


@router.get("/info")
async def get_upload_info(
        current_user: User = Depends(get_current_user)
):
    """
    Get upload configuration information
    Requires: Authenticated user
    """
    return {
        "max_file_size_mb": MAX_FILE_SIZE / (1024 * 1024),
        "allowed_extensions": list(ALLOWED_EXTENSIONS),
        "allowed_subfolders": ["events", "proofs", "rewards"],
        "upload_permissions": {
            "events": ["organizer", "staff"],
            "proofs": ["student", "officer", "staff", "organizer"],
            "rewards": ["organizer"]
        }
    }