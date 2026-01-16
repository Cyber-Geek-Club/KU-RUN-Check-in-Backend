"""
Integration Test: Reward and Leaderboard Reward System
ทดสอบระบบรางวัลและ Leaderboard แบบ Integration Test

Test Flow:
1. สร้าง Users (Students + Staff)
2. สร้าง Events
3. สร้าง Rewards
4. สร้าง Leaderboard Config
5. Users เข้าร่วมกิจกรรม (Join Events)
6. Staff Check-in Users
7. Submit Proof & Complete
8. Check Rewards & Leaderboard

Usage:
    python test_reward_integration.py
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from decimal import Decimal

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import database and models
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from sqlalchemy import text

from src.models.base import Base
from src.models.user import User, Student, Staff, UserRole
from src.models.event import Event, EventType
from src.models.event_participation import EventParticipation, ParticipationStatus
from src.models.reward import Reward, UserReward
from src.models.reward_lb import RewardLeaderboardConfig, RewardLeaderboardEntry

# Import CRUD operations
from src.crud import user_crud, event_crud, reward_crud, reward_lb_crud
from src.crud.event_participation_crud import (
    create_participation,
    check_in_participation,
    get_participation_by_id
)
from src.schemas.user_schema import StudentCreate, StaffCreate
from src.schemas.event_schema import EventCreate
from src.schemas.event_participation_schema import EventParticipationCreate
from src.schemas.reward_schema import RewardCreate
from src.schemas.reward_lb_schema import LeaderboardConfigCreate, RewardTier


# ============================================
# Test Configuration
# ============================================

# Use test database or in-memory database
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", os.getenv("DATABASE_URL"))

# Test data configuration
NUM_TEST_STUDENTS = 5
NUM_TEST_EVENTS = 3
REQUIRED_COMPLETIONS_FOR_REWARD = 3  # จำนวนครั้งที่ต้องวิ่งเพื่อได้รับรางวัล


# ============================================
# Database Setup
# ============================================

class TestDatabase:
    """Test database manager"""
    
    def __init__(self):
        self.engine = create_async_engine(TEST_DATABASE_URL, echo=False)
        self.SessionLocal = sessionmaker(
            self.engine, 
            class_=AsyncSession, 
            expire_on_commit=False
        )
    
    async def create_tables(self):
        """Create all tables"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Created database tables")
    
    async def drop_tables(self):
        """Drop all tables"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        print("✅ Dropped all database tables")
    
    async def get_session(self) -> AsyncSession:
        """Get database session"""
        return self.SessionLocal()
    
    async def close(self):
        """Close database connection"""
        await self.engine.dispose()


# ============================================
# Test Data Generators
# ============================================

async def create_test_students(db: AsyncSession, count: int) -> List[Student]:
    """สร้างนักศึกษาทดสอบ"""
    students = []
    for i in range(1, count + 1):
        student_data = StudentCreate(
            email=f"student{i}_test_{datetime.now().timestamp():.0f}@ku.th",
            password="TestPassword123!",
            title="นาย",
            first_name=f"ทดสอบ{i}",
            last_name=f"นักศึกษา{i}",
            nisit_id=f"64{i:08d}",
            major="วิทยาการคอมพิวเตอร์",
            faculty="วิศวกรรมศาสตร์"
        )
        
        try:
            student = await user_crud.create_student(db, student_data)
            # Verify user and set verified for testing
            student.is_verified = True
            await db.commit()
            await db.refresh(student)
            students.append(student)
            print(f"  ✓ Created Student: {student.first_name} {student.last_name} (ID: {student.id})")
        except Exception as e:
            print(f"  ✗ Failed to create student {i}: {e}")
    
    return students


async def create_test_staff(db: AsyncSession) -> Staff:
    """สร้าง Staff ทดสอบสำหรับ check-in และ approve"""
    staff_data = StaffCreate(
        email=f"staff_test_{datetime.now().timestamp():.0f}@ku.th",
        password="StaffPassword123!",
        title="นาย",
        first_name="เจ้าหน้าที่",
        last_name="ทดสอบ",
        department="กองกิจกรรมนักศึกษา"
    )
    
    try:
        staff = await user_crud.create_staff(db, staff_data)
        staff.is_verified = True
        await db.commit()
        await db.refresh(staff)
        print(f"  ✓ Created Staff: {staff.first_name} {staff.last_name} (ID: {staff.id})")
        return staff
    except Exception as e:
        print(f"  ✗ Failed to create staff: {e}")
        return None


async def create_test_events(db: AsyncSession, staff_id: int, count: int) -> List[Event]:
    """สร้าง Events ทดสอบ"""
    events = []
    base_date = datetime.now(timezone.utc)
    
    for i in range(1, count + 1):
        event_data = EventCreate(
            title=f"KU Run Test Event #{i}",
            description=f"กิจกรรมวิ่งทดสอบครั้งที่ {i}",
            event_type=EventType.SINGLE_DAY,
            event_date=base_date + timedelta(days=i),
            location="สนามกีฬา มหาวิทยาลัยเกษตรศาสตร์",
            distance_km=5,
            max_participants=100,
            is_active=True,
            is_published=True
        )
        
        try:
            event = await event_crud.create_event(db, event_data, staff_id)
            events.append(event)
            print(f"  ✓ Created Event: {event.title} (ID: {event.id})")
        except Exception as e:
            print(f"  ✗ Failed to create event {i}: {e}")
    
    return events


async def create_test_rewards(db: AsyncSession) -> List[Reward]:
    """สร้างรางวัลทดสอบ"""
    rewards_data = [
        RewardCreate(
            name="🥉 Bronze Runner",
            description="เหรียญทองแดงสำหรับผู้ที่วิ่งครบ 3 ครั้ง",
            badge_image_url="https://example.com/bronze.png",
            required_completions=3,
            time_period_days=30
        ),
        RewardCreate(
            name="🥈 Silver Runner",
            description="เหรียญเงินสำหรับผู้ที่วิ่งครบ 5 ครั้ง",
            badge_image_url="https://example.com/silver.png",
            required_completions=5,
            time_period_days=30
        ),
        RewardCreate(
            name="🥇 Gold Runner",
            description="เหรียญทองสำหรับผู้ที่วิ่งครบ 10 ครั้ง",
            badge_image_url="https://example.com/gold.png",
            required_completions=10,
            time_period_days=30
        ),
    ]
    
    rewards = []
    for reward_data in rewards_data:
        try:
            reward = await reward_crud.create_reward(db, reward_data)
            rewards.append(reward)
            print(f"  ✓ Created Reward: {reward.name} (ID: {reward.id})")
        except Exception as e:
            print(f"  ✗ Failed to create reward: {e}")
    
    return rewards


async def create_leaderboard_config(
    db: AsyncSession, 
    event_id: int, 
    staff_id: int,
    rewards: List[Reward]
) -> RewardLeaderboardConfig:
    """สร้าง Leaderboard Config ทดสอบ"""
    now = datetime.now(timezone.utc)
    
    # Create reward tiers
    tiers = []
    if len(rewards) >= 3:
        tiers = [
            RewardTier(
                tier=1,
                min_rank=1,
                max_rank=3,
                reward_id=rewards[2].id,  # Gold
                reward_name=rewards[2].name,
                quantity=3,
                required_completions=3
            ),
            RewardTier(
                tier=2,
                min_rank=4,
                max_rank=10,
                reward_id=rewards[1].id,  # Silver
                reward_name=rewards[1].name,
                quantity=7,
                required_completions=2
            ),
            RewardTier(
                tier=3,
                min_rank=11,
                max_rank=50,
                reward_id=rewards[0].id,  # Bronze
                reward_name=rewards[0].name,
                quantity=40,
                required_completions=1
            ),
        ]
    
    config_data = LeaderboardConfigCreate(
        event_id=event_id,
        name="KU Run 2026 Leaderboard",
        description="กระดานผู้นำสำหรับกิจกรรม KU Run 2026",
        required_completions=3,
        max_reward_recipients=50,
        reward_tiers=tiers,
        starts_at=now - timedelta(days=1),
        ends_at=now + timedelta(days=30)
    )
    
    try:
        config = await reward_lb_crud.create_leaderboard_config(
            db, config_data, staff_id
        )
        print(f"  ✓ Created Leaderboard Config: {config.name} (ID: {config.id})")
        return config
    except Exception as e:
        print(f"  ✗ Failed to create leaderboard config: {e}")
        return None


# ============================================
# Test Actions
# ============================================

async def join_event(db: AsyncSession, user_id: int, event_id: int) -> EventParticipation:
    """ให้ user เข้าร่วมกิจกรรม"""
    participation_data = EventParticipationCreate(event_id=event_id)
    
    try:
        participation = await create_participation(db, participation_data, user_id)
        print(f"    ✓ User {user_id} joined Event {event_id} (Join Code: {participation.join_code})")
        return participation
    except Exception as e:
        print(f"    ✗ User {user_id} failed to join Event {event_id}: {e}")
        return None


async def staff_checkin_user(
    db: AsyncSession, 
    join_code: str, 
    staff_id: int
) -> EventParticipation:
    """Staff check-in ผู้ใช้"""
    try:
        participation = await check_in_participation(db, join_code, staff_id)
        if participation:
            print(f"    ✓ Checked in: {join_code} -> Status: {participation.status}")
            return participation
        else:
            print(f"    ✗ Check-in failed for code: {join_code}")
            return None
    except Exception as e:
        print(f"    ✗ Check-in error: {e}")
        return None


async def complete_participation(
    db: AsyncSession,
    participation_id: int,
    staff_id: int,
    distance_km: float = 5.0
) -> EventParticipation:
    """Complete การเข้าร่วมกิจกรรม"""
    try:
        participation = await get_participation_by_id(db, participation_id)
        if not participation:
            print(f"    ✗ Participation {participation_id} not found")
            return None
        
        # Update to completed
        participation.status = ParticipationStatus.COMPLETED
        participation.completed_by = staff_id
        participation.completed_at = datetime.now(timezone.utc)
        participation.actual_distance_km = Decimal(str(distance_km))
        
        await db.commit()
        await db.refresh(participation)
        
        print(f"    ✓ Completed participation {participation_id} (Distance: {distance_km} km)")
        return participation
    except Exception as e:
        print(f"    ✗ Complete error: {e}")
        return None


async def check_user_rewards(db: AsyncSession, user_id: int) -> List[UserReward]:
    """ตรวจสอบรางวัลของผู้ใช้"""
    try:
        # Check and award rewards
        await reward_crud.check_and_award_rewards(db, user_id)
        
        # Get user rewards
        user_rewards = await reward_crud.get_user_rewards(db, user_id)
        return user_rewards
    except Exception as e:
        print(f"    ✗ Check rewards error: {e}")
        return []


async def update_leaderboard_progress(
    db: AsyncSession,
    config_id: int,
    user_id: int,
    event_id: int
) -> RewardLeaderboardEntry:
    """อัปเดต progress ใน Leaderboard"""
    try:
        entry = await reward_lb_crud.update_entry_progress(
            db, config_id, user_id, event_id
        )
        if entry:
            print(f"    ✓ Updated leaderboard entry for User {user_id}: {entry.total_completions} completions")
        return entry
    except Exception as e:
        print(f"    ✗ Update leaderboard error: {e}")
        return None


# ============================================
# Test Results Display
# ============================================

async def display_leaderboard(db: AsyncSession, config_id: int):
    """แสดง Leaderboard"""
    print("\n" + "=" * 60)
    print("📊 LEADERBOARD RESULTS")
    print("=" * 60)
    
    try:
        entries = await reward_lb_crud.get_leaderboard_entries(db, config_id)
        
        if not entries:
            print("  (No entries)")
            return
        
        print(f"{'Rank':<6}{'User ID':<10}{'Completions':<15}{'Tier':<15}{'Reward ID':<12}")
        print("-" * 60)
        
        for entry in entries:
            rank = entry.rank or "-"
            tier = entry.reward_tier or "N/A"
            reward_id = entry.reward_id or "-"
            
            print(f"{rank:<6}{entry.user_id:<10}{entry.total_completions:<15}{tier:<15}{reward_id:<12}")
    
    except Exception as e:
        print(f"Error displaying leaderboard: {e}")


async def display_user_rewards(db: AsyncSession, users: List[User]):
    """แสดงรางวัลของผู้ใช้"""
    print("\n" + "=" * 60)
    print("🏆 USER REWARDS")
    print("=" * 60)
    
    for user in users:
        rewards = await reward_crud.get_user_rewards(db, user.id)
        if rewards:
            print(f"\n  User: {user.first_name} {user.last_name} (ID: {user.id})")
            for ur in rewards:
                # Get reward details
                reward = await reward_crud.get_reward_by_id(db, ur.reward_id)
                if reward:
                    print(f"    • {reward.name} (Earned: {ur.earned_at.strftime('%Y-%m-%d')})")
        else:
            print(f"\n  User: {user.first_name} {user.last_name} (ID: {user.id}) - No rewards yet")


async def display_participation_summary(db: AsyncSession, users: List[User]):
    """แสดงสรุปการเข้าร่วมกิจกรรม"""
    print("\n" + "=" * 60)
    print("📋 PARTICIPATION SUMMARY")
    print("=" * 60)
    
    for user in users:
        result = await db.execute(
            select(EventParticipation)
            .where(EventParticipation.user_id == user.id)
        )
        participations = result.scalars().all()
        
        completed = sum(1 for p in participations if p.status == ParticipationStatus.COMPLETED)
        total = len(participations)
        
        print(f"  {user.first_name} {user.last_name}: {completed}/{total} completed")


# ============================================
# Main Test Runner
# ============================================

async def run_integration_test():
    """รัน Integration Test ทั้งหมด"""
    print("\n" + "=" * 70)
    print("🚀 REWARD & LEADERBOARD INTEGRATION TEST")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Initialize test database
    test_db = TestDatabase()
    
    try:
        # Step 1: Setup Database
        print("\n📦 STEP 1: Database Setup")
        print("-" * 40)
        await test_db.create_tables()
        
        # Get session
        db = await test_db.get_session()
        
        try:
            # Step 2: Create Test Users
            print("\n👥 STEP 2: Create Test Users")
            print("-" * 40)
            
            # Create staff first (for creating events)
            staff = await create_test_staff(db)
            if not staff:
                raise Exception("Failed to create staff")
            
            # Create students
            students = await create_test_students(db, NUM_TEST_STUDENTS)
            if not students:
                raise Exception("Failed to create students")
            
            # Step 3: Create Test Events
            print("\n📅 STEP 3: Create Test Events")
            print("-" * 40)
            events = await create_test_events(db, staff.id, NUM_TEST_EVENTS)
            if not events:
                raise Exception("Failed to create events")
            
            # Step 4: Create Rewards
            print("\n🏆 STEP 4: Create Rewards")
            print("-" * 40)
            rewards = await create_test_rewards(db)
            if not rewards:
                raise Exception("Failed to create rewards")
            
            # Step 5: Create Leaderboard Config (for first event)
            print("\n📊 STEP 5: Create Leaderboard Config")
            print("-" * 40)
            lb_config = await create_leaderboard_config(
                db, events[0].id, staff.id, rewards
            )
            
            # Step 6: Students Join Events
            print("\n🏃 STEP 6: Students Join Events")
            print("-" * 40)
            participations: Dict[int, List[EventParticipation]] = {}
            
            for student in students:
                participations[student.id] = []
                # Each student joins different number of events
                events_to_join = events[:min(len(events), students.index(student) + 1)]
                
                for event in events_to_join:
                    participation = await join_event(db, student.id, event.id)
                    if participation:
                        participations[student.id].append(participation)
            
            # Step 7: Staff Check-in Students
            print("\n✅ STEP 7: Staff Check-in Students")
            print("-" * 40)
            for student_id, student_participations in participations.items():
                for participation in student_participations:
                    await staff_checkin_user(db, participation.join_code, staff.id)
            
            # Step 8: Complete Participations
            print("\n🏁 STEP 8: Complete Participations")
            print("-" * 40)
            for student_id, student_participations in participations.items():
                for participation in student_participations:
                    await complete_participation(
                        db, 
                        participation.id, 
                        staff.id, 
                        distance_km=5.0
                    )
            
            # Step 9: Update Leaderboard Progress
            print("\n📈 STEP 9: Update Leaderboard Progress")
            print("-" * 40)
            if lb_config:
                for student in students:
                    for event in events:
                        await update_leaderboard_progress(
                            db, lb_config.id, student.id, event.id
                        )
            
            # Step 10: Calculate and Allocate Leaderboard Rewards
            print("\n🎯 STEP 10: Calculate Leaderboard Rewards")
            print("-" * 40)
            if lb_config:
                try:
                    stats = await reward_lb_crud.calculate_and_allocate_rewards(
                        db, lb_config.id
                    )
                    print(f"  ✓ Allocation Stats:")
                    print(f"    - Total Qualified: {stats['total_qualified']}")
                    print(f"    - Awarded: {stats['awarded']}")
                    print(f"    - Waitlisted: {stats['waitlisted']}")
                    print(f"    - Tier Distribution: {stats['tier_distribution']}")
                except Exception as e:
                    print(f"  ✗ Allocation error: {e}")
            
            # Step 11: Check Standard Rewards (based on completions)
            print("\n🎖️ STEP 11: Check Standard Rewards")
            print("-" * 40)
            for student in students:
                user_rewards = await check_user_rewards(db, student.id)
                if user_rewards:
                    print(f"  ✓ User {student.id} earned {len(user_rewards)} reward(s)")
                else:
                    print(f"  ○ User {student.id} has no rewards yet")
            
            # ============================================
            # Display Results
            # ============================================
            
            # Show participation summary
            await display_participation_summary(db, students)
            
            # Show user rewards
            await display_user_rewards(db, students)
            
            # Show leaderboard
            if lb_config:
                await display_leaderboard(db, lb_config.id)
            
            # ============================================
            # Test Summary
            # ============================================
            print("\n" + "=" * 70)
            print("✅ INTEGRATION TEST COMPLETED SUCCESSFULLY!")
            print("=" * 70)
            print(f"\nTest Summary:")
            print(f"  • Students Created: {len(students)}")
            print(f"  • Events Created: {len(events)}")
            print(f"  • Rewards Created: {len(rewards)}")
            print(f"  • Leaderboard Config: {'Created' if lb_config else 'Failed'}")
            print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
        finally:
            await db.close()
    
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await test_db.close()


async def run_cleanup_test():
    """ล้างข้อมูลทดสอบ (Optional)"""
    print("\n🧹 Cleaning up test data...")
    test_db = TestDatabase()
    
    try:
        await test_db.drop_tables()
        print("✅ Cleanup completed!")
    finally:
        await test_db.close()


# ============================================
# CLI Entry Point
# ============================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Reward & Leaderboard Integration Test")
    parser.add_argument(
        "--cleanup", 
        action="store_true", 
        help="Drop all tables after test (cleanup)"
    )
    parser.add_argument(
        "--cleanup-only",
        action="store_true",
        help="Only run cleanup (drop tables)"
    )
    
    args = parser.parse_args()
    
    if args.cleanup_only:
        asyncio.run(run_cleanup_test())
    else:
        asyncio.run(run_integration_test())
        
        if args.cleanup:
            asyncio.run(run_cleanup_test())
