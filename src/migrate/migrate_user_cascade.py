"""
Database Migration Script: Add CASCADE DELETE to user foreign keys
Save this file as: src/migrate_user_cascade.py
Run: python src/migrate_user_cascade.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from src.database.db_config import engine


async def migrate_user_cascade():
    """
    Add CASCADE DELETE to all foreign keys referencing users table
    """
    print("🔄 Starting migration: Add CASCADE DELETE for user foreign keys...")
    print()

    async with engine.begin() as conn:
        try:
            # ===== 1. event_participations.user_id =====
            print("📝 Step 1: Updating event_participations.user_id...")

            # Drop old constraint
            await conn.execute(text("""
                ALTER TABLE event_participations 
                DROP CONSTRAINT IF EXISTS event_participations_user_id_fkey;
            """))
            print("   ✅ Old constraint dropped")

            # Add new constraint with CASCADE
            await conn.execute(text("""
                ALTER TABLE event_participations 
                ADD CONSTRAINT event_participations_user_id_fkey 
                FOREIGN KEY (user_id) 
                REFERENCES users(id) 
                ON DELETE CASCADE;
            """))
            print("   ✅ New constraint added with CASCADE DELETE")
            print()

            # ===== 2. event_participations.checked_in_by =====
            print("📝 Step 2: Updating event_participations.checked_in_by...")

            await conn.execute(text("""
                ALTER TABLE event_participations 
                DROP CONSTRAINT IF EXISTS event_participations_checked_in_by_fkey;
            """))
            print("   ✅ Old constraint dropped")

            await conn.execute(text("""
                ALTER TABLE event_participations 
                ADD CONSTRAINT event_participations_checked_in_by_fkey 
                FOREIGN KEY (checked_in_by) 
                REFERENCES users(id) 
                ON DELETE SET NULL;
            """))
            print("   ✅ New constraint added with SET NULL")
            print()

            # ===== 3. event_participations.completed_by =====
            print("📝 Step 3: Updating event_participations.completed_by...")

            await conn.execute(text("""
                ALTER TABLE event_participations 
                DROP CONSTRAINT IF EXISTS event_participations_completed_by_fkey;
            """))
            print("   ✅ Old constraint dropped")

            await conn.execute(text("""
                ALTER TABLE event_participations 
                ADD CONSTRAINT event_participations_completed_by_fkey 
                FOREIGN KEY (completed_by) 
                REFERENCES users(id) 
                ON DELETE SET NULL;
            """))
            print("   ✅ New constraint added with SET NULL")
            print()

            # ===== 4. event_participations.rejected_by =====
            print("📝 Step 4: Updating event_participations.rejected_by...")

            await conn.execute(text("""
                ALTER TABLE event_participations 
                DROP CONSTRAINT IF EXISTS event_participations_rejected_by_fkey;
            """))
            print("   ✅ Old constraint dropped")

            await conn.execute(text("""
                ALTER TABLE event_participations 
                ADD CONSTRAINT event_participations_rejected_by_fkey 
                FOREIGN KEY (rejected_by) 
                REFERENCES users(id) 
                ON DELETE SET NULL;
            """))
            print("   ✅ New constraint added with SET NULL")
            print()

            # ===== 5. events.created_by =====
            print("📝 Step 5: Updating events.created_by...")

            await conn.execute(text("""
                ALTER TABLE events 
                DROP CONSTRAINT IF EXISTS events_created_by_fkey;
            """))
            print("   ✅ Old constraint dropped")

            await conn.execute(text("""
                ALTER TABLE events 
                ADD CONSTRAINT events_created_by_fkey 
                FOREIGN KEY (created_by) 
                REFERENCES users(id) 
                ON DELETE SET NULL;
            """))
            print("   ✅ New constraint added with SET NULL")
            print()

            # ===== 6. user_rewards.user_id =====
            print("📝 Step 6: Updating user_rewards.user_id...")

            await conn.execute(text("""
                ALTER TABLE user_rewards 
                DROP CONSTRAINT IF EXISTS user_rewards_user_id_fkey;
            """))
            print("   ✅ Old constraint dropped")

            await conn.execute(text("""
                ALTER TABLE user_rewards 
                ADD CONSTRAINT user_rewards_user_id_fkey 
                FOREIGN KEY (user_id) 
                REFERENCES users(id) 
                ON DELETE CASCADE;
            """))
            print("   ✅ New constraint added with CASCADE DELETE")
            print()

            # ===== 7. notifications.user_id =====
            print("📝 Step 7: Updating notifications.user_id...")

            await conn.execute(text("""
                ALTER TABLE notifications 
                DROP CONSTRAINT IF EXISTS notifications_user_id_fkey;
            """))
            print("   ✅ Old constraint dropped")

            await conn.execute(text("""
                ALTER TABLE notifications 
                ADD CONSTRAINT notifications_user_id_fkey 
                FOREIGN KEY (user_id) 
                REFERENCES users(id) 
                ON DELETE CASCADE;
            """))
            print("   ✅ New constraint added with CASCADE DELETE")
            print()

            # ===== 8. password_reset_logs.user_id (if exists) =====
            print("📝 Step 8: Checking password_reset_logs.user_id...")

            # Check if table exists
            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'password_reset_logs'
                );
            """))
            table_exists = result.scalar()

            if table_exists:
                await conn.execute(text("""
                    ALTER TABLE password_reset_logs 
                    DROP CONSTRAINT IF EXISTS password_reset_logs_user_id_fkey;
                """))
                print("   ✅ Old constraint dropped")

                await conn.execute(text("""
                    ALTER TABLE password_reset_logs 
                    ADD CONSTRAINT password_reset_logs_user_id_fkey 
                    FOREIGN KEY (user_id) 
                    REFERENCES users(id) 
                    ON DELETE CASCADE;
                """))
                print("   ✅ New constraint added with CASCADE DELETE")
            else:
                print("   ℹ️  Table password_reset_logs doesn't exist, skipping...")
            print()

            print("🎉 Migration completed successfully!")
            return True

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            return False


