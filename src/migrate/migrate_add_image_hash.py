"""
Migration: Add image_hash column to event_participations
Run: python migrate_add_image_hash.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from src.database.db_config import engine


async def add_image_hash_column():
    print("🔄 Adding image_hash column...")
    print()

    async with engine.begin() as conn:
        try:
            # Check if column exists
            print("📝 Checking existing columns...")
            result = await conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'event_participations' 
                AND column_name = 'proof_image_hash';
            """))

            if result.fetchone():
                print("   ℹ️  Column already exists. Skipping...")
                return True

            # Add image_hash column
            print("📝 Adding proof_image_hash column...")
            await conn.execute(text("""
                ALTER TABLE event_participations 
                ADD COLUMN proof_image_hash VARCHAR(64);
            """))
            print("   ✅ proof_image_hash column added")
            print()

            # Create index for faster duplicate detection
            print("📝 Creating index...")
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_proof_image_hash 
                ON event_participations(proof_image_hash);
            """))
            print("   ✅ Index created")
            print()

            print("🎉 Migration completed successfully!")
            return True

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            return False


async def verify_column():
    print()
    print("🔍 Verifying column...")
    print()

    async with engine.begin() as conn:
        try:
            result = await conn.execute(text("""
                SELECT column_name, data_type, character_maximum_length
                FROM information_schema.columns 
                WHERE table_name = 'event_participations' 
                AND column_name = 'proof_image_hash';
            """))

            col = result.fetchone()
            if col:
                print(f"📊 Column: {col[0]} ({col[1]})")
                print("✅ Column verified!")
                return True
            else:
                print("❌ Column not found")
                return False

        except Exception as e:
            print(f"❌ Verification failed: {e}")
            return False


async def main():
    print("=" * 70)
    print(" Add Image Hash Column Migration")
    print("=" * 70)
    print()

    try:
        success = await add_image_hash_column()

        if success:
            await verify_column()

        print()
        print("=" * 70)
        if success:
            print("✨ Migration completed!")
        else:
            print("⚠️  Migration failed")
        print("=" * 70)
        print()

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())