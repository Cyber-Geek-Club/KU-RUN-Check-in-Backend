import os
import uuid
import mimetypes
from pathlib import Path
from typing import Optional, List
from fastapi import UploadFile, HTTPException, status, APIRouter, File, Depends, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
import aiofiles

from src.api.dependencies.auth import get_db, get_current_user, require_staff_or_organizer
from src.models.user import User
from src.models.uploaded_image import UploadedImage
from src.utils.image_hash import calculate_image_hash_from_bytes
from src.crud import image_crud
from src.schemas.image_schema import (
    ImageResponse, ImageUploadResponse, ImageListResponse, 
    ImageDetailResponse, UploaderInfo
)

# สร้าง Router instance เพื่อให้ main.py เรียกใช้ได้
router = APIRouter()

# Configuration
UPLOAD_DIR = Path("uploads")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".webp"}
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
) -> tuple[str, str, int, str]:  # 🆕 Return path, hash, size, filename
    """
    Save uploaded file to disk and calculate hash

    Returns:
        tuple: (file_path, image_hash, file_size, filename)
    """
    validate_image_file(file)
    validate_subfolder(subfolder)

    filename = generate_unique_filename(file.filename)
    save_path = UPLOAD_DIR / subfolder
    save_path.mkdir(parents=True, exist_ok=True)
    file_path = save_path / filename

    total_size = 0
    file_bytes = bytearray()  # 🆕 Collect bytes for hashing

    try:
        async with aiofiles.open(file_path, 'wb') as f:
            while chunk := await file.read(8192):
                total_size += len(chunk)
                if total_size > MAX_FILE_SIZE:
                    await f.close()
                    file_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"File too large. Maximum size: {MAX_FILE_SIZE / (1024 * 1024)}MB"
                    )
                await f.write(chunk)
                file_bytes.extend(chunk)  # 🆕 Collect bytes

        # 🆕 Calculate image hash
        image_hash = calculate_image_hash_from_bytes(bytes(file_bytes))

        if not image_hash:
            # Clean up if hash calculation fails
            file_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process image"
            )

        relative_path = f"/uploads/{subfolder}/{filename}"
        return relative_path, image_hash, total_size, filename

    except Exception as e:
        file_path.unlink(missing_ok=True)
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save file: {str(e)}"
        )


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

@router.post("/upload", response_model=ImageUploadResponse)
async def upload_image(
        file: UploadFile = File(...),
        subfolder: str = Form("events"),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Upload an image file with duplicate detection and save to database

    Returns:
        - url: Path to uploaded image
        - image_hash: Perceptual hash for duplicate detection
        - image_id: ID of the image record in database
    """
    try:
        validate_subfolder(subfolder)
    except HTTPException as e:
        return ImageUploadResponse(success=False, error=e.detail)

    # Role-based validation
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

    try:
        # Get path, hash, size and filename
        file_url, image_hash, file_size, filename = await save_upload_file(file, subfolder)
        
        # Get MIME type
        mime_type = mimetypes.guess_type(file.filename)[0] or "image/jpeg"
        
        # Save to database
        db_image = await image_crud.create_image(
            db=db,
            filename=filename,
            original_filename=file.filename,
            file_path=file_url,
            category=subfolder,
            uploaded_by=current_user.id,
            file_size=file_size,
            mime_type=mime_type,
            image_hash=image_hash
        )

        return ImageUploadResponse(
            success=True,
            url=file_url,
            image_hash=image_hash,
            image_id=db_image.id,
            message="Image uploaded successfully"
        )
    except HTTPException as e:
        return ImageUploadResponse(success=False, error=e.detail)
    except Exception as e:
        return ImageUploadResponse(success=False, error=f"Upload failed: {str(e)}")


@router.delete("/delete")
async def delete_image(
        file_path: str,
        current_user: User = Depends(require_staff_or_organizer),
        db: AsyncSession = Depends(get_db)
):
    """
    Delete an uploaded image (file + database record)
    Requires: Staff or Organizer role

    - **file_path**: Path to the file to delete (e.g., /uploads/events/abc123.jpg)
    - **Returns**: Success status
    """
    # Delete file from disk
    deleted = await delete_upload_file(file_path)
    
    # Delete from database
    await image_crud.delete_image_by_path(db, file_path)

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


@router.get("/list", response_model=ImageListResponse)
async def list_images(
        category: Optional[str] = Query(None, description="Filter by category (events, proofs, rewards)"),
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=100),
        current_user: User = Depends(require_staff_or_organizer),
        db: AsyncSession = Depends(get_db)
):
    """
    List all uploaded images with pagination
    Requires: Staff or Organizer role
    
    - **category**: Filter by category (optional)
    - **skip**: Number of records to skip
    - **limit**: Maximum number of records to return
    """
    if category:
        images = await image_crud.get_images_by_category(db, category, skip, limit)
        total = await image_crud.count_images(db, category)
    else:
        images = await image_crud.get_all_images(db, skip, limit)
        total = await image_crud.count_images(db)
    
    return ImageListResponse(
        total=total,
        images=[ImageResponse.model_validate(img) for img in images]
    )


@router.get("/my-uploads", response_model=ImageListResponse)
async def list_my_uploads(
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=100),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    List images uploaded by current user
    """
    images = await image_crud.get_images_by_uploader(db, current_user.id, skip, limit)
    
    # Count user's images
    from sqlalchemy import select, func
    from src.models.uploaded_image import UploadedImage
    result = await db.execute(
        select(func.count(UploadedImage.id))
        .where(UploadedImage.uploaded_by == current_user.id)
    )
    total = result.scalar() or 0
    
    return ImageListResponse(
        total=total,
        images=[ImageResponse.model_validate(img) for img in images]
    )


@router.get("/{image_id}", response_model=ImageDetailResponse)
async def get_image_detail(
        image_id: int,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Get details of a specific image
    """
    image = await image_crud.get_image_by_id(db, image_id)
    
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    
    # Build response
    response_data = {
        "id": image.id,
        "filename": image.filename,
        "original_filename": image.original_filename,
        "file_path": image.file_path,
        "category": image.category,
        "file_size": image.file_size,
        "mime_type": image.mime_type,
        "image_hash": image.image_hash,
        "uploaded_by": image.uploaded_by,
        "created_at": image.created_at,
        "updated_at": image.updated_at,
        "uploader": None
    }
    
    if image.uploader:
        response_data["uploader"] = UploaderInfo(
            id=image.uploader.id,
            email=image.uploader.email,
            first_name=image.uploader.first_name,
            last_name=image.uploader.last_name
        )
    
    return ImageDetailResponse(**response_data)


@router.delete("/{image_id}")
async def delete_image_by_id(
        image_id: int,
        current_user: User = Depends(require_staff_or_organizer),
        db: AsyncSession = Depends(get_db)
):
    """
    Delete an image by ID (file + database record)
    Requires: Staff or Organizer role
    """
    # Get image from database
    image = await image_crud.get_image_by_id(db, image_id)
    
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    
    # Delete file from disk
    try:
        await delete_upload_file(image.file_path)
    except HTTPException:
        pass  # File might already be deleted
    
    # Delete from database
    await image_crud.delete_image(db, image_id)
    
    return {
        "success": True,
        "message": "Image deleted successfully",
        "deleted_id": image_id
    }
