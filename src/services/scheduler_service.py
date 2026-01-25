"""
⏰ Scheduler Service - Auto unlock/lock for Multi-day Events
Handles automatic daily code generation and expiration with strict daily reset logic.
"""
import logging
from datetime import datetime, date, timezone, timedelta
import pytz  # เพิ่มการจัดการ Timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, not_, or_
from src.database.db_config import SessionLocal
from src.models.event import Event, EventType
from src.models.event_participation import EventParticipation, ParticipationStatus
from src.models.user import User
from src.crud import reward_lb_crud


logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

# ✅ กำหนด Timezone สำหรับประเทศไทย
BANGKOK_TZ = pytz.timezone('Asia/Bangkok')


async def auto_expire_unused_codes():
    """
    🔒 Auto-expire: เปลี่ยนสถานะทุกรายการที่ยังไม่สำเร็จให้เป็น EXPIRED
    
    Time: รันทุกวันเวลา 00:05 น. (Asia/Bangkok) ของวันถัดไป
    Scope: รายการของ 'เมื่อวาน' ที่ยังไม่เสร็จสิ้น
    States to expire: JOINED, CHECKED_IN, PROOF_SUBMITTED, CHECKED_OUT
    States to keep: COMPLETED, CANCELLED, EXPIRED (already)
    """
    # 1. Get today's date in Bangkok time
    now_bkk = datetime.now(BANGKOK_TZ)
    today = now_bkk.date()
    
    logger.info(f"🔒 Starting auto-expire for dates before: {today} (Time: {now_bkk.strftime('%H:%M:%S')})")
    
    async with SessionLocal() as db:
        try:
            # 2. Query participations with status NOT IN (COMPLETED, CANCELLED, EXPIRED)
            # เราเลือกเฉพาะรายการของวันนี้ (หรือเก่ากว่าที่อาจหลุดรอด) ที่ยังค้างสถานะอยู่
            query = select(EventParticipation).where(
                and_(
                    # เช็คว่าเป็นรายการของเมื่อวาน (หรือก่อนหน้า)
                    EventParticipation.checkin_date < today,
                    # สถานะที่ต้อง Expire (ยังไม่จบและยังไม่ยกเลิก)
                    not_(EventParticipation.status.in_([
                        ParticipationStatus.COMPLETED,
                        ParticipationStatus.CANCELLED,
                        ParticipationStatus.EXPIRED,
                        ParticipationStatus.REJECTED # ขึ้นกับ Policy ว่า Rejected ถือว่าจบไหม ถ้าจบแล้วก็ไม่ต้อง Expire
                    ]))
                )
            )
            
            result = await db.execute(query)
            pending_participations = result.scalars().all()
            
            if not pending_participations:
                logger.info("   ℹ️ No pending participations to expire.")
                return
            
            logger.info(f"   📋 Found {len(pending_participations)} participations to expire.")
            
            # 3. Update status to EXPIRED
            expire_count = 0
            for p in pending_participations:
                old_status = p.status
                p.status = ParticipationStatus.EXPIRED
                # อัปเดตเวลาเพื่อให้รู้ว่าระบบจัดการเมื่อไหร่ (ใช้ UTC ใน DB)
                p.updated_at = datetime.now(timezone.utc)
                
                expire_count += 1
                logger.debug(f"      - Expiring: User {p.user_id} | Event {p.event_id} | {old_status} -> EXPIRED")
            
            await db.commit()
            logger.info(f"   ✅ Successfully expired {expire_count} participations.")
            logger.info("🔒 Auto-expire completed successfully.")
            
        except Exception as e:
            logger.error(f"❌ Auto-expire failed: {str(e)}")
            await db.rollback()


