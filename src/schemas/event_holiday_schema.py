# src/schemas/event_holiday_schema.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import date, datetime


class HolidayBase(BaseModel):
    """Base schema สำหรับวันหยุด"""
    holiday_date: date = Field(..., description="วันที่หยุด (YYYY-MM-DD)")
    holiday_name: Optional[str] = Field(None, max_length=255, description="ชื่อวันหยุด")
    description: Optional[str] = Field(None, description="คำอธิบายเพิ่มเติม")


class HolidayCreate(HolidayBase):
    """Schema สำหรับสร้างวันหยุด"""
    pass


class HolidayUpdate(BaseModel):
    """Schema สำหรับอัพเดทวันหยุด (ไม่รวมวันที่)"""
    holiday_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None


class HolidayResponse(HolidayBase):
    """Schema สำหรับ response วันหยุด"""
    id: int
    event_id: int
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    is_past: bool = Field(default=False, description="วันหยุดนี้ผ่านไปแล้วหรือไม่")
    
    class Config:
        from_attributes = True


class HolidayListResponse(BaseModel):
    """Schema สำหรับรายการวันหยุด"""
    total: int
    holidays: List[HolidayResponse]


class BulkHolidayCreate(BaseModel):
    """Schema สำหรับเพิ่มวันหยุดหลายวันพร้อมกัน"""
    holidays: List[HolidayCreate] = Field(..., min_length=1, description="รายการวันหยุด")
    
    @field_validator('holidays')
    def validate_unique_dates(cls, v):
        """ตรวจสอบว่าไม่มีวันที่ซ้ำกัน"""
        dates = [h.holiday_date for h in v]
        if len(dates) != len(set(dates)):
            raise ValueError("มีวันที่ซ้ำกันในรายการวันหยุด")
        return v


class BulkHolidayResponse(BaseModel):
    """Schema สำหรับ response หลังเพิ่มวันหยุดหลายวัน"""
    success: bool
    created_count: int
    skipped_count: int = Field(default=0, description="จำนวนวันที่มีอยู่แล้ว")
    holidays: List[HolidayResponse]
    message: str


class HolidayDeleteResponse(BaseModel):
    """Schema สำหรับ response หลังลบวันหยุด"""
    success: bool
    message: str
    deleted_id: Optional[int] = None


class QuickHolidayCreate(BaseModel):
    """Schema สำหรับเพิ่มวันหยุดแบบง่าย (เฉพาะวันที่)"""
    holiday_dates: List[date] = Field(..., min_length=1, description="รายการวันที่หยุด")
    holiday_names: Optional[List[str]] = Field(None, description="ชื่อวันหยุด (ถ้ามี)")
    
    @field_validator('holiday_dates')
    def validate_unique_dates(cls, v):
        """ตรวจสอบว่าไม่มีวันที่ซ้ำกัน"""
        if len(v) != len(set(v)):
            raise ValueError("มีวันที่ซ้ำกันในรายการ")
        return v
    
    @field_validator('holiday_names')
    def validate_names_length(cls, v, info):
        """ตรวจสอบว่าจำนวนชื่อตรงกับจำนวนวันที่"""
        if v is not None:
            dates = info.data.get('holiday_dates', [])
            if len(v) != len(dates):
                raise ValueError("จำนวนชื่อวันหยุดต้องตรงกับจำนวนวันที่")
        return v
