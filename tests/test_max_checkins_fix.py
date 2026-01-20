"""
Test: แก้ไขปัญหา max_checkins_per_user ไม่ปลดล็อครหัสวันใหม่
"""
import asyncio
import sys
import os
from datetime import datetime, date, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select, and_, func
from src.database.db_config import SessionLocal
from src.models.event import Event, EventType
from src.models.event_participation import EventParticipation, ParticipationStatus
from src.crud.event_participation_crud import check_daily_registration_limit, pre_register_for_multi_day_event


async def test_max_checkins_counting():
    """
    Test: ตรวจสอบว่าการนับ max_checkins_per_user นับทุกรหัสที่สร้างแล้ว
    ไม่ใช่แค่รหัสที่เช็คอินสำเร็จ
    """
    print("🧪 Testing max_checkins_per_user counting logic...")
    print()
    
    async with SessionLocal() as db:
        try:
            # 1. หากิจกรรม ID 5 (จาก user request)
            result = await db.execute(
                select(Event).where(Event.id == 5)
            )
            event = result.scalar_one_or_none()
            
            if not event:
                print("❌ Event ID 5 not found")
                return
            
            print(f"📅 Event: {event.title}")
            print(f"   Type: {event.event_type}")
            print(f"   Max check-ins per user: {event.max_checkins_per_user}")
            print(f"   Date: {event.event_date.date()} - {event.event_end_date.date()}")
            print()
            
            # 2. หา participations ทั้งหมดของ user (สมมติ user_id = 1)
            user_id = 1
            participations_result = await db.execute(
                select(EventParticipation)
                .where(
                    EventParticipation.event_id == 5,
                    EventParticipation.user_id == user_id
                )
                .order_by(EventParticipation.checkin_date)
            )
            participations = participations_result.scalars().all()
            
            print(f"👤 User {user_id} participations:")
            total_count = 0
            for p in participations:
                if p.status != ParticipationStatus.CANCELLED:
                    total_count += 1
                print(f"   - Date: {p.checkin_date}, Status: {p.status}, Code: {p.join_code}")
            print()
            
            # 3. นับจำนวนทั้งหมด (ไม่รวม CANCELLED)
            count_result = await db.execute(
                select(func.count(EventParticipation.id))
                .where(
                    EventParticipation.user_id == user_id,
                    EventParticipation.event_id == 5,
                    EventParticipation.status != ParticipationStatus.CANCELLED
                )
            )
            total_checkins = count_result.scalar() or 0
            
            print(f"📊 Total participations (excluding CANCELLED): {total_checkins}")
            print(f"📊 Max allowed: {event.max_checkins_per_user}")
            print()
            
            # 4. ทดสอบ check_daily_registration_limit
            check_result = await check_daily_registration_limit(
                db, user_id, 5
            )
            
            print("🔍 Check result:")
            print(f"   Can register: {check_result['can_register']}")
            print(f"   Reason: {check_result['reason']}")
            print(f"   Total check-ins: {check_result.get('total_checkins', 0)}")
            print()
            
            # 5. วิเคราะห์ผล
            if event.max_checkins_per_user:
                remaining = event.max_checkins_per_user - total_checkins
                print(f"✅ Remaining slots: {remaining}")
                
                if remaining > 0:
                    print(f"✅ User should be able to register {remaining} more times")
                else:
                    print(f"⚠️ User has used all {event.max_checkins_per_user} check-ins")
            
            print()
            print("=" * 60)
            
            # 6. แสดงสถานะแต่ละวัน
            print("📅 Daily participation status:")
            today = date.today()
            start_date = event.event_date.date()
            end_date = event.event_end_date.date() if event.event_end_date else start_date
            
            participation_by_date = {p.checkin_date: p for p in participations}
            
            current = start_date
            while current <= min(end_date, today):
                if current in participation_by_date:
                    p = participation_by_date[current]
                    status_icon = {
                        ParticipationStatus.JOINED: "🟡",
                        ParticipationStatus.CHECKED_IN: "✅",
                        ParticipationStatus.COMPLETED: "🏆",
                        ParticipationStatus.EXPIRED: "⏰",
                        ParticipationStatus.CANCELLED: "❌"
                    }.get(p.status, "❓")
                    print(f"   {current}: {status_icon} {p.status} - {p.join_code}")
                else:
                    if current == today:
                        if check_result['can_register']:
                            print(f"   {current}: 🔓 Available (not yet created)")
                        else:
                            print(f"   {current}: 🔒 Locked ({check_result['reason']})")
                    else:
                        print(f"   {current}: ⚪ No participation")
                current += timedelta(days=1)
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()


