import os
import uuid
from pathlib import Path
from typing import Optional
from fastapi import UploadFile, HTTPException, status, APIRouter, Form
import aiofiles

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


async def save_upload_file(
        file: UploadFile,
        subfolder: str = "events"
) -> str:
    """
    Save uploaded file to disk
    """
    validate_image_file(file)

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

    # Remove leading slash and construct full path
    relative_path = file_path.lstrip("/")
    full_path = Path(relative_path)

    try:
        if full_path.exists():
            full_path.unlink()
            return True
        return False
    except Exception as e:
        print(f"Error deleting file {file_path}: {e}")
        return False


# --- เพิ่ม Endpoint สำหรับ Upload ---
@router.post("/upload")
async def upload_image(
        file: UploadFile,
        subfolder: str = Form("events")  # รับค่า subfolder จาก Form data (default: events)
):
    """
    API Endpoint สำหรับอัปโหลดรูปภาพ
    """
    if subfolder not in ["events", "proofs", "rewards"]:
        raise HTTPException(status_code=400, detail="Invalid subfolder")

    file_url = await save_upload_file(file, subfolder)
    return {"url": file_url}