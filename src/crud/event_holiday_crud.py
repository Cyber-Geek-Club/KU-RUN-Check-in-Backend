# src/crud/event_holiday_crud.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from typing import Optional, List
from datetime import date, datetime

from src.models.event_holiday import EventHoliday


async def create_holiday(
    db: AsyncSession,
    event_id: int,
    holiday_date: date,
    holiday_name: Optional[str] = None,
    description: Optional[str] = None,
    created_by: Optional[int] = None
) -> EventHoliday:
    """เพิ่มวันหยุดให้กับกิจกรรม"""
    holiday = EventHoliday(
        event_id=event_id,
        holiday_date=holiday_date,
        holiday_name=holiday_name,
        description=description,
        created_by=created_by
    )
    db.add(holiday)
    await db.commit()
    await db.refresh(holiday)
    return holiday


async def get_holiday_by_id(db: AsyncSession, holiday_id: int) -> Optional[EventHoliday]:
    """ดึงข้อมูลวันหยุดตาม ID"""
    result = await db.execute(
        select(EventHoliday).where(EventHoliday.id == holiday_id)
    )
    return result.scalar_one_or_none()


async def get_holidays_by_event(
    db: AsyncSession, 
    event_id: int,
    include_past: bool = True
) -> List[EventHoliday]:
    """ดึงวันหยุดทั้งหมดของกิจกรรม"""
    query = select(EventHoliday).where(EventHoliday.event_id == event_id)
    
    if not include_past:
        query = query.where(EventHoliday.holiday_date >= date.today())
    
    query = query.order_by(EventHoliday.holiday_date)
    result = await db.execute(query)
    return result.scalars().all()


async def get_holiday_by_event_and_date(
    db: AsyncSession,
    event_id: int,
    holiday_date: date
) -> Optional[EventHoliday]:
    """ตรวจสอบว่ามีวันหยุดในวันที่กำหนดหรือไม่"""
    result = await db.execute(
        select(EventHoliday).where(
            and_(
                EventHoliday.event_id == event_id,
                EventHoliday.holiday_date == holiday_date
            )
        )
    )
    return result.scalar_one_or_none()


async def is_holiday(
    db: AsyncSession,
    event_id: int,
    check_date: date
) -> bool:
    """ตรวจสอบว่าวันที่กำหนดเป็นวันหยุดหรือไม่"""
    holiday = await get_holiday_by_event_and_date(db, event_id, check_date)
    return holiday is not None


async def update_holiday(
    db: AsyncSession,
    holiday_id: int,
    holiday_name: Optional[str] = None,
    description: Optional[str] = None
) -> Optional[EventHoliday]:
    """อัพเดทข้อมูลวันหยุด (ไม่รวมวันที่)"""
    holiday = await get_holiday_by_id(db, holiday_id)
    if not holiday:
        return None
    
    if holiday_name is not None:
        holiday.holiday_name = holiday_name
    if description is not None:
        holiday.description = description
    
    await db.commit()
    await db.refresh(holiday)
    return holiday


async def delete_holiday(db: AsyncSession, holiday_id: int) -> bool:
    """ลบวันหยุด"""
    result = await db.execute(
        delete(EventHoliday).where(EventHoliday.id == holiday_id)
    )
    await db.commit()
    return result.rowcount > 0


async def delete_holidays_by_event(db: AsyncSession, event_id: int) -> int:
    """ลบวันหยุดทั้งหมดของกิจกรรม"""
    result = await db.execute(
        delete(EventHoliday).where(EventHoliday.event_id == event_id)
    )
    await db.commit()
    return result.rowcount


async def bulk_create_holidays(
    db: AsyncSession,
    event_id: int,
    holiday_dates: List[date],
    holiday_names: Optional[List[str]] = None,
    created_by: Optional[int] = None
) -> List[EventHoliday]:
    """เพิ่มวันหยุดหลายวันพร้อมกัน"""
    holidays = []
    
    for i, holiday_date in enumerate(holiday_dates):
        # ตรวจสอบว่ามีวันนี้อยู่แล้วหรือไม่
        existing = await get_holiday_by_event_and_date(db, event_id, holiday_date)
        if existing:
            continue
        
        holiday_name = holiday_names[i] if holiday_names and i < len(holiday_names) else None
        
        holiday = EventHoliday(
            event_id=event_id,
            holiday_date=holiday_date,
            holiday_name=holiday_name,
            created_by=created_by
        )
        db.add(holiday)
        holidays.append(holiday)
    
    await db.commit()
    for holiday in holidays:
        await db.refresh(holiday)
    
    return holidays


async def get_holidays_in_range(
    db: AsyncSession,
    event_id: int,
    start_date: date,
    end_date: date
) -> List[EventHoliday]:
    """ดึงวันหยุดในช่วงวันที่กำหนด"""
    result = await db.execute(
        select(EventHoliday).where(
            and_(
                EventHoliday.event_id == event_id,
                EventHoliday.holiday_date >= start_date,
                EventHoliday.holiday_date <= end_date
            )
        ).order_by(EventHoliday.holiday_date)
    )
    return result.scalars().all()


async def count_holidays(db: AsyncSession, event_id: int) -> int:
    """นับจำนวนวันหยุดทั้งหมดของกิจกรรม"""
    from sqlalchemy import func
    result = await db.execute(
        select(func.count(EventHoliday.id))
        .where(EventHoliday.event_id == event_id)
    )
    return result.scalar() or 0
