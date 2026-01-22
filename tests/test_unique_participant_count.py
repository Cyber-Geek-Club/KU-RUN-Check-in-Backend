import asyncio
import sys
import os
import random
import string
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, delete
from src.database.db_config import SessionLocal
from src.models.event import Event, EventType
from src.models.user import User, UserRole, Student
from src.models.event_participation import EventParticipation, ParticipationStatus
from src.crud import event_crud, event_participation_crud
from src.schemas.event_participation_schema import EventParticipationCreate

# Helper to generate random string
def random_string(length=10):
    return ''.join(random.choices(string.ascii_letters, k=length))

async def create_test_user(db, role=UserRole.STUDENT):
    email = f"test_{random_string()}@example.com"
    user = Student(
        email=email,
        password_hash="hash",
        role=role,
        first_name="Test",
        last_name="User",
        nisit_id=random_string(10),
        major="CS",
        faculty="Science"
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def test_unique_counting():
    print("\n" + "="*60)
    print("Testing Unique Participant Counting Logic")
    print("="*60)

    async with SessionLocal() as db:
        creator = await create_test_user(db, UserRole.ORGANIZER)
        user1 = await create_test_user(db, UserRole.STUDENT)
        user2 = await create_test_user(db, UserRole.STUDENT)
        user3 = await create_test_user(db, UserRole.STUDENT)
        
        event = None
        try:
            print(f"Created test users: {user1.id}, {user2.id}, {user3.id}")

            # 1. Create Event with capacity 2
            print("Creating event with max_participants=2...")
            event = Event(
                title=f"Test Unique Count {random_string()}",
                event_type=EventType.SINGLE_DAY,
                event_date=datetime.now(timezone.utc) + timedelta(days=1),
                max_participants=2,
                created_by=creator.id,
                is_active=True,
                is_published=True
            )
            db.add(event)
            await db.commit()
            await db.refresh(event)
            print(f"Event created: ID {event.id}")

            # 2. User 1 Joins
            print("\nUser 1 joining...")
            p1 = await event_participation_crud.create_participation(
                db, 
                EventParticipationCreate(event_id=event.id), 
                user1.id
            )
            
            # Refresh event to check property
            await db.refresh(event)
            print(f"   Count: {event.participant_count} (Expected: 1)")
            assert event.participant_count == 1, "Count should be 1"

            # 3. User 1 Joins AGAIN (Simulate duplicate record)
            print("\nUser 1 joining AGAIN (Duplicate)...")
            # We force insert another participation directly to bypass endpoint checks if any
            p1_duplicate = EventParticipation(
                user_id=user1.id,
                event_id=event.id,
                status=ParticipationStatus.JOINED,
                join_code=f"DUP-{random_string()}"
            )
            db.add(p1_duplicate)
            await db.commit()

            # Refresh event
            await db.refresh(event, attribute_names=['participations']) # Force reload relationship
            print(f"   Count: {event.participant_count} (Expected: 1 - Unique User)")
            assert event.participant_count == 1, f"Count failed! Got {event.participant_count}, Expected 1"

            # 4. Check Stats
            print("\nChecking Stats...")
            stats = await event_crud.get_event_participant_stats(db, event.id)
            print(f"   Stats Total: {stats.total} (Expected: 1)")
            assert stats.total == 1, "Stats total should be 1"

            # 5. User 2 Joins
            print("\nUser 2 joining...")
            p2 = await event_participation_crud.create_participation(
                db, 
                EventParticipationCreate(event_id=event.id), 
                user2.id
            )
            await db.refresh(event, attribute_names=['participations'])
            print(f"   Count: {event.participant_count} (Expected: 2)")
            assert event.participant_count == 2, "Count should be 2"
            
            print(f"   Is Full: {event.is_full} (Expected: True)")
            assert event.is_full == True, "Event should be full"

            # 6. Check Capacity Endpoint Logic
            print("\nChecking Capacity Logic...")
            cap = await event_crud.check_event_capacity(db, event.id)
            print(f"   Remaining Slots: {cap['remaining_slots']} (Expected: 0)")
            assert cap['remaining_slots'] == 0, "Remaining slots should be 0"

            # 7. User 3 Tries to Join (Should check capacity)
            print("\nUser 3 joins... (Simulating capacity check)")
            cap_check = await event_crud.check_event_capacity(db, event.id)
            if not cap_check['can_join']:
                print("User 3 cannot join (Correctly blocked)")
            else:
                print("User 3 CAN join (Incorrect)")
                raise AssertionError("User 3 should not be able to join")

            print("\nALL TESTS PASSED")

        except Exception as e:
            print(f"\nTEST FAILED: {e}")
            import traceback
            traceback.print_exc()
        finally:
            print("\nCleaning up...")
            if event:
                await db.delete(event)
            # Delete users
            await db.execute(delete(User).where(User.id.in_([creator.id, user1.id, user2.id, user3.id])))
            await db.commit()
            print("Cleanup done.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_unique_counting())
