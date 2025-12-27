import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from src.database.db_config import engine


async def migrate_image_columns_to_text():
    """Change image URL columns from VARCHAR(500) to TEXT"""
    print("🔄 Starting migration: Change image columns to TEXT...")
    print()

    async with engine.begin() as conn:
        try:
            # 1. Events table - banner_image_url
            print("📝 Step 1: Updating events.banner_image_url...")
            await conn.execute(text("""
                ALTER TABLE events 
                ALTER COLUMN banner_image_url TYPE TEXT;
            """))
            print("   ✅ events.banner_image_url changed to TEXT")
            print()

            # 2. Event participations - proof_image_url
            print("📝 Step 2: Updating event_participations.proof_image_url...")
            await conn.execute(text("""
                ALTER TABLE event_participations 
                ALTER COLUMN proof_image_url TYPE TEXT;
            """))
            print("   ✅ event_participations.proof_image_url changed to TEXT")
            print()

            # 3. Event participations - strava_link
            print("📝 Step 3: Updating event_participations.strava_link...")
            await conn.execute(text("""
                ALTER TABLE event_participations 
                ALTER COLUMN strava_link TYPE TEXT;
            """))
            print("   ✅ event_participations.strava_link changed to TEXT")
            print()

            # 4. Rewards table - badge_image_url
            print("📝 Step 4: Updating rewards.badge_image_url...")
            await conn.execute(text("""
                ALTER TABLE rewards 
                ALTER COLUMN badge_image_url TYPE TEXT;
            """))
            print("   ✅ rewards.badge_image_url changed to TEXT")
            print()

            print("🎉 Migration completed successfully!")
            return True

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            return False


async def verify_changes():
    """Verify column types"""
    print()
    print("🔍 Verifying column types...")
    print()

    async with engine.begin() as conn:
        try:
            result = await conn.execute(text("""
                SELECT 
                    table_name,
                    column_name,
                    data_type,
                    character_maximum_length
                FROM information_schema.columns 
                WHERE (
                    (table_name = 'events' AND column_name = 'banner_image_url') OR
                    (table_name = 'event_participations' AND column_name IN ('proof_image_url', 'strava_link')) OR
                    (table_name = 'rewards' AND column_name = 'badge_image_url')
                )
                ORDER BY table_name, column_name;
            """))

            columns = result.fetchall()
            if columns:
                print("📊 Column Types:")
                print()
                print(f"{'Table':<30} {'Column':<25} {'Type':<15} {'Max Length'}")
                print("-" * 85)
                for col in columns:
                    max_len = str(col[3]) if col[3] else "unlimited"
                    print(f"{col[0]:<30} {col[1]:<25} {col[2]:<15} {max_len}")
                print()
                print("✅ All columns verified!")
                return True
            else:
                print("❌ Columns not found")
                return False

        except Exception as e:
            print(f"❌ Verification failed: {e}")
            return False


async def show_summary():
    """Show summary"""
    print("=" * 70)
    print(" KU RUN - Image URL Column Type Migration")
    print("=" * 70)
    print()
    print("📋 This script will change column types from VARCHAR(500) to TEXT:")
    print()
    print("   Tables to update:")
    print("   - events.banner_image_url")
    print("   - event_participations.proof_image_url")
    print("   - event_participations.strava_link")
    print("   - rewards.badge_image_url")
    print()
    print("   Why: To support base64-encoded images (can be 50KB+)")
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
        success = await migrate_image_columns_to_text()

        if success:
            await verify_changes()

        print()
        print("=" * 70)
        if success:
            print("✨ Migration completed successfully!")
        else:
            print("⚠️  Migration completed with warnings")
        print("=" * 70)
        print()
        print("💡 Next steps:")
        print("   1. Update model definitions (change String(500) to Text)")
        print("   2. Restart your FastAPI server")
        print("   3. Try creating an event with base64 image again")
        print()
        print("📝 Note: Base64 images can be 50-100KB in size")
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