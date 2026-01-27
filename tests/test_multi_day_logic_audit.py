import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date, timedelta, timezone
import pytz
import sys
import os

# Add root directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.engine.result import Result

# Mock models
class MockEvent:
    def __init__(self, id=1, event_type="multi_day", event_date=None, event_end_date=None, max_checkins_per_user=10):
        self.id = id
        self.event_type = event_type
        self.event_date = event_date
        self.event_end_date = event_end_date
        self.max_checkins_per_user = max_checkins_per_user
        self.title = "Test Event"
        self.max_participants = 100

class MockParticipation:
    def __init__(self, id=1, user_id=1, event_id=1, checkin_date=None, status="joined", code_used=False):
        self.id = id
        self.user_id = user_id
        self.event_id = event_id
        self.checkin_date = checkin_date
        self.status = status
        self.code_used = code_used
        self.join_code = "12345"
        self.code_expires_at = None
        self.joined_at = datetime.now(timezone.utc)

# Mock DB Session
@pytest.fixture
def mock_db():
    db = AsyncMock()
    # Mock execute/scalars/first/all chain
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_result
    mock_result.first.return_value = None
    mock_result.all.return_value = []
    mock_result.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_result
    db.get = AsyncMock(return_value=None)
    return db

@pytest.mark.asyncio
async def test_ensure_daily_participation_creates_new(mock_db):
    """
    Given: Multi-day event, User is pre-registered, NO record for today.
    When: ensure_daily_participation is called.
    Then: Should create a new participation record.
    """
    from src.crud.event_participation_crud import ensure_daily_participation
    from src.models.event import EventType
    
    # Setup Data
    BANGKOK_TZ = pytz.timezone('Asia/Bangkok')
    today = datetime.now(BANGKOK_TZ).date()
    
    # 1. Event exists and is active today
    event = MockEvent(
        event_type=EventType.MULTI_DAY,
        event_date=datetime.now(timezone.utc) - timedelta(days=1),
        event_end_date=datetime.now(timezone.utc) + timedelta(days=5)
    )
    mock_db.get.return_value = event
    
    # 2. Mock Queries
    # Q1: Check Pre-registration -> Returns Existing Record (User is registered)
    # Q2: Check Today's Record -> Returns None (Needs creation)
    # Q3: Check Quota -> Returns 0 (Limit 10)
    
    # We need to mock 'execute' behavior depending on call count or query structure
    # Since checking exact SQL string is hard with mocks, we'll assume sequential calls or use side_effect
    
    # Let's use side_effect for execute to return different results
    # Call 1: check_registered -> Found
    # Call 2: existing_today -> None (So we create)
    # Call 3: quota -> 0
    # Call 4: get_join_code -> None (Unique)
    
    res_found = MagicMock()
    res_found.scalar_one_or_none.return_value = MockParticipation()
    
    res_none = MagicMock()
    res_none.scalar_one_or_none.return_value = None
    
    res_quota = MagicMock()
    res_quota.scalar.return_value = 0
    
    mock_db.execute.side_effect = [
        res_found, # Check pre-registered
        res_none,  # Check today
        res_quota, # Check quota
        res_none,  # Check join code uniqueness (used by generate_join_code check)
    ]

    # Run
    with patch('src.crud.event_participation_crud.generate_join_code', return_value="99999"):
        await ensure_daily_participation(mock_db, user_id=1, event_id=1)
    
    # Verify
    assert mock_db.add.called
    # Check arguments of db.add
    args, _ = mock_db.add.call_args
    new_p = args[0]
    assert new_p.checkin_date == today
    assert new_p.join_code == "99999"
    assert new_p.status == "joined"
    print("SUCCESS: Created new daily participation")

@pytest.mark.asyncio
async def test_ensure_daily_participation_skips_existing(mock_db):
    """
    Given: Multi-day event, User ALREADY has today's record.
    When: ensure_daily_participation is called.
    Then: Should DO NOTHING.
    """
    from src.crud.event_participation_crud import ensure_daily_participation
    from src.models.event import EventType
    
    # Setup Data
    BANGKOK_TZ = pytz.timezone('Asia/Bangkok')
    today = datetime.now(BANGKOK_TZ).date()
    
    event = MockEvent(
        event_type=EventType.MULTI_DAY,
        event_date=datetime.now(timezone.utc) - timedelta(days=1),
        event_end_date=datetime.now(timezone.utc) + timedelta(days=5)
    )
    mock_db.get.return_value = event
    
    res_found = MagicMock()
    res_found.scalar_one_or_none.return_value = MockParticipation()
    
    mock_db.execute.side_effect = [
        res_found, # Check pre-registered -> Found
        res_found, # Check today -> Found! (Should stop here)
    ]
    
    await ensure_daily_participation(mock_db, user_id=1, event_id=1)
    
    assert not mock_db.add.called
    print("SUCCESS: Skipped creating duplicate")

if __name__ == "__main__":
    import asyncio
    
    # Simple manual runner for Windows environment without full pytest setup
    async def run_tests():
        db = MagicMock()
        db.get = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.rollback = AsyncMock()
        db.add = MagicMock()
        
        print("Running tests...")
        
        # Reset mocks for each test
        db.reset_mock()
        await test_ensure_daily_participation_creates_new(db)
        
        db.reset_mock()
        await test_ensure_daily_participation_skips_existing(db)
        
        print("All manual tests passed!")

    asyncio.run(run_tests())
