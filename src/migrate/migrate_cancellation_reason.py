"""
Database Migration Script: Add cancellation_reason and cancelled_at to event_participations
Run this file: python migrate_cancellation_reason.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from src.database.db_config import engine


async def migrate_cancellation_fields():
    """Add cancellation_reason and cancelled_at columns"""
    print("🔄 Starting migration: Add cancellation fields...")
    print()

    async with engine.begin() as conn:
        try:
            # Check if columns already exist
            print("📝 Checking existing columns...")
            result = await conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'event_participations' 
                AND column_name IN ('cancellation_reason', 'cancelled_at');
            """))
            existing_columns = [row[0] for row in result.fetchall()]

            if 'cancellation_reason' in existing_columns and 'cancelled_at' in existing_columns:
                print("   ℹ️  Columns already exist. Skipping...")
                return True

            # Add cancellation_reason column
            if 'cancellation_reason' not in existing_columns:
                print("📝 Adding cancellation_reason column...")
                await conn.execute(text("""
                    ALTER TABLE event_participations 
                    ADD COLUMN cancellation_reason TEXT;
                """))
                print("   ✅ cancellation_reason column added")
            else:
                print("   ℹ️  cancellation_reason already exists")

            # Add cancelled_at column
            if 'cancelled_at' not in existing_columns:
                print("📝 Adding cancelled_at column...")
                await conn.execute(text("""
                    ALTER TABLE event_participations 
                    ADD COLUMN cancelled_at TIMESTAMP WITH TIME ZONE;
                """))
                print("   ✅ cancelled_at column added")
            else:
                print("   ℹ️  cancelled_at already exists")

            print()
            print("🎉 Migration completed successfully!")
            return True

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            return False


async def verify_columns():
    """Verify that columns were added"""
    print()
    print("🔍 Verifying columns...")
    print()

    async with engine.begin() as conn:
        try:
            result = await conn.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'event_participations' 
                AND column_name IN ('cancellation_reason', 'cancelled_at')
                ORDER BY column_name;
            """))

            columns = result.fetchall()
            if columns:
                print("📊 Column Details:")
                for col in columns:
                    print(f"   - {col[0]}: {col[1]} (nullable: {col[2]})")
                print()
                print("✅ Columns verified successfully!")
                return True
            else:
                print("❌ Columns not found")
                return False

        except Exception as e:
            print(f"❌ Verification failed: {e}")
            return False


async def show_summary():
    """Show summary of what will happen"""
    print("=" * 70)
    print(" KU RUN - Add Cancellation Reason Migration")
    print("=" * 70)
    print()
    print("📋 This script will:")
    print("   1. Add 'cancellation_reason' column (TEXT)")
    print("   2. Add 'cancelled_at' column (TIMESTAMP WITH TIME ZONE)")
    print("   3. Verify the changes")
    print()
    print("⚠️  Warning: This will modify your database structure!")
    print()

    try:
        response = input("Continue? (yes/no): ").lower().strip()
        if response not in ['yes', 'y']:
            print()
            print("❌ Migration cancelled by user")
            return False
    except KeyboardInterrupt:
        print()
        print()
        print("❌ Migration cancelled by user")
        return False

    print()
    return True


async def main():
    """Main migration function"""
    if not await show_summary():
        return

    print("=" * 70)
    print()

    try:
        success = await migrate_cancellation_fields()

        if success:
            await verify_columns()

        print()
        print("=" * 70)
        if success:
            print("✨ Migration completed successfully!")
        else:
            print("⚠️  Migration completed with warnings")
        print("=" * 70)
        print()
        print("💡 Next steps:")
        print("   1. Update event_participation schema")
        print("   2. Update participation CRUD")
        print("   3. Restart your FastAPI server")
        print()

    except KeyboardInterrupt:
        print()
        print()
        print("❌ Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print()
        print("=" * 70)
        print("❌ Migration failed!")
        print("=" * 70)
        print()
        print(f"Error: {e}")
        print()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()
        print()
        print("❌ Migration cancelled")
        sys.exit(1)