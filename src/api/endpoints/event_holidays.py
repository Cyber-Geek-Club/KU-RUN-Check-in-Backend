# src/api/endpoints/event_holidays.py
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import date

from src.api.dependencies.auth import get_db, get_current_user, require_staff_or_organizer
from src.models.user import User
from src.crud import event_crud, event_holiday_crud
from src.schemas.event_holiday_schema import (
    HolidayCreate,
    HolidayUpdate,
    HolidayResponse,
    HolidayListResponse,
    BulkHolidayCreate,
    BulkHolidayResponse,
    HolidayDeleteResponse,
    QuickHolidayCreate
)

router = APIRouter()


@router.post("/events/{event_id}/holidays", response_model=HolidayResponse, status_code=status.HTTP_201_CREATED)
async def create_event_holiday(
    event_id: int = Path(..., description="Event ID"),
    holiday_data: HolidayCreate = ...,
    current_user: User = Depends(require_staff_or_organizer),
    db: AsyncSession = Depends(get_db)
):
    """
    เพิ่มวันหยุดให้กับกิจกรรม
    Requires: Staff or Organizer role
    
    - **event_id**: ID ของกิจกรรม
    - **holiday_date**: วันที่หยุด
    - **holiday_name**: ชื่อวันหยุด (ถ้ามี)
    - **description**: คำอธิบายเพิ่มเติม
    """
    # ตรวจสอบว่ากิจกรรมมีอยู่จริง
    event = await event_crud.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # ตรวจสอบว่ากิจกรรมเป็นแบบหลายวันหรือไม่
    if not event.is_multi_day:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add holidays to single-day events"
        )
    
    # ตรวจสอบว่าวันหยุดอยู่ในช่วงกิจกรรมหรือไม่
    event_start = event.event_date.date()
    event_end = event.event_end_date.date() if event.event_end_date else event_start
    
    if not (event_start <= holiday_data.holiday_date <= event_end):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Holiday date must be between {event_start} and {event_end}"
        )
    
    # ตรวจสอบว่ามีวันหยุดนี้อยู่แล้วหรือไม่
    existing = await event_holiday_crud.get_holiday_by_event_and_date(
        db, event_id, holiday_data.holiday_date
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Holiday already exists for this date"
        )
    
    # สร้างวันหยุด
    holiday = await event_holiday_crud.create_holiday(
        db=db,
        event_id=event_id,
        holiday_date=holiday_data.holiday_date,
        holiday_name=holiday_data.holiday_name,
        description=holiday_data.description,
        created_by=current_user.id
    )
    
    return HolidayResponse.model_validate(holiday)


@router.post("/events/{event_id}/holidays/bulk", response_model=BulkHolidayResponse)
async def create_bulk_holidays(
    event_id: int = Path(..., description="Event ID"),
    bulk_data: BulkHolidayCreate = ...,
    current_user: User = Depends(require_staff_or_organizer),
    db: AsyncSession = Depends(get_db)
):
    """
    เพิ่มวันหยุดหลายวันพร้อมกัน
    Requires: Staff or Organizer role
    """
    # ตรวจสอบว่ากิจกรรมมีอยู่จริง
    event = await event_crud.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    if not event.is_multi_day:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add holidays to single-day events"
        )
    
    event_start = event.event_date.date()
    event_end = event.event_end_date.date() if event.event_end_date else event_start
    
    created_holidays = []
    skipped = 0
    
    for holiday_data in bulk_data.holidays:
        # ตรวจสอบวันที่
        if not (event_start <= holiday_data.holiday_date <= event_end):
            skipped += 1
            continue
        
        # ตรวจสอบว่ามีอยู่แล้วหรือไม่
        existing = await event_holiday_crud.get_holiday_by_event_and_date(
            db, event_id, holiday_data.holiday_date
        )
        if existing:
            skipped += 1
            continue
        
        # สร้างวันหยุด
        holiday = await event_holiday_crud.create_holiday(
            db=db,
            event_id=event_id,
            holiday_date=holiday_data.holiday_date,
            holiday_name=holiday_data.holiday_name,
            description=holiday_data.description,
            created_by=current_user.id
        )
        created_holidays.append(holiday)
    
    return BulkHolidayResponse(
        success=True,
        created_count=len(created_holidays),
        skipped_count=skipped,
        holidays=[HolidayResponse.model_validate(h) for h in created_holidays],
        message=f"Created {len(created_holidays)} holidays, skipped {skipped}"
    )


