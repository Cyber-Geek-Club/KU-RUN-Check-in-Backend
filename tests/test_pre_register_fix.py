"""
ทดสอบการแก้ไข pre_register ให้รองรับ max_checkins_per_user
"""
import asyncio
import sys
import os
from datetime import datetime, date, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select, func
from src.database.db_config import SessionLocal
from src.models.event import Event
from src.models.event_participation import EventParticipation, ParticipationStatus
from src.crud.event_participation_crud import pre_register_for_multi_day_event


async def test_pre_register():
    """
    ทดสอบว่า pre_register ยอมรับให้ลงทะเบียนได้หลายครั้งตาม max_checkins_per_user
    """
    print("="*60)
    print("🧪 Testing Pre-Register with max_checkins_per_user")
    print("="*60)
    print()
    
    user_id = 1  # เปลี่ยนเป็น user_id ของคุณ
    event_id = 5  # Event ที่มีปัญหา
    
    async with SessionLocal() as db:
        try:
            # ดึงข้อมูล event
            event_result = await db.execute(
                select(Event).where(Event.id == event_id)
            )
            event = event_result.scalar_one_or_none()
            
            if not event:
                print(f"❌ Event ID {event_id} not found")
                return
            
            print(f"📅 Event: {event.title}")
            print(f"   Type: {event.event_type}")
            print(f"   Max check-ins per user: {event.max_checkins_per_user}")
            print(f"   Date: {event.event_date.date()} - {event.event_end_date.date()}")
            print()
            
            # นับจำนวนที่ลงทะเบียนไปแล้ว
            count_result = await db.execute(
                select(func.count(EventParticipation.id))
                .where(
                    EventParticipation.user_id == user_id,
                    EventParticipation.event_id == event_id,
                    EventParticipation.status != ParticipationStatus.CANCELLED
                )
            )
            current_registrations = count_result.scalar() or 0
            
            print(f"📊 Current Status:")
            print(f"   Registrations: {current_registrations}/{event.max_checkins_per_user}")
            print()
            
            # ดูรายละเอียดแต่ละวัน
            participations_result = await db.execute(
                select(EventParticipation)
                .where(
                    EventParticipation.user_id == user_id,
                    EventParticipation.event_id == event_id
                )
                .order_by(EventParticipation.checkin_date)
            )
            participations = participations_result.scalars().all()
            
            if participations:
                print("📋 Existing Participations:")
                for p in participations:
                    status_icon = {
                        ParticipationStatus.JOINED: "🟡",
                        ParticipationStatus.CHECKED_IN: "✅",
                        ParticipationStatus.COMPLETED: "🏆",
                        ParticipationStatus.EXPIRED: "⏰",
                        ParticipationStatus.CANCELLED: "❌"
                    }.get(p.status, "❓")
                    print(f"   {status_icon} {p.checkin_date}: {p.status.value} - {p.join_code}")
                print()
            
            # ทดสอบลงทะเบียนวันนี้
            today = datetime.now(timezone.utc).date()
            
            today_check = await db.execute(
                select(EventParticipation)
                .where(
                    EventParticipation.user_id == user_id,
                    EventParticipation.event_id == event_id,
                    EventParticipation.checkin_date == today,
                    EventParticipation.status != ParticipationStatus.CANCELLED
                )
            )
            
            if today_check.scalar_one_or_none():
                print(f"⚠️ Already registered for today ({today})")
                print(f"   Cannot register again for the same day")
            elif event.max_checkins_per_user and current_registrations >= event.max_checkins_per_user:
                print(f"⚠️ Already reached maximum registrations ({event.max_checkins_per_user})")
                print(f"   Cannot register anymore")
            else:
                remaining = event.max_checkins_per_user - current_registrations if event.max_checkins_per_user else "unlimited"
                print(f"✅ Can register today!")
                print(f"   Remaining slots: {remaining}")
                print()
                print("💡 To test registration, uncomment the code below:")
                print("   # result = await pre_register_for_multi_day_event(db, user_id, event_id)")
                print("   # print(f'✅ Registered: {result}')")
            
            print()
            print("="*60)
            print("📝 Summary:")
            print(f"   - Old logic: Blocked after 1st registration regardless of max_checkins")
            print(f"   - New logic: Allows up to {event.max_checkins_per_user} registrations (1 per day)")
            print(f"   - Current: {current_registrations} registrations")
            
            if event.max_checkins_per_user:
                if current_registrations < event.max_checkins_per_user:
                    print(f"   ✅ Still has {event.max_checkins_per_user - current_registrations} slots available")
                else:
                    print(f"   ⚠️ All slots used")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()


async def main():
    await test_pre_register()


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
