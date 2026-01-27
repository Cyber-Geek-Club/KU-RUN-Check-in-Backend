import asyncio
import sys
import os
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crud import event_participation_crud
from src.models.event_participation import ParticipationStatus

# Mock classes
class MockEvent:
    def __init__(self, id, event_date, event_end_date, max_checkins_per_user=None):
        self.id = id
        self.event_date = event_date
        self.event_end_date = event_end_date
        self.max_checkins_per_user = max_checkins_per_user

class MockParticipation:
    def __init__(self, id, status, checkin_date):
        self.id = id
        self.status = status
        self.checkin_date = checkin_date

async def test_check_daily_registration_limit_mocked():
    print("\n" + "="*60)
    print("Testing check_daily_registration_limit logic with MOCKS")
    print("="*60)

    # Setup Mocks
    mock_db = AsyncMock()
    
    # Mock Helper for db.execute
    # We need to handle 3 calls:
    # 1. Get Event
    # 2. Check Today Registration (The one that causes error)
    # 3. Check Total Checkins (Optional)
    
    user_id = 999
    event_id = 888
    
    # Prepare Mock Data
    now = datetime.now()
    mock_event = MockEvent(event_id, now, now, max_checkins_per_user=10)
    
    # 1. Mock Event Query Result
    mock_event_result = MagicMock()
    mock_event_result.scalar_one_or_none.return_value = mock_event
    
    # 2. Mock Today Registration Result (Simulating DUPLICATES)
    # Create two existing participations for today
    p1 = MockParticipation(101, ParticipationStatus.JOINED, now.date())
    p2 = MockParticipation(102, ParticipationStatus.JOINED, now.date())
    
    # The CRUD calls: existing_today = today_registration_result.scalars().first()
    # We want to ensure it doesn't crash even if we provide a list that has multiple items
    # Note: verify that using scalars().first() is actually what happens.
    
    mock_today_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.first.side_effect = lambda: p1 # first() returns the first item
    
    mock_today_result.scalars.return_value = mock_scalars
    
    # 3. Mock Total Checkins Result
    mock_total_result = MagicMock()
    mock_total_result.scalar.return_value = 0
    
    # Configure db.execute side_effect
    # The order of execution:
    # 1. select(Event)
    # 2. select(EventParticipation) ... (today check)
    # 3. select(func.count) ... (total limit)
    
    mock_db.execute.side_effect = [
        mock_event_result,
        mock_today_result,
        mock_total_result
    ]
    
    # Execution
    print("Calling check_daily_registration_limit...")
    try:
        result = await event_participation_crud.check_daily_registration_limit(
            mock_db, user_id, event_id
        )
    # print(f"Result: {result}") # Commented out to avoid UnicodeEncodeError on Windows
        
        # Assertions
        # Since we mocked finding a record (p1), it should return can_register=False
        assert result['can_register'] is False
        assert result['today_registration'] == p1
        assert "คุณได้ลงทะเบียนวันนี้แล้ว" in result['reason']
        
        print("SUCCESS: Logic handled existing record correctly.")
        
    except Exception as e:
        print(f"FAILED with error: {e}")
        import traceback
        traceback.print_exc()
        raise e

if __name__ == "__main__":
    asyncio.run(test_check_daily_registration_limit_mocked())