@router.post("/events/{event_id}/holidays/quick", response_model=BulkHolidayResponse)
async def quick_create_holidays(
        event_id: int = Path(..., description="Event ID"),
        quick_data: QuickHolidayCreate = ...,
        current_user: User = Depends(require_staff_or_organizer),
        db: AsyncSession = Depends(get_db)
):
    """
    เพิ่มวันหยุดแบบง่าย (ระบุแค่วันที่)
    Requires: Staff or Organizer role
    """
    # ตรวจสอบกิจกรรม
    event = await event_crud.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    if not event.is_multi_day:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add holidays to single-day events"
        )

    # --- เริ่มส่วนแก้ไข: เพิ่ม Validation ช่วงวันที่ ---
    event_start = event.event_date.date()
    event_end = event.event_end_date.date() if event.event_end_date else event_start

    valid_dates = []
    valid_names = []

    # เตรียม list ชื่อวันหยุด (ถ้าไม่ได้ส่งมา ให้เป็น None ทั้งหมดเพื่อให้ zip ทำงานได้)
    input_names = quick_data.holiday_names if quick_data.holiday_names else [None] * len(quick_data.holiday_dates)

    # วนลูปตรวจสอบวันที่ว่าอยู่ในช่วงหรือไม่
    for date_obj, name in zip(quick_data.holiday_dates, input_names):
        if event_start <= date_obj <= event_end:
            valid_dates.append(date_obj)
            if quick_data.holiday_names:
                valid_names.append(name)

    # เตรียมข้อมูลสำหรับส่งไป CRUD
    pass_names = valid_names if quick_data.holiday_names else None
    # --- จบส่วนแก้ไข ---

    # สร้างวันหยุด (ส่งเฉพาะวันที่ Valid ไป)
    holidays = await event_holiday_crud.bulk_create_holidays(
        db=db,
        event_id=event_id,
        holiday_dates=valid_dates,
        holiday_names=pass_names,
        created_by=current_user.id
    )

    # คำนวณจำนวนที่ถูกข้าม (รวมทั้งที่อยู่นอกช่วงวันที่ และที่มีอยู่แล้วใน DB)
    skipped = len(quick_data.holiday_dates) - len(holidays)

    return BulkHolidayResponse(
        success=True,
        created_count=len(holidays),
        skipped_count=skipped,
        holidays=[HolidayResponse.model_validate(h) for h in holidays],
        message=f"Created {len(holidays)} holidays" + (f", skipped {skipped}" if skipped > 0 else "")
    )


@router.get("/events/{event_id}/holidays", response_model=HolidayListResponse)
async def get_event_holidays(
    event_id: int = Path(..., description="Event ID"),
    include_past: bool = Query(True, description="รวมวันหยุดที่ผ่านไปแล้ว"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    ดูรายการวันหยุดของกิจกรรม
    """
    # ตรวจสอบกิจกรรม
    event = await event_crud.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    holidays = await event_holiday_crud.get_holidays_by_event(
        db, event_id, include_past=include_past
    )
    
    return HolidayListResponse(
        total=len(holidays),
        holidays=[HolidayResponse.model_validate(h) for h in holidays]
    )


@router.get("/events/{event_id}/holidays/{holiday_id}", response_model=HolidayResponse)
async def get_holiday_detail(
    event_id: int = Path(..., description="Event ID"),
    holiday_id: int = Path(..., description="Holiday ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """ดูรายละเอียดวันหยุด"""
    holiday = await event_holiday_crud.get_holiday_by_id(db, holiday_id)
    
    if not holiday or holiday.event_id != event_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Holiday not found"
        )
    
    return HolidayResponse.model_validate(holiday)


@router.get("/events/{event_id}/holidays/check/{check_date}")
async def check_is_holiday(
    event_id: int = Path(..., description="Event ID"),
    check_date: date = Path(..., description="Date to check (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    ตรวจสอบว่าวันที่กำหนดเป็นวันหยุดหรือไม่
    """
    is_holiday_date = await event_holiday_crud.is_holiday(db, event_id, check_date)
    
    response = {
        "event_id": event_id,
        "date": check_date,
        "is_holiday": is_holiday_date
    }
    
    if is_holiday_date:
        holiday = await event_holiday_crud.get_holiday_by_event_and_date(db, event_id, check_date)
        response["holiday_name"] = holiday.holiday_name
        response["description"] = holiday.description
    
    return response


@router.patch("/events/{event_id}/holidays/{holiday_id}", response_model=HolidayResponse)
async def update_holiday(
    event_id: int = Path(..., description="Event ID"),
    holiday_id: int = Path(..., description="Holiday ID"),
    update_data: HolidayUpdate = ...,
    current_user: User = Depends(require_staff_or_organizer),
    db: AsyncSession = Depends(get_db)
):
    """
    อัพเดทข้อมูลวันหยุด (ไม่รวมวันที่)
    Requires: Staff or Organizer role
    """
    holiday = await event_holiday_crud.get_holiday_by_id(db, holiday_id)
    
    if not holiday or holiday.event_id != event_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Holiday not found"
        )
    
    updated_holiday = await event_holiday_crud.update_holiday(
        db=db,
        holiday_id=holiday_id,
        holiday_name=update_data.holiday_name,
        description=update_data.description
    )
    
    return HolidayResponse.model_validate(updated_holiday)


@router.delete("/events/{event_id}/holidays/{holiday_id}", response_model=HolidayDeleteResponse)
async def delete_holiday(
    event_id: int = Path(..., description="Event ID"),
    holiday_id: int = Path(..., description="Holiday ID"),
    current_user: User = Depends(require_staff_or_organizer),
    db: AsyncSession = Depends(get_db)
):
    """
    ลบวันหยุด
    Requires: Staff or Organizer role
    """
    holiday = await event_holiday_crud.get_holiday_by_id(db, holiday_id)
    
    if not holiday or holiday.event_id != event_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Holiday not found"
        )
    
    deleted = await event_holiday_crud.delete_holiday(db, holiday_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete holiday"
        )
    
    return HolidayDeleteResponse(
        success=True,
        message="Holiday deleted successfully",
        deleted_id=holiday_id
    )


@router.delete("/events/{event_id}/holidays", response_model=HolidayDeleteResponse)
async def delete_all_holidays(
    event_id: int = Path(..., description="Event ID"),
    current_user: User = Depends(require_staff_or_organizer),
    db: AsyncSession = Depends(get_db)
):
    """
    ลบวันหยุดทั้งหมดของกิจกรรม
    Requires: Staff or Organizer role
    """
    # ตรวจสอบกิจกรรม
    event = await event_crud.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    deleted_count = await event_holiday_crud.delete_holidays_by_event(db, event_id)
    
    return HolidayDeleteResponse(
        success=True,
        message=f"Deleted {deleted_count} holidays"
    )
