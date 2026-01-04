"""
Database Migration: Add Daily Check-in Support (Fixed)
Save as: src/migrate_daily_checkin.py
Run: python -m src.migrate_daily_checkin
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

    # Use connect() instead of begin() to manually control the transaction
    # This ensures we don't accidentally commit partial errors
    async with engine.connect() as conn:
        trans = await conn.begin()
        try:
            # ===== 1. Add columns to events table =====
            print("📝 Step 1: Adding columns to events table...")

            # Create Enum Type (Safe to re-run)
            await conn.execute(text("""
                DO $$ BEGIN
                    CREATE TYPE eventtype AS ENUM ('single_day', 'multi_day');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """))
            print("   ✅ EventType enum handled")

            # Add columns (Safe to re-run due to IF NOT EXISTS)
            await conn.execute(text("ALTER TABLE events ADD COLUMN IF NOT EXISTS event_type VARCHAR(20) DEFAULT 'single_day'"))
            await conn.execute(text("ALTER TABLE events ADD COLUMN IF NOT EXISTS allow_daily_checkin BOOLEAN DEFAULT FALSE"))
            await conn.execute(text("ALTER TABLE events ADD COLUMN IF NOT EXISTS max_checkins_per_user INTEGER"))
            print("   ✅ Events table columns handled")

            # ===== 2. Add columns to event_participations table =====
            print("📝 Step 2: Adding columns to event_participations table...")

            await conn.execute(text("ALTER TABLE event_participations ADD COLUMN IF NOT EXISTS checkin_date DATE"))
            await conn.execute(text("ALTER TABLE event_participations ADD COLUMN IF NOT EXISTS code_used BOOLEAN DEFAULT FALSE"))
            await conn.execute(text("ALTER TABLE event_participations ADD COLUMN IF NOT EXISTS code_expires_at TIMESTAMP WITH TIME ZONE"))
            print("   ✅ Event Participations table columns handled")

            # ===== 3. Add new status to enum (DYNAMIC FIX) =====
            print("📝 Step 3: Adding 'expired' status...")

            # 🔍 Find the ACTUAL name of the enum type from the database
            # SQLAlchemy might have named it 'participation_status', 'participationstatus', or similar
            result = await conn.execute(text("""
                SELECT udt_name 
                FROM information_schema.columns 
                WHERE table_name = 'event_participations' 
                AND column_name = 'status';
            """))
            enum_name = result.scalar()

            if not enum_name:
                print("   ❌ Could not find Enum type for 'status' column. Skipping Step 3.")
            else:
                print(f"   ℹ️  Found Enum Type Name: '{enum_name}'")
                # Use the detected name to alter the type safely
                await conn.execute(text(f"""
                    ALTER TYPE "{enum_name}" ADD VALUE IF NOT EXISTS 'expired';
                """))
                print(f"   ✅ 'expired' status added to '{enum_name}'")

            # ===== 4. Create indexes =====
            print("📝 Step 4: Creating indexes...")
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_participations_checkin_date ON event_participations(checkin_date)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_participations_user_event_date ON event_participations(user_id, event_id, checkin_date)"))
            print("   ✅ Indexes handled")

            # ===== 5. Migrate existing data =====
            print("📝 Step 5: Migrating existing data...")
            await conn.execute(text("""
                UPDATE event_participations 
                SET checkin_date = DATE(joined_at)
                WHERE checkin_date IS NULL AND joined_at IS NOT NULL;
            """))
            print("   ✅ Existing participations migrated")

            await trans.commit()
            print()
            print("🎉 Migration completed successfully!")
            return True

        except Exception as e:
            await trans.rollback()
            print(f"❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            return False

async def verify_migration():
    print()
    print("🔍 Verifying migration...")
    async with engine.connect() as conn:
        try:
            # Check events table columns
            result = await conn.execute(text("""
                SELECT column_name, data_type, udt_name
                FROM information_schema.columns 
                WHERE table_name = 'event_participations' 
                AND column_name = 'status';
            """))
            status_col = result.fetchone()
            print(f"   📊 Status Column Type: {status_col.udt_name if status_col else 'Not Found'}")

            print("✅ Verification finished!")
            return True
        except Exception as e:
            print(f"❌ Verification failed: {e}")
            return False

async def main():
    print("=" * 70)
    print(" KU RUN - Daily Check-in Migration (Fix)")
    print("=" * 70)
    try:
        if await migrate_daily_checkin():
            await verify_migration()
    except KeyboardInterrupt:
        print("\n❌ Migration cancelled")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())