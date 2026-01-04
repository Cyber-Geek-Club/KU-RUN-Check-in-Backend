"""
Database Migration: Add Daily Check-in Support
Save as: src/migrate_daily_checkin.py
Run: python src/migrate_daily_checkin.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from src.database.db_config import engine


async def migrate_daily_checkin():
    print("🔄 Adding Daily Check-in Support...")
    print()

    async with engine.begin() as conn:
        try:
            # ===== 1. Add columns to events table =====
            print("📝 Step 1: Adding columns to events table...")

            # Add event_type enum
            await conn.execute(text("""
                DO $$ BEGIN
                    CREATE TYPE eventtype AS ENUM ('single_day', 'multi_day');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """))
            print("   ✅ EventType enum created")

            # Add event_type column
            await conn.execute(text("""
                ALTER TABLE events 
                ADD COLUMN IF NOT EXISTS event_type VARCHAR(20) DEFAULT 'single_day';
            """))
            print("   ✅ event_type column added")

            # Add allow_daily_checkin column
            await conn.execute(text("""
                ALTER TABLE events 
                ADD COLUMN IF NOT EXISTS allow_daily_checkin BOOLEAN DEFAULT FALSE;
            """))
            print("   ✅ allow_daily_checkin column added")

            # Add max_checkins_per_user column
            await conn.execute(text("""
                ALTER TABLE events 
                ADD COLUMN IF NOT EXISTS max_checkins_per_user INTEGER;
            """))
            print("   ✅ max_checkins_per_user column added")
            print()

            # ===== 2. Add columns to event_participations table =====
            print("📝 Step 2: Adding columns to event_participations table...")

            # Add checkin_date column
            await conn.execute(text("""
                ALTER TABLE event_participations 
                ADD COLUMN IF NOT EXISTS checkin_date DATE;
            """))
            print("   ✅ checkin_date column added")

            # Add code_used column
            await conn.execute(text("""
                ALTER TABLE event_participations 
                ADD COLUMN IF NOT EXISTS code_used BOOLEAN DEFAULT FALSE;
            """))
            print("   ✅ code_used column added")

            # Add code_expires_at column
            await conn.execute(text("""
                ALTER TABLE event_participations 
                ADD COLUMN IF NOT EXISTS code_expires_at TIMESTAMP WITH TIME ZONE;
            """))
            print("   ✅ code_expires_at column added")
            print()

            # ===== 3. Add new status to enum =====
            print("📝 Step 3: Adding 'expired' status...")
            await conn.execute(text("""
                DO $$ BEGIN
                    ALTER TYPE participationstatus ADD VALUE IF NOT EXISTS 'expired';
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """))
            print("   ✅ 'expired' status added")
            print()

            # ===== 4. Create indexes =====
            print("📝 Step 4: Creating indexes...")
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_participations_checkin_date 
                ON event_participations(checkin_date);
            """))
            print("   ✅ Index on checkin_date created")

            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_participations_user_event_date 
                ON event_participations(user_id, event_id, checkin_date);
            """))
            print("   ✅ Composite index created")
            print()

            # ===== 5. Migrate existing data =====
            print("📝 Step 5: Migrating existing data...")
            await conn.execute(text("""
                UPDATE event_participations 
                SET checkin_date = DATE(joined_at)
                WHERE checkin_date IS NULL AND joined_at IS NOT NULL;
            """))
            print("   ✅ Existing participations migrated")
            print()

            print("🎉 Migration completed successfully!")
            return True

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            return False


async def verify_migration():
    print()
    print("🔍 Verifying migration...")
    print()

    async with engine.begin() as conn:
        try:
            # Check events table
            result = await conn.execute(text("""
                SELECT column_name, data_type
                FROM information_schema.columns 
                WHERE table_name = 'events' 
                AND column_name IN ('event_type', 'allow_daily_checkin', 'max_checkins_per_user')
                ORDER BY column_name;
            """))
            events_cols = result.fetchall()

            print("📊 Events Table:")
            for col in events_cols:
                print(f"   - {col[0]}: {col[1]}")
            print()

            # Check participations table
            result = await conn.execute(text("""
                SELECT column_name, data_type
                FROM information_schema.columns 
                WHERE table_name = 'event_participations' 
                AND column_name IN ('checkin_date', 'code_used', 'code_expires_at')
                ORDER BY column_name;
            """))
            part_cols = result.fetchall()

            print("📊 Event Participations Table:")
            for col in part_cols:
                print(f"   - {col[0]}: {col[1]}")
            print()

            print("✅ Migration verified!")
            return True

        except Exception as e:
            print(f"❌ Verification failed: {e}")
            return False


async def show_summary():
    print("=" * 70)
    print(" KU RUN - Daily Check-in Migration")
    print("=" * 70)
    print()
    print("📋 This migration adds support for:")
    print()
    print("   🎯 Multi-day events (กิจกรรมหลายวัน)")
    print("   📅 Daily registration (ลงทะเบียนได้ทุกวัน)")
    print("   🔐 One-time use codes (รหัสใช้ครั้งเดียว)")
    print("   ⏰ Code expiration (รหัสหมดอายุ)")
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
    if not await show_summary():
        return

    print("=" * 70)
    print()

    try:
        success = await migrate_daily_checkin()

        if success:
            await verify_migration()

        print()
        print("=" * 70)
        if success:
            print("✨ Migration completed successfully!")
        else:
            print("⚠️  Migration completed with warnings")
        print("=" * 70)
        print()
        print("💡 Next steps:")
        print("   1. Update your models (Event, EventParticipation)")
        print("   2. Update schemas")
        print("   3. Update CRUD functions")
        print("   4. Add new API endpoints")
        print("   5. Restart FastAPI server")
        print("   6. Test the daily check-in flow")
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