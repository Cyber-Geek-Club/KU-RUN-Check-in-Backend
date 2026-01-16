# src/crud/image_crud.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import datetime, timezone

from src.models.uploaded_image import UploadedImage


async def create_image(
    db: AsyncSession,
    filename: str,
    original_filename: str,
    file_path: str,
    category: str,
    uploaded_by: Optional[int] = None,
    file_size: Optional[int] = None,
    mime_type: Optional[str] = None,
    image_hash: Optional[str] = None
) -> UploadedImage:
    """สร้างข้อมูลรูปภาพในฐานข้อมูล"""
    image = UploadedImage(
        filename=filename,
        original_filename=original_filename,
        file_path=file_path,
        category=category,
        uploaded_by=uploaded_by,
        file_size=file_size,
        mime_type=mime_type,
        image_hash=image_hash
    )
    db.add(image)
    await db.commit()
    await db.refresh(image)
    return image


async def get_image_by_id(db: AsyncSession, image_id: int) -> Optional[UploadedImage]:
    """ดึงข้อมูลรูปภาพตาม ID"""
    result = await db.execute(
        select(UploadedImage)
        .options(selectinload(UploadedImage.uploader))
        .where(UploadedImage.id == image_id)
    )
    return result.scalar_one_or_none()


async def get_image_by_path(db: AsyncSession, file_path: str) -> Optional[UploadedImage]:
    """ดึงข้อมูลรูปภาพตาม file path"""
    result = await db.execute(
        select(UploadedImage)
        .where(UploadedImage.file_path == file_path)
    )
    return result.scalar_one_or_none()


async def get_image_by_hash(db: AsyncSession, image_hash: str) -> Optional[UploadedImage]:
    """ดึงข้อมูลรูปภาพตาม hash (สำหรับเช็ค duplicate)"""
    result = await db.execute(
        select(UploadedImage)
        .where(UploadedImage.image_hash == image_hash)
    )
    return result.scalar_one_or_none()


async def get_images_by_category(
    db: AsyncSession, 
    category: str,
    skip: int = 0,
    limit: int = 100
) -> List[UploadedImage]:
    """ดึงรูปภาพทั้งหมดตาม category"""
    result = await db.execute(
        select(UploadedImage)
        .where(UploadedImage.category == category)
        .order_by(UploadedImage.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def get_images_by_uploader(
    db: AsyncSession, 
    user_id: int,
    skip: int = 0,
    limit: int = 100
) -> List[UploadedImage]:
    """ดึงรูปภาพทั้งหมดที่ผู้ใช้อัพโหลด"""
    result = await db.execute(
        select(UploadedImage)
        .where(UploadedImage.uploaded_by == user_id)
        .order_by(UploadedImage.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def get_all_images(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100
) -> List[UploadedImage]:
    """ดึงรูปภาพทั้งหมด"""
    result = await db.execute(
        select(UploadedImage)
        .options(selectinload(UploadedImage.uploader))
        .order_by(UploadedImage.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def count_images(db: AsyncSession, category: Optional[str] = None) -> int:
    """นับจำนวนรูปภาพทั้งหมด"""
    from sqlalchemy import func
    query = select(func.count(UploadedImage.id))
    if category:
        query = query.where(UploadedImage.category == category)
    result = await db.execute(query)
    return result.scalar() or 0


async def delete_image(db: AsyncSession, image_id: int) -> bool:
    """ลบข้อมูลรูปภาพตาม ID"""
    result = await db.execute(
        delete(UploadedImage).where(UploadedImage.id == image_id)
    )
    await db.commit()
    return result.rowcount > 0


async def delete_image_by_path(db: AsyncSession, file_path: str) -> bool:
    """ลบข้อมูลรูปภาพตาม file path"""
    result = await db.execute(
        delete(UploadedImage).where(UploadedImage.file_path == file_path)
    )
    await db.commit()
    return result.rowcount > 0


async def find_duplicate_images(
    db: AsyncSession, 
    image_hash: str,
    exclude_id: Optional[int] = None
) -> List[UploadedImage]:
    """หารูปที่มี hash ซ้ำกัน"""
    query = select(UploadedImage).where(UploadedImage.image_hash == image_hash)
    if exclude_id:
        query = query.where(UploadedImage.id != exclude_id)
    result = await db.execute(query)
    return result.scalars().all()
