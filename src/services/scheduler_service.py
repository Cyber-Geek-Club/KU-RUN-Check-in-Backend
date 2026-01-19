"""
⏰ Scheduler Service - Auto unlock/lock for Multi-day Events
Handles automatic daily code generation and expiration
"""
import logging
from datetime import datetime, date, timezone, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from src.database.db_config import SessionLocal
from src.models.event import Event, EventType
from src.models.event_participation import EventParticipation, ParticipationStatus
from src.models.user import User

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def auto_unlock_daily_codes():
    """
    🔓 Auto-unlock: สร้างรหัส join_code ใหม่ให้ผู้ที่ลงทะเบียนล่วงหน้าไว้
    รันทุกวันเวลา 00:00 น.
    """
    logger.info("🔓 Starting auto-unlock for multi-day events...")
    
    async with SessionLocal() as db:
        try:
            today = date.today()
            
            # หา multi-day events ที่กำลังดำเนินการอยู่
            result = await db.execute(
                select(Event).where(
                    and_(
                        Event.event_type == EventType.MULTI_DAY,
                        Event.is_active == True,
                        Event.is_published == True,
                        Event.event_date <= datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc),
                        Event.event_end_date >= datetime.combine(today, datetime.max.time()).replace(tzinfo=timezone.utc)
                    )
                )
            )
            active_events = result.scalars().all()
            
            if not active_events:
                logger.info("   ℹ️ No active multi-day events found")
                return
            
            logger.info(f"   📅 Found {len(active_events)} active multi-day events")
            
            for event in active_events:
                # หาผู้ใช้ที่ลงทะเบียนกิจกรรมนี้แล้ว (pre-registered)
                users_result = await db.execute(
                    select(EventParticipation.user_id)
                    .where(
                        and_(
                            EventParticipation.event_id == event.id,
                            EventParticipation.status.in_([
                                ParticipationStatus.JOINED,
                                ParticipationStatus.CHECKED_IN,
                                ParticipationStatus.CHECKED_OUT,
                                ParticipationStatus.COMPLETED
                            ])
                        )
                    )
                    .distinct()
                )
                registered_user_ids = [row[0] for row in users_result.fetchall()]
                
                if not registered_user_ids:
                    logger.info(f"   ℹ️ Event '{event.title}': No registered users")
                    continue
                
                logger.info(f"   🎯 Event '{event.title}': Processing {len(registered_user_ids)} users")
                
                codes_created = 0
                
                for user_id in registered_user_ids:
                    # เช็คว่าวันนี้มีรหัสแล้วหรือยัง
                    existing_check = await db.execute(
                        select(EventParticipation).where(
                            and_(
                                EventParticipation.user_id == user_id,
                                EventParticipation.event_id == event.id,
                                EventParticipation.checkin_date == today,
                                EventParticipation.status != ParticipationStatus.CANCELLED
                            )
                        )
                    )
                    
                    if existing_check.scalar_one_or_none():
                        continue  # มีรหัสวันนี้แล้ว
                    
                    # เช็คจำนวนครั้งทั้งหมด (นับทุกรหัสที่สร้างไว้ รวมทั้ง JOINED และ EXPIRED)
                    if event.max_checkins_per_user:
                        total_checkins_result = await db.execute(
                            select(EventParticipation).where(
                                and_(
                                    EventParticipation.user_id == user_id,
                                    EventParticipation.event_id == event.id,
                                    EventParticipation.status != ParticipationStatus.CANCELLED
                                )
                            )
                        )
                        total_checkins = len(total_checkins_result.scalars().all())
                        
                        if total_checkins >= event.max_checkins_per_user:
                            continue  # สร้างรหัสครบจำนวนแล้ว
                    
                    # สร้างรหัสใหม่
                    from src.crud.event_participation_crud import generate_join_code, get_participation_by_join_code
                    
                    join_code = generate_join_code()
                    while await get_participation_by_join_code(db, join_code):
                        join_code = generate_join_code()
                    
                    # กำหนดเวลาหมดอายุ (เที่ยงคืนของวันนี้)
                    code_expires_at = datetime.combine(
                        today,
                        datetime.max.time()
                    ).replace(tzinfo=timezone.utc)
                    
                    # สร้าง participation ใหม่
                    new_participation = EventParticipation(
                        user_id=user_id,
                        event_id=event.id,
                        join_code=join_code,
                        status=ParticipationStatus.JOINED,
                        checkin_date=today,
                        code_used=False,
                        code_expires_at=code_expires_at
                    )
                    
                    db.add(new_participation)
                    codes_created += 1
                
                await db.commit()
                logger.info(f"   ✅ Event '{event.title}': Created {codes_created} new codes")
            
            logger.info("🔓 Auto-unlock completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Auto-unlock failed: {str(e)}")
            await db.rollback()


async def auto_expire_unused_codes():
    """
    🔒 Auto-lock: ทำให้รหัสที่ไม่ได้ใช้หมดอายุ
    รันทุกวันเวลา 23:59 น.
    """
    logger.info("🔒 Starting auto-expire for unused codes...")
    
    async with SessionLocal() as db:
        try:
            now = datetime.now(timezone.utc)
            
            # หารหัสที่หมดอายุแล้วแต่ยังไม่ได้เปลี่ยนสถานะ
            result = await db.execute(
                select(EventParticipation).where(
                    and_(
                        EventParticipation.status == ParticipationStatus.JOINED,
                        EventParticipation.code_used == False,
                        EventParticipation.code_expires_at <= now
                    )
                )
            )
            expired_participations = result.scalars().all()
            
            if not expired_participations:
                logger.info("   ℹ️ No codes to expire")
                return
            
            logger.info(f"   ⏰ Found {len(expired_participations)} expired codes")
            
            # เปลี่ยนสถานะเป็น EXPIRED
            for participation in expired_participations:
                participation.status = ParticipationStatus.EXPIRED
                participation.updated_at = now
            
            await db.commit()
            logger.info(f"   ✅ Expired {len(expired_participations)} unused codes")
            logger.info("🔒 Auto-expire completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Auto-expire failed: {str(e)}")
            await db.rollback()


def start_scheduler():
    """
    🚀 เริ่มต้น scheduler
    """
    try:
        # Auto-unlock: รันทุกวันเวลา 00:00 น.
        scheduler.add_job(
            auto_unlock_daily_codes,
            CronTrigger(hour=0, minute=0),
            id='auto_unlock_daily',
            name='Auto-unlock daily codes',
            replace_existing=True
        )
        
        # Auto-expire: รันทุกวันเวลา 23:59 น.
        scheduler.add_job(
            auto_expire_unused_codes,
            CronTrigger(hour=23, minute=59),
            id='auto_expire_codes',
            name='Auto-expire unused codes',
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("⏰ Scheduler started successfully")
        logger.info("   🔓 Auto-unlock: Every day at 00:00")
        logger.info("   🔒 Auto-expire: Every day at 23:59")
        
    except Exception as e:
        logger.error(f"❌ Failed to start scheduler: {str(e)}")


def shutdown_scheduler():
    """
    🛑 ปิด scheduler
    """
    try:
        if scheduler.running:
            scheduler.shutdown()
            logger.info("⏰ Scheduler shutdown successfully")
    except Exception as e:
        logger.error(f"❌ Failed to shutdown scheduler: {str(e)}")