async def verify_constraints():
    """Verify all foreign key constraints"""
    print()
    print("🔍 Verifying all foreign key constraints...")
    print()

    async with engine.begin() as conn:
        try:
            result = await conn.execute(text("""
                SELECT 
                    tc.table_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    rc.delete_rule
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                JOIN information_schema.referential_constraints AS rc
                    ON rc.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND ccu.table_name = 'users'
                ORDER BY tc.table_name, kcu.column_name;
            """))

            rows = result.fetchall()

            if rows:
                print("📊 Foreign Key Constraints to users table:")
                print()
                print(f"{'Table':<30} {'Column':<25} {'Delete Rule':<15}")
                print("-" * 70)

                for row in rows:
                    table = row[0]
                    column = row[1]
                    delete_rule = row[3]

                    # Color code based on delete rule
                    if delete_rule == 'CASCADE':
                        status = "✅ CASCADE"
                    elif delete_rule == 'SET NULL':
                        status = "✅ SET NULL"
                    else:
                        status = f"⚠️  {delete_rule}"

                    print(f"{table:<30} {column:<25} {status}")

                print()
                print("✅ All constraints verified!")
                return True
            else:
                print("❌ No foreign key constraints found")
                return False

        except Exception as e:
            print(f"❌ Verification failed: {e}")
            return False


async def show_summary():
    """Show summary of what will happen"""
    print("=" * 70)
    print(" KU RUN - User CASCADE DELETE Migration")
    print("=" * 70)
    print()
    print("📋 This script will update foreign key constraints:")
    print()
    print("   CASCADE DELETE (ลบข้อมูลตาม):")
    print("   - event_participations.user_id")
    print("   - user_rewards.user_id")
    print("   - notifications.user_id")
    print("   - password_reset_logs.user_id")
    print()
    print("   SET NULL (ตั้งเป็น NULL):")
    print("   - event_participations.checked_in_by")
    print("   - event_participations.completed_by")
    print("   - event_participations.rejected_by")
    print("   - events.created_by")
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
        success = await migrate_user_cascade()

        if success:
            await verify_constraints()

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
        print("   2. Try deleting a user - related data will be handled automatically:")
        print("      - Participations → CASCADE (deleted)")
        print("      - Rewards → CASCADE (deleted)")
        print("      - Notifications → CASCADE (deleted)")
        print("      - Staff references → SET NULL")
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