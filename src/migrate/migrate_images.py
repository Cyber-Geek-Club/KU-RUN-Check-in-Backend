"""
Database Migration Script: Add image-related columns
Save as: src/migrate_images.py
Run: python src/migrate_images.py
"""
import asyncio
import sys
import os

# Fix path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from src.database.db_config import engine


async def migrate_image_columns():
    """Add image-related columns to tables"""
    print("🔄 Starting migration: Add image columns...")
    print()

    async with engine.begin() as conn:
        try:
            # Check existing columns
            print("📝 Checking existing columns...")

            # Check events table
            result = await conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'events' 
                AND column_name = 'banner_image_url';
            """))
            events_has_banner = result.fetchone() is not None

            # Check event_participations table
            result = await conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'event_participations' 
                AND column_name = 'proof_image_url';
            """))
            participations_has_proof = result.fetchone() is not None

            # Check rewards table
            result = await conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'rewards' 
                AND column_name = 'badge_image_url';
            """))
            rewards_has_badge = result.fetchone() is not None

            print()

            # Add banner_image_url to events
            if not events_has_banner:
                print("📝 Adding banner_image_url to events table...")
                await conn.execute(text("""
                    ALTER TABLE events 
                    ADD COLUMN banner_image_url VARCHAR(500);
                """))
                print("   ✅ banner_image_url added to events")
            else:
                print("   ℹ️  events.banner_image_url already exists")

            # Add proof_image_url to event_participations
            if not participations_has_proof:
                print("📝 Adding proof_image_url to event_participations table...")
                await conn.execute(text("""
                    ALTER TABLE event_participations 
                    ADD COLUMN proof_image_url VARCHAR(500);
                """))
                print("   ✅ proof_image_url added to event_participations")
            else:
                print("   ℹ️  event_participations.proof_image_url already exists")

            # Add badge_image_url to rewards
            if not rewards_has_badge:
                print("📝 Adding badge_image_url to rewards table...")
                await conn.execute(text("""
                    ALTER TABLE rewards 
                    ADD COLUMN badge_image_url VARCHAR(500);
                """))
                print("   ✅ badge_image_url added to rewards")
            else:
                print("   ℹ️  rewards.badge_image_url already exists")

            print()

            if not events_has_banner and not participations_has_proof and not rewards_has_badge:
                print("🎉 All image columns added successfully!")
            elif events_has_banner and participations_has_proof and rewards_has_badge:
                print("ℹ️  All image columns already exist. No changes needed.")
            else:
                print("✅ Migration completed with some columns added.")

            return True

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            return False


async def verify_columns():
    """Verify that all image columns exist"""
    print()
    print("🔍 Verifying image columns...")
    print()

    async with engine.begin() as conn:
        try:
            # Check all image columns
            result = await conn.execute(text("""
                SELECT 
                    table_name,
                    column_name,
                    data_type,
                    character_maximum_length
                FROM information_schema.columns 
                WHERE (
                    (table_name = 'events' AND column_name = 'banner_image_url') OR
                    (table_name = 'event_participations' AND column_name = 'proof_image_url') OR
                    (table_name = 'rewards' AND column_name = 'badge_image_url')
                )
                ORDER BY table_name, column_name;
            """))

            columns = result.fetchall()
            if columns:
                print("📊 Image Column Details:")
                for col in columns:
                    max_len = f"({col[3]})" if col[3] else ""
                    print(f"   - {col[0]}.{col[1]}: {col[2]}{max_len}")
                print()
                print("✅ All image columns verified!")
                return True
            else:
                print("❌ No image columns found")
                return False

        except Exception as e:
            print(f"❌ Verification failed: {e}")
            return False


async def create_upload_directories():
    """Create upload directories if they don't exist"""
    print()
    print("📁 Creating upload directories...")
    print()

    try:
        import os
        from pathlib import Path

        upload_dirs = [
            "uploads",
            "uploads/events",
            "uploads/proofs",
            "uploads/rewards"
        ]

        for dir_path in upload_dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            print(f"   ✅ {dir_path}/")

        print()
        print("✅ All upload directories created!")
        return True

    except Exception as e:
        print(f"❌ Failed to create directories: {e}")
        return False


async def show_summary():
    """Show summary of what will happen"""
    print("=" * 70)
    print(" KU RUN - Image Columns Migration")
    print("=" * 70)
    print()
    print("📋 This script will:")
    print("   1. Add 'banner_image_url' to events table (VARCHAR(500))")
    print("   2. Add 'proof_image_url' to event_participations table (VARCHAR(500))")
    print("   3. Add 'badge_image_url' to rewards table (VARCHAR(500))")
    print("   4. Create upload directories (uploads/events, uploads/proofs, uploads/rewards)")
    print("   5. Verify all changes")
    print()
    print("⚠️  Note: This is safe to run multiple times (idempotent)")
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
        # Run migrations
        success = await migrate_image_columns()

        if success:
            # Verify
            await verify_columns()

            # Create directories
            await create_upload_directories()

        print()
        print("=" * 70)
        if success:
            print("✨ Migration completed successfully!")
        else:
            print("⚠️  Migration completed with warnings")
        print("=" * 70)
        print()
        print("💡 Next steps:")
        print("   1. Restart your FastAPI server")
        print("   2. Test image upload endpoints:")
        print("      - POST /api/images/upload")
        print("      - DELETE /api/images/delete")
        print("   3. Verify uploaded images are saved in uploads/ directory")
        print()
        print("📝 Image URL format:")
        print("   - Events: /uploads/events/[filename]")
        print("   - Proofs: /uploads/proofs/[filename]")
        print("   - Rewards: /uploads/rewards/[filename]")
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
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()
        print()
        print("❌ Migration cancelled")
        sys.exit(1)