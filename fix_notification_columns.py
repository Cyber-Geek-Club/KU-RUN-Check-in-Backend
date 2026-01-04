"""
Quick Fix: Change notification columns from ENUM to VARCHAR
Run: python fix_notification_columns.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from src.database.db_config import engine


async def fix_notification_columns():
    print("🔧 Fixing notification columns...")
    print()

    async with engine.begin() as conn:
        try:
            # 1. Drop and recreate 'channel' column
            print("📝 Step 1: Fixing 'channel' column...")
            await conn.execute(text("""
                ALTER TABLE notifications 
                ALTER COLUMN channel TYPE VARCHAR(20);
            """))
            print("   ✅ channel column fixed")
            print()

            # 2. Drop and recreate 'status' column
            print("📝 Step 2: Fixing 'status' column...")
            await conn.execute(text("""
                ALTER TABLE notifications 
                ALTER COLUMN status TYPE VARCHAR(20);
            """))
            print("   ✅ status column fixed")
            print()

            # 3. Drop and recreate 'type' column
            print("📝 Step 3: Fixing 'type' column...")
            await conn.execute(text("""
                ALTER TABLE notifications 
                ALTER COLUMN type TYPE VARCHAR(50);
            """))
            print("   ✅ type column fixed")
            print()

            print("🎉 All columns fixed successfully!")
            return True

        except Exception as e:
            print(f"❌ Fix failed: {e}")
            import traceback
            traceback.print_exc()
            return False


async def main():
    try:
        success = await fix_notification_columns()

        if success:
            print()
            print("=" * 70)
            print("✨ Fix completed!")
            print("=" * 70)
            print()
            print("💡 Next steps:")
            print("   1. Restart your FastAPI server")
            print("   2. Try joining an event again")
            print()

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())