async def auto_unlock_daily_codes():
    """
    🔓 Auto-unlock: สร้างรหัสใหม่สำหรับ Multi-day Events
    
    Time: รันทุกวันเวลา 00:00 น. (Asia/Bangkok)
    Conditions:
    - User must be pre-registered (เคยเข้าร่วมกิจกรรมนี้มาก่อน)
    - User must NOT have today's participation yet.
    - User must NOT exceed max_checkins_per_user (EXCLUDING EXPIRED records).
    """
    now_bkk = datetime.now(BANGKOK_TZ)
    today = now_bkk.date()
    
    logger.info(f"🔓 Starting auto-unlock for date: {today} (Time: {now_bkk.strftime('%H:%M:%S')})")
    
    async with SessionLocal() as db:
        try:
            # หา multi-day events ที่กำลังดำเนินการอยู่
            # หมายเหตุ: เปรียบเทียบ date กับ datetime ใน DB ต้องระวัง type mismatch
            # Query นี้หา Event ที่ Active และอยู่ในช่วงเวลา
            result = await db.execute(
                select(Event).where(
                    and_(
                        Event.event_type == EventType.MULTI_DAY,
                        Event.is_active == True,
                        Event.is_published == True
                    )
                )
            )
            events = result.scalars().all()
            
            # กรอง Event ที่วันนี้อยู่ในช่วงเวลา (ทำใน Python เพื่อลดความซับซ้อนของ Timezone ใน SQL Query)
            active_events = []
            for event in events:
                start_date = event.event_date.date()
                end_date = event.event_end_date.date() if event.event_end_date else start_date
                if start_date <= today <= end_date:
                    active_events.append(event)
            
            if not active_events:
                logger.info("   ℹ️ No active multi-day events for today.")
                return
            
            logger.info(f"   📅 Found {len(active_events)} active events.")
            
            for event in active_events:
                # หาผู้ใช้ที่เคยลงทะเบียนกิจกรรมนี้ (Pre-registered)
                # ✅ แก้ไข: ดึงเฉพาะ user ที่มี participation ที่ไม่ใช่ CANCELLED
                users_result = await db.execute(
                    select(EventParticipation.user_id)
                    .where(
                        and_(
                            EventParticipation.event_id == event.id,
                            EventParticipation.status != ParticipationStatus.CANCELLED
                        )
                    )
                    .distinct()
                )
                registered_user_ids = [row[0] for row in users_result.fetchall()]
                
                logger.info(f"   🎯 Event '{event.title}': Checking {len(registered_user_ids)} candidates.")
                
                codes_created = 0
                
                for user_id in registered_user_ids:
                    # 1. Check if user already has TODAY'S participation
                    # ต้องไม่นับ EXPIRED ของเมื่อวาน แต่ถ้ารายการของ 'วันนี้' เป็น EXPIRED (ซึ่งไม่น่าเกิดตอน 00:00) ก็ถือว่ามีแล้ว
                    # เราเช็คแค่ checkin_date == today และ status != CANCELLED
                    existing_today = await db.execute(
                        select(EventParticipation).where(
                            and_(
                                EventParticipation.user_id == user_id,
                                EventParticipation.event_id == event.id,
                                EventParticipation.checkin_date == today,
                                EventParticipation.status != ParticipationStatus.CANCELLED
                            )
                        )
                    )
                    
                    if existing_today.scalar_one_or_none():
                        logger.debug(f"      - User {user_id}: ⏭️ Skip - Already has today's participation")
                        continue  # มีของวันนี้แล้ว (อาจจะสร้างเองหรือระบบสร้างให้แล้ว)
                    
                    # 2. Check Quota (Max Check-ins)
                    # ✅ แก้ไข: ไม่นับทั้ง EXPIRED และ CANCELLED
                    if event.max_checkins_per_user:
                        quota_query = select(func.count(EventParticipation.id)).where(
                            and_(
                                EventParticipation.user_id == user_id,
                                EventParticipation.event_id == event.id,
                                # ✅ นับเฉพาะที่ไม่ใช่ EXPIRED และ CANCELLED
                                not_(EventParticipation.status.in_([
                                    ParticipationStatus.EXPIRED,
                                    ParticipationStatus.CANCELLED
                                ]))
                            )
                        )
                        quota_result = await db.execute(quota_query)
                        total_usage = quota_result.scalar() or 0
                        
                        if total_usage >= event.max_checkins_per_user:
                            logger.debug(f"      - User {user_id}: ⏭️ Skip - Quota full ({total_usage}/{event.max_checkins_per_user})")
                            continue
                    
                    # 3. Create New Participation
                    from src.crud.event_participation_crud import generate_join_code, get_participation_by_join_code
                    
                    join_code = generate_join_code()
                    while await get_participation_by_join_code(db, join_code):
                        join_code = generate_join_code()
                    
                    # หมดอายุตอนสิ้นวันของ 'วันนี้' (BKK)
                    code_expires_at = BANGKOK_TZ.localize(datetime.combine(today, datetime.max.time()))
                    
                    new_participation = EventParticipation(
                        user_id=user_id,
                        event_id=event.id,
                        join_code=join_code,
                        status=ParticipationStatus.JOINED,
                        checkin_date=today,
                        code_used=False,
                        code_expires_at=code_expires_at,
                        joined_at=datetime.now(timezone.utc)
                    )
                    
                    db.add(new_participation)
                    codes_created += 1
                    logger.debug(f"      - User {user_id}: ✅ Created new participation")
                
                await db.commit()
                logger.info(f"   ✅ Event '{event.title}': Created {codes_created} new codes.")
            
            logger.info("🔓 Auto-unlock completed successfully.")
            
        except Exception as e:
            logger.error(f"❌ Auto-unlock failed: {str(e)}")
            await db.rollback()


