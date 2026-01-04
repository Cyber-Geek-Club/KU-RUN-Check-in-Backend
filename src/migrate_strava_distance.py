"""
Database Migration Script: Add Strava link and actual distance to event_participations
Run: python src/migrate_strava_distance.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from src.database.db_config import engine


async def migrate_strava_distance():
    """Add strava_link and actual_distance_km columns"""
    print("🔄 Starting migration: Add Strava and distance tracking...")
    print()

    async with engine.begin() as conn:
        try:
            # Check existing columns
            print("📝 Checking existing columns...")
            result = await conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'event_participations' 
                AND column_name IN ('strava_link', 'actual_distance_km');
            """))
            existing_columns = [row[0] for row in result.fetchall()]

            if 'strava_link' in existing_columns and 'actual_distance_km' in existing_columns:
                print("   ℹ️  Columns already exist. Skipping...")
                return True

            # Add strava_link column
            if 'strava_link' not in existing_columns:
                print("📝 Adding strava_link column...")
                await conn.execute(text("""
                    ALTER TABLE event_participations 
                    ADD COLUMN strava_link VARCHAR(500);
                """))
                print("   ✅ strava_link column added")
            else:
                print("   ℹ️  strava_link already exists")

            # Add actual_distance_km column
            if 'actual_distance_km' not in existing_columns:
                print("📝 Adding actual_distance_km column...")
                await conn.execute(text("""
                    ALTER TABLE event_participations 
                    ADD COLUMN actual_distance_km DECIMAL(6,2);
                """))
                print("   ✅ actual_distance_km column added")
            else:
                print("   ℹ️  actual_distance_km already exists")

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
                SELECT column_name, data_type, character_maximum_length
                FROM information_schema.columns 
                WHERE table_name = 'event_participations' 
                AND column_name IN ('strava_link', 'actual_distance_km')
                ORDER BY column_name;
            """))

            columns = result.fetchall()
            if columns:
                print("📊 Column Details:")
                for col in columns:
                    if col[2]:
                        print(f"   - {col[0]}: {col[1]}({col[2]})")
                    else:
                        print(f"   - {col[0]}: {col[1]}")
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
    print(" KU RUN - Add Strava & Distance Tracking Migration")
    print("=" * 70)
    print()
    print("📋 This script will:")
    print("   1. Add 'strava_link' column (VARCHAR(500)) - optional Strava activity link")
    print("   2. Add 'actual_distance_km' column (DECIMAL(6,2)) - actual distance ran")
    print()
    print("💡 Use cases:")
    print("   - Users can submit Strava link as proof")
    print("   - System tracks actual distance vs event distance")
    print("   - Can calculate total distance statistics")
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
        success = await migrate_strava_distance()

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
        print("   1. Update EventParticipation model")
        print("   2. Update participation schemas")
        print("   3. Update participation CRUD")
        print("   4. Update participation endpoints")
        print("   5. Create user statistics endpoint")
        print("   6. Restart your FastAPI server")
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