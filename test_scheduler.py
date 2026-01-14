"""
🧪 Test Script for Auto Unlock/Lock System
Run this to test the scheduler functions manually
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.scheduler_service import auto_unlock_daily_codes, auto_expire_unused_codes


async def test_auto_unlock():
    """Test auto-unlock function"""
    print("=" * 70)
    print("🔓 Testing Auto-Unlock Function")
    print("=" * 70)
    
    try:
        await auto_unlock_daily_codes()
        print("\n✅ Auto-unlock test completed successfully!")
    except Exception as e:
        print(f"\n❌ Auto-unlock test failed: {str(e)}")


async def test_auto_expire():
    """Test auto-expire function"""
    print("\n" + "=" * 70)
    print("🔒 Testing Auto-Expire Function")
    print("=" * 70)
    
    try:
        await auto_expire_unused_codes()
        print("\n✅ Auto-expire test completed successfully!")
    except Exception as e:
        print(f"\n❌ Auto-expire test failed: {str(e)}")


async def main():
    print("\n🚀 Starting Scheduler Tests...\n")
    
    # Test both functions
    await test_auto_unlock()
    await test_auto_expire()
    
    print("\n" + "=" * 70)
    print("🎉 All Tests Completed!")
    print("=" * 70)


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())