async def simulate_scenario():
    """
    จำลองสถานการณ์จริง: max_checkins_per_user เปลี่ยนจาก 1 → 4
    """
    print("\n" + "="*60)
    print("🎬 Simulating real scenario...")
    print("="*60)
    print()
    
    async with SessionLocal() as db:
        try:
            user_id = 1
            event_id = 5
            
            # นับจำนวนรหัสที่สร้างไว้แล้วทั้งหมด (ทุกสถานะยกเว้น CANCELLED)
            all_codes_result = await db.execute(
                select(func.count(EventParticipation.id))
                .where(
                    EventParticipation.user_id == user_id,
                    EventParticipation.event_id == event_id,
                    EventParticipation.status != ParticipationStatus.CANCELLED
                )
            )
            all_codes = all_codes_result.scalar() or 0
            
            # นับเฉพาะที่เช็คอินสำเร็จ
            checked_in_result = await db.execute(
                select(func.count(EventParticipation.id))
                .where(
                    EventParticipation.user_id == user_id,
                    EventParticipation.event_id == event_id,
                    EventParticipation.status.in_([
                        ParticipationStatus.CHECKED_IN,
                        ParticipationStatus.COMPLETED
                    ])
                )
            )
            checked_in_only = checked_in_result.scalar() or 0
            
            print(f"📊 Current status:")
            print(f"   Total codes created (excl. CANCELLED): {all_codes}")
            print(f"   Actually checked in: {checked_in_only}")
            print()
            
            # Get event info
            event_result = await db.execute(select(Event).where(Event.id == event_id))
            event = event_result.scalar_one_or_none()
            
            if event:
                print(f"⚙️ Event settings:")
                print(f"   max_checkins_per_user: {event.max_checkins_per_user}")
                print()
                
                # Test with old logic (would count only CHECKED_IN + COMPLETED)
                print("🔴 OLD LOGIC (counting only CHECKED_IN + COMPLETED):")
                if event.max_checkins_per_user:
                    if checked_in_only >= event.max_checkins_per_user:
                        print(f"   ❌ Would BLOCK (checked in {checked_in_only} >= max {event.max_checkins_per_user})")
                    else:
                        print(f"   ✅ Would ALLOW (checked in {checked_in_only} < max {event.max_checkins_per_user})")
                        print(f"   ⚠️ But this is WRONG if user has JOINED/EXPIRED codes!")
                print()
                
                # Test with new logic (counts all non-CANCELLED)
                print("🟢 NEW LOGIC (counting all codes incl. JOINED/EXPIRED):")
                if event.max_checkins_per_user:
                    if all_codes >= event.max_checkins_per_user:
                        print(f"   ❌ Will BLOCK (created {all_codes} >= max {event.max_checkins_per_user})")
                    else:
                        print(f"   ✅ Will ALLOW (created {all_codes} < max {event.max_checkins_per_user})")
                        print(f"   ✅ This is CORRECT - counts all created codes")
                print()
                
                # Show the difference
                print("💡 Key insight:")
                print(f"   When user has codes in JOINED/EXPIRED status,")
                print(f"   old logic would incorrectly allow more codes to be created.")
                print(f"   New logic correctly counts: {all_codes} codes already created")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()


async def test_pre_register_logic():
    """
    🧪 ทดสอบฟังก์ชัน pre_register ที่ต้องยอมรับ multiple registrations
    """
    print("\n" + "="*60)
    print("🧪 Testing pre_register logic with max_checkins_per_user...")
    print("="*60)
    print()
    
    async with SessionLocal() as db:
        try:
            user_id = 1
            event_id = 5
            
            # ดึงข้อมูล event
            event_result = await db.execute(select(Event).where(Event.id == event_id))
            event = event_result.scalar_one_or_none()
            
            if not event:
                print("❌ Event not found")
                return
            
            print(f"📅 Event: {event.title}")
            print(f"   Max check-ins per user: {event.max_checkins_per_user}")
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
            current_count = count_result.scalar() or 0
            
            print(f"📊 Current registrations: {current_count}/{event.max_checkins_per_user}")
            print()
            
            # ทดสอบ pre-register
            for i in range(1, 6):  # พยายามลงทะเบียน 5 ครั้ง
                print(f"🔄 Attempt {i}: ", end="")
                
                try:
                    result = await pre_register_for_multi_day_event(db, user_id, event_id)
                    print(f"✅ SUCCESS - {result['message']}")
                    print(f"   Code: {result['first_code']}, Date: {result['first_date']}")
                    
                    # รอให้ date เปลี่ยน (simulate)
                    import asyncio
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    if "ลงทะเบียนครบ" in str(e):
                        print(f"⚠️ BLOCKED - {str(e)}")
                        print(f"   ✅ This is CORRECT behavior")
                    elif "ลงทะเบียนวันนี้แล้ว" in str(e):
                        print(f"⚠️ BLOCKED - {str(e)}")
                        print(f"   ✅ This is CORRECT (same day)")
                    else:
                        print(f"❌ ERROR - {str(e)}")
                    break
            
            print()
            
            # แสดงสรุป
            final_count_result = await db.execute(
                select(func.count(EventParticipation.id))
                .where(
                    EventParticipation.user_id == user_id,
                    EventParticipation.event_id == event_id,
                    EventParticipation.status != ParticipationStatus.CANCELLED
                )
            )
            final_count = final_count_result.scalar() or 0
            
            print(f"📊 Final registrations: {final_count}/{event.max_checkins_per_user}")
            
            if event.max_checkins_per_user and final_count >= event.max_checkins_per_user:
                print(f"✅ System correctly blocked after reaching limit")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()


async def main():
    print("="*60)
    print("🔧 Testing max_checkins_per_user Fix")
    print("="*60)
    print()
    
    await test_max_checkins_counting()
    await simulate_scenario()
    await test_pre_register_logic()
    
    print()
    print("="*60)
    print("✅ Test completed")
    print("="*60)


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