async def auto_finalize_ended_single_day_events():
    """
    🏆 Auto-finalize: สรุปผลรางวัลสำหรับ Single-Day Events ที่จบแล้ว
    
    Time: รันทุกวันเวลา 00:30 น. (Asia/Bangkok)
    Scope: Events ที่จบเมื่อวาน (หรือก่อนหน้า) ที่ยังไม่ finalize
    """
    now_bkk = datetime.now(BANGKOK_TZ)
    logger.info(f"🏆 Starting auto-finalize for single-day events (Time: {now_bkk.strftime('%H:%M:%S')})")
    
    async with SessionLocal() as db:
        try:
            # 1. Find Single-Day Events that are ended but not finalized
            # Note: We check events ended before NOW
            now_utc = datetime.now(timezone.utc)
            
            # Subquery or Join to find events with non-finalized configs
            # Easier to fetch candidate events then check config
            
            result = await db.execute(
                select(Event, func.count(EventParticipation.id).label("p_count"))
                .outerjoin(EventParticipation, Event.id == EventParticipation.event_id)
                .where(
                    and_(
                        Event.event_type == EventType.SINGLE_DAY,
                        Event.event_end_date < now_utc
                    )
                )
                .group_by(Event.id)
            )
            
            events = result.all()
            finalized_count = 0
            
            for row in events:
                event = row[0]
                config = await reward_lb_crud.get_leaderboard_config_by_event(db, event.id)
                
                if config and not config.finalized_at:
                    logger.info(f"   🔄 Finalizing event: {event.title} (ID: {event.id})")
                    success = await reward_lb_crud.auto_finalize_single_day_rewards(db, event.id)
                    if success:
                        finalized_count += 1
            
            logger.info(f"   ✅ Auto-finalize completed. Finalized {finalized_count} events.")
            
        except Exception as e:
            logger.error(f"❌ Auto-finalize failed: {str(e)}")



def start_scheduler():
    """
    🚀 เริ่มต้น scheduler โดยใช้ Timezone Asia/Bangkok
    
    Note: In load-balanced environments, only one instance should run the scheduler.
    Set ENABLE_SCHEDULER=false on secondary instances to prevent duplicate jobs.
    """
    import os
    
    # Check if scheduler should be enabled (default: True for backward compatibility)
    enable_scheduler = os.getenv("ENABLE_SCHEDULER", "true").lower() in ("true", "1", "yes")
    instance_id = os.getenv("INSTANCE_ID", "main")
    
    if not enable_scheduler:
        logger.info(f"⏰ Scheduler disabled for instance: {instance_id}")
        return
    
    try:
        # Auto-unlock: รันทุกวันเวลา 00:00 น. (เริ่มวันใหม่)
        scheduler.add_job(
            auto_unlock_daily_codes,
            CronTrigger(hour=0, minute=0, timezone=BANGKOK_TZ),
            id='auto_unlock_daily',
            name='Auto-unlock daily codes',
            replace_existing=True
        )
        
        # Auto-expire: รันทุกวันเวลา 00:05 น. (เริ่มวันใหม่)
        scheduler.add_job(
            auto_expire_unused_codes,
            CronTrigger(hour=0, minute=5, timezone=BANGKOK_TZ),
            id='auto_expire_codes',
            name='Auto-expire unused codes',
            replace_existing=True
        )

        # Auto-finalize: รันทุกวันเวลา 00:30 น.
        scheduler.add_job(
            auto_finalize_ended_single_day_events,
            CronTrigger(hour=0, minute=30, timezone=BANGKOK_TZ),
            id='auto_finalize_rewards',
            name='Auto-finalize single-day rewards',
            replace_existing=True
        )

        
        scheduler.start()
        logger.info("⏰ Scheduler started successfully (Timezone: Asia/Bangkok)")
        logger.info("   🔓 Auto-unlock: Every day at 00:00")
        logger.info("   🔒 Auto-expire: Every day at 23:59")
        logger.info("   🏆 Auto-finalize: Every day at 00:30")
        
    except Exception as e:
        logger.error(f"❌ Failed to start scheduler: {str(e)}")

def shutdown_scheduler():
    try:
        if scheduler.running:
            scheduler.shutdown()
            logger.info("⏰ Scheduler shutdown successfully")
    except Exception as e:
        logger.error(f"❌ Failed to shutdown scheduler: {str(e)}")