import sys
import os
import pytest

# Add project root to path so we can import src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database.db_config import engine

@pytest.fixture(autouse=True)
async def cleanup_database_engine():
    """
    Auto-use fixture to dispose of the global SQLAlchemy engine after each test.
    This prevents 'InterfaceError: another operation is in progress' when 
    different tests (running in different event loops) try to reuse 
    the same async connection pool.
    """
    yield
    await engine.dispose()
