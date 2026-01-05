"""
Database Migration Script: Add CASCADE DELETE to event_participations
Save this file as: migrate_cascade.py in your project root folder
Then run: python migrate_cascade.py
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from src.database.db_config import engine


async def migrate_cascade_delete():
    """
    Add CASCADE DELETE to event_participations.event_id foreign key
    """
    print("🔄 Starting migration: Add CASCADE DELETE...")
    print()

    async with engine.begin() as conn:
        try:
            # Step 1: Drop existing foreign key constraint
            print("📝 Step 1: Dropping existing foreign key constraint...")
            await conn.execute(text("""
                ALTER TABLE event_participations 
                DROP CONSTRAINT IF EXISTS event_participations_event_id_fkey;
            """))
            print("   ✅ Old constraint dropped")
            print()

            # Step 2: Add new foreign key constraint with CASCADE DELETE
            print("📝 Step 2: Adding new foreign key constraint with CASCADE...")
            await conn.execute(text("""
                ALTER TABLE event_participations 
                ADD CONSTRAINT event_participations_event_id_fkey 
                FOREIGN KEY (event_id) 
                REFERENCES events(id) 
                ON DELETE CASCADE;
            """))
            print("   ✅ New constraint added with CASCADE DELETE")
            print()

            # Step 3: Verify the constraint
            print("📝 Step 3: Verifying constraint...")
            result = await conn.execute(text("""
                SELECT 
                    conname AS constraint_name,
                    confdeltype AS delete_action
                FROM pg_constraint
                WHERE conname = 'event_participations_event_id_fkey';
            """))

            row = result.fetchone()
            if row:
                delete_action = row[1]
                action_map = {
                    'a': 'NO ACTION',
                    'r': 'RESTRICT',
                    'c': 'CASCADE',
                    'n': 'SET NULL',
                    'd': 'SET DEFAULT'
                }
                action_text = action_map.get(delete_action, 'UNKNOWN')
                print(f"   ✅ Constraint verified: {action_text}")
                print()

                if delete_action == 'c':
                    print("🎉 Migration completed successfully!")
                else:
                    print(f"⚠️  Warning: Delete action is {action_text}, expected CASCADE")
            else:
                print("   ❌ Error: Could not verify constraint")

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            print()
            print("💡 Possible solutions:")
            print("   1. Check if PostgreSQL is running")
            print("   2. Verify DATABASE_URL in .env file")
            print("   3. Ensure you have database permissions")
            raise

    print()


async def verify_cascade():
    """Verify that CASCADE DELETE is working"""
    print("🔍 Testing CASCADE DELETE configuration...")
    print()

    async with engine.begin() as conn:
        try:
            # Check if there are any constraints
            result = await conn.execute(text("""
                SELECT 
                    tc.constraint_name,
                    tc.table_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name,
                    rc.delete_rule
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                JOIN information_schema.referential_constraints AS rc
                    ON rc.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_name = 'event_participations'
                    AND kcu.column_name = 'event_id';
            """))

            row = result.fetchone()
            if row:
                print("📊 Foreign Key Configuration:")
                print(f"   Table: {row[1]}")
                print(f"   Column: {row[2]}")
                print(f"   References: {row[3]}.{row[4]}")
                print(f"   On Delete: {row[5]}")
                print()

                if row[5] == 'CASCADE':
                    print("✅ CASCADE DELETE is properly configured!")
                    return True
                else:
                    print(f"⚠️  Warning: Delete rule is {row[5]}, not CASCADE")
                    return False
            else:
                print("❌ Could not find foreign key constraint")
                return False

        except Exception as e:
            print(f"❌ Verification failed: {e}")
            return False


async def show_summary():
    """Show summary of what will happen"""
    print("=" * 70)
    print(" KU RUN - Database Migration Tool")
    print("=" * 70)
    print()
    print("📋 This script will:")
    print("   1. Drop the existing foreign key constraint")
    print("   2. Add a new constraint with CASCADE DELETE")
    print("   3. Verify the changes")
    print()
    print("⚠️  Warning: This will modify your database structure!")
    print()

    # Wait for user confirmation
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
    # Show summary
    if not await show_summary():
        return

    print("=" * 70)
    print()

    try:
        # Run migration
        await migrate_cascade_delete()

        # Verify migration
        success = await verify_cascade()

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
        print("   2. Try deleting an event with participations")
        print("   3. Verify that participations are deleted automatically")
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