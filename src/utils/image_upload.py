import os
import uuid
from pathlib import Path
from typing import Optional
from fastapi import UploadFile, HTTPException, status
import aiofiles

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

        # Ensure the resolved path is within uploads directory
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

    Args:
        file: The uploaded file
        subfolder: Subfolder within uploads directory (events, proofs, rewards)

    Returns:
        Relative path to the saved file
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
    """
    Delete uploaded file from disk

    Args:
        file_path: Relative path to the file (e.g., /uploads/events/abc123.jpg)

    Returns:
        True if deleted, False if file not found
    """
    if not file_path:
        return False

    try:
        # Validate path to prevent directory traversal
        full_path = validate_file_path(file_path)

        if full_path.exists():
            full_path.unlink()
            return True
        return False
    except HTTPException:
        # Re-raise validation errors
        raise
    except Exception as e:
        print(f"Error deleting file {file_path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not delete file: {str(e)}"
        )