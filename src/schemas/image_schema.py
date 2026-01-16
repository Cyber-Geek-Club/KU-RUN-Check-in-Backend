# src/schemas/image_schema.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ImageBase(BaseModel):
    """Base schema สำหรับรูปภาพ"""
    filename: str
    original_filename: Optional[str] = None
    file_path: str
    category: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    image_hash: Optional[str] = None


class ImageCreate(ImageBase):
    """Schema สำหรับสร้างรูปภาพ"""
    uploaded_by: Optional[int] = None


class ImageResponse(ImageBase):
    """Schema สำหรับ response รูปภาพ"""
    id: int
    uploaded_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ImageUploadResponse(BaseModel):
    """Schema สำหรับ response หลังอัพโหลด"""
    success: bool
    url: Optional[str] = None
    image_hash: Optional[str] = None
    image_id: Optional[int] = None
    message: Optional[str] = None
    error: Optional[str] = None


class ImageListResponse(BaseModel):
    """Schema สำหรับ response รายการรูปภาพ"""
    total: int
    images: list[ImageResponse]


class UploaderInfo(BaseModel):
    """Schema สำหรับข้อมูลผู้อัพโหลด"""
    id: int
    email: str
    first_name: str
    last_name: str
    
    class Config:
        from_attributes = True


class ImageDetailResponse(ImageResponse):
    """Schema สำหรับ response รายละเอียดรูปภาพพร้อมข้อมูลผู้อัพโหลด"""
    uploader: Optional[UploaderInfo] = None
