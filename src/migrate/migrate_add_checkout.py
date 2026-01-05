"""
Migration: Add check-out functionality to event_participations
Run: python migrate_add_checkout.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from src.database.db_config import engine


async def add_checkout_columns():
    print("🔄 Adding check-out columns...")
    print()

    async with engine.begin() as conn:
        try:
            # 1. Check existing columns
            print("📝 Checking existing columns...")
            result = await conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'event_participations' 
                AND column_name IN ('checked_out_by', 'checked_out_at');
            """))
            existing = [row[0] for row in result.fetchall()]

            if 'checked_out_by' in existing and 'checked_out_at' in existing:
                print("   ℹ️  Columns already exist. Skipping...")
                return True

            # 2. Add checked_out_by
            if 'checked_out_by' not in existing:
                print("📝 Adding checked_out_by column...")
                await conn.execute(text("""
                    ALTER TABLE event_participations 
                    ADD COLUMN checked_out_by INTEGER REFERENCES users(id) ON DELETE SET NULL;
                """))
                print("   ✅ checked_out_by added")
            else:
                print("   ℹ️  checked_out_by exists")

            # 3. Add checked_out_at
            if 'checked_out_at' not in existing:
                print("📝 Adding checked_out_at column...")
                await conn.execute(text("""
                    ALTER TABLE event_participations 
                    ADD COLUMN checked_out_at TIMESTAMP WITH TIME ZONE;
                """))
                print("   ✅ checked_out_at added")
            else:
                print("   ℹ️  checked_out_at exists")

            print()

            # 4. Add checked_out status to enum (if using enum)
            print("📝 Adding 'checked_out' status...")

            # Find enum type name
            result = await conn.execute(text("""
                SELECT udt_name 
                FROM information_schema.columns 
                WHERE table_name = 'event_participations' 
                AND column_name = 'status';
            """))
            enum_name = result.scalar()

            if enum_name and enum_name.lower() not in ('varchar', 'text', 'string'):
                await conn.execute(text(f"""
                    ALTER TYPE "{enum_name}" ADD VALUE IF NOT EXISTS 'checked_out';
                """))
                print(f"   ✅ 'checked_out' status added to '{enum_name}'")
            else:
                print(f"   ℹ️  Column is text type ('{enum_name}'). No enum update needed.")

            print()
            print("🎉 Migration completed!")
            return True

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            return False


async def verify_columns():
    print()
    print("🔍 Verifying columns...")
    print()

    async with engine.begin() as conn:
        try:
            result = await conn.execute(text("""
                SELECT column_name, data_type
                FROM information_schema.columns 
                WHERE table_name = 'event_participations' 
                AND column_name IN ('checked_out_by', 'checked_out_at')
                ORDER BY column_name;
            """))

            columns = result.fetchall()
            if columns:
                print("📊 Column Details:")
                for col in columns:
                    print(f"   - {col[0]}: {col[1]}")
                print()
                print("✅ Columns verified!")
                return True
            else:
                print("❌ Columns not found")
                return False

        except Exception as e:
            print(f"❌ Verification failed: {e}")
            return False


async def main():
    print("=" * 70)
    print(" KU RUN - Add Check-out Functionality")
    print("=" * 70)
    print()
    print("📋 This script will:")
    print("   1. Add 'checked_out_by' column (INTEGER)")
    print("   2. Add 'checked_out_at' column (TIMESTAMP)")
    print("   3. Add 'checked_out' status to enum")
    print()

    try:
        response = input("Continue? (yes/no): ").lower().strip()
        if response not in ['yes', 'y']:
            print()
            print("❌ Migration cancelled")
            return
    except KeyboardInterrupt:
        print()
        print()
        print("❌ Migration cancelled")
        return

    print()
    print("=" * 70)
    print()

    try:
        success = await add_checkout_columns()

        if success:
            await verify_columns()

        print()
        print("=" * 70)
        if success:
            print("✨ Migration completed!")
        else:
            print("⚠️  Migration failed")
        print("=" * 70)
        print()
        print("💡 Next steps:")
        print("   1. Restart FastAPI server")
        print("   2. Test check-out endpoint:")
        print("      POST /api/participations/check-out")
        print("      { \"join_code\": \"12345\" }")
        print()

    except KeyboardInterrupt:
        print()
        print()
        print("❌ Migration interrupted")
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