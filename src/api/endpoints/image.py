from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.dependencies import get_db, get_current_user, require_organizer
from src.models.user import User
from src.utils.image_upload import save_upload_file, delete_upload_file
from typing import List

router = APIRouter()


@router.post("/upload/event-banner")
async def upload_event_banner(
        file: UploadFile = File(...),
        current_user: User = Depends(require_organizer)
):
    """
    Upload event banner image
    Requires: Organizer role

    Returns URL path to be stored in database
    """
    try:
        file_path = await save_upload_file(file, subfolder="events")
        return {
            "message": "Image uploaded successfully",
            "file_path": file_path,
            "filename": file.filename
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


@router.post("/upload/proof")
async def upload_proof_image(
        file: UploadFile = File(...),
        current_user: User = Depends(get_current_user)
):
    """
    Upload proof of completion image
    Requires: Any authenticated user

    Returns URL path to be stored in database
    """
    try:
        file_path = await save_upload_file(file, subfolder="proofs")
        return {
            "message": "Proof image uploaded successfully",
            "file_path": file_path,
            "filename": file.filename
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


@router.post("/upload/reward-badge")
async def upload_reward_badge(
        file: UploadFile = File(...),
        current_user: User = Depends(require_organizer)
):
    """
    Upload reward badge image
    Requires: Organizer role

    Returns URL path to be stored in database
    """
    try:
        file_path = await save_upload_file(file, subfolder="rewards")
        return {
            "message": "Reward badge uploaded successfully",
            "file_path": file_path,
            "filename": file.filename
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


@router.delete("/delete-image")
async def delete_image(
        file_path: str,
        current_user: User = Depends(require_organizer)
):
    """
    Delete uploaded image
    Requires: Organizer role

    Use this when deleting events or updating images
    """
    deleted = await delete_upload_file(file_path)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    return {"message": "Image deleted successfully"}