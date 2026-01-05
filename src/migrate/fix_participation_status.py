"""
Fix event_participations status column
Run: python fix_participation_status.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from src.database.db_config import engine


async def fix_participation_status():
    print("🔧 Fixing participation status column...")
    print()

    async with engine.begin() as conn:
        try:
            # Fix status column
            print("📝 Fixing 'status' column in event_participations...")
            await conn.execute(text("""
                ALTER TABLE event_participations 
                ALTER COLUMN status TYPE VARCHAR(20);
            """))
            print("   ✅ status column fixed")
            print()

            print("🎉 Column fixed successfully!")
            return True

        except Exception as e:
            print(f"❌ Fix failed: {e}")
            import traceback
            traceback.print_exc()
            return False


async def main():
    try:
        success = await fix_participation_status()

        if success:
            print()
            print("=" * 70)
            print("✨ Fix completed!")
            print("=" * 70)
            print()
            print("💡 Restart your server now")
            print()

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())