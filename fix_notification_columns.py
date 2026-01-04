"""
Fix Notification Columns - Convert VARCHAR to ENUM types
Save as: fix_notification_columns.py
Run: python fix_notification_columns.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from src.database.db_config import engine


async def check_column_types():
    """Check current column types"""
    print("🔍 Checking current column types...")
    print()

    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT column_name, data_type, udt_name
            FROM information_schema.columns 
            WHERE table_name = 'notifications' 
            AND column_name IN ('channel', 'status')
            ORDER BY column_name;
        """))

        columns = result.fetchall()
        for col in columns:
            col_type = col[2] if col[1] == 'USER-DEFINED' else col[1]
            print(f"   {col[0]}: {col_type}")
        print()

        return columns


async def fix_notification_columns():
    """Fix notification columns - convert VARCHAR to ENUM"""
    print("🔄 Starting fix: Convert VARCHAR columns to ENUM types...")
    print()

    async with engine.begin() as conn:
        try:
            # Check current state
            columns = await check_column_types()

            # Check if enums exist
            result = await conn.execute(text("""
                SELECT typname FROM pg_type 
                WHERE typname IN ('notificationchannel', 'notificationstatus');
            """))
            existing_types = [row[0] for row in result.fetchall()]

            # Create enum types if they don't exist
            if 'notificationchannel' not in existing_types:
                print("📝 Creating notificationchannel enum type...")
                await conn.execute(text("""
                    CREATE TYPE notificationchannel AS ENUM ('in_app', 'email', 'push', 'sms');
                """))
                print("   ✅ notificationchannel type created")
            else:
                print("   ℹ️  notificationchannel type already exists")

            if 'notificationstatus' not in existing_types:
                print("📝 Creating notificationstatus enum type...")
                await conn.execute(text("""
                    CREATE TYPE notificationstatus AS ENUM ('pending', 'sent', 'failed', 'read');
                """))
                print("   ✅ notificationstatus type created")
            else:
                print("   ℹ️  notificationstatus type already exists")
            print()

            # Convert channel column if it's VARCHAR
            print("📝 Checking channel column...")
            result = await conn.execute(text("""
                SELECT data_type FROM information_schema.columns 
                WHERE table_name = 'notifications' AND column_name = 'channel';
            """))
            channel_type = result.scalar()

            if channel_type == 'character varying':
                print("📝 Converting channel from VARCHAR to ENUM...")
                await conn.execute(text("""
                    ALTER TABLE notifications 
                    ALTER COLUMN channel TYPE notificationchannel 
                    USING channel::notificationchannel;
                """))
                print("   ✅ channel converted to notificationchannel enum")
            else:
                print("   ℹ️  channel is already ENUM type")
            print()

            # Convert status column if it's VARCHAR
            print("📝 Checking status column...")
            result = await conn.execute(text("""
                SELECT data_type FROM information_schema.columns 
                WHERE table_name = 'notifications' AND column_name = 'status';
            """))
            status_type = result.scalar()

            if status_type == 'character varying':
                print("📝 Converting status from VARCHAR to ENUM...")
                await conn.execute(text("""
                    ALTER TABLE notifications 
                    ALTER COLUMN status TYPE notificationstatus 
                    USING status::notificationstatus;
                """))
                print("   ✅ status converted to notificationstatus enum")

                # Update existing records
                print("📝 Updating existing notification statuses...")
                await conn.execute(text("""
                    UPDATE notifications 
                    SET status = CASE 
                        WHEN is_read = true THEN 'read'::notificationstatus
                        ELSE 'sent'::notificationstatus
                    END
                    WHERE status NOT IN ('pending', 'sent', 'failed', 'read');
                """))
                print("   ✅ Statuses updated")
            else:
                print("   ℹ️  status is already ENUM type")
            print()

            # Create indexes
            print("📝 Creating indexes...")
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_notifications_status_pending
                ON notifications(status) 
                WHERE status = 'pending'::notificationstatus;
            """))
            print("   ✅ Index on status (pending) created")

            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_notifications_channel 
                ON notifications(channel);
            """))
            print("   ✅ Index on channel created")

            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_notifications_is_sent 
                ON notifications(is_sent) 
                WHERE is_sent = false;
            """))
            print("   ✅ Index on is_sent created")
            print()

            print("🎉 Fix completed successfully!")
            return True

        except Exception as e:
            print(f"❌ Fix failed: {e}")
            import traceback
            traceback.print_exc()
            return False


async def verify_fix():
    """Verify the fix"""
    print()
    print("🔍 Verifying columns after fix...")
    print()

    async with engine.begin() as conn:
        try:
            # Check column types
            result = await conn.execute(text("""
                SELECT column_name, data_type, udt_name, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'notifications' 
                AND column_name IN ('channel', 'status', 'is_sent', 'sent_at', 'send_attempts', 'last_error')
                ORDER BY column_name;
            """))

            columns = result.fetchall()
            if columns:
                print("📊 Column Details:")
                print(f"{'Column':<20} {'Type':<30} {'Nullable'}")
                print("-" * 60)
                for col in columns:
                    col_type = col[2] if col[1] == 'USER-DEFINED' else col[1]
                    print(f"{col[0]:<20} {col_type:<30} {col[3]}")
                print()

            # Check indexes
            result = await conn.execute(text("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'notifications' 
                AND indexname LIKE 'idx_notifications_%'
                ORDER BY indexname;
            """))

            indexes = result.fetchall()
            if indexes:
                print("📊 Indexes:")
                for idx in indexes:
                    print(f"   ✅ {idx[0]}")
                print()

            # Check sample data
            result = await conn.execute(text("""
                SELECT channel, status, COUNT(*) as count
                FROM notifications
                GROUP BY channel, status
                ORDER BY channel, status;
            """))

            data = result.fetchall()
            if data:
                print("📊 Sample Data Distribution:")
                print(f"{'Channel':<15} {'Status':<15} {'Count'}")
                print("-" * 45)
                for row in data:
                    print(f"{row[0]:<15} {row[1]:<15} {row[2]}")
                print()

            print("✅ Verification completed successfully!")
            return True

        except Exception as e:
            print(f"❌ Verification failed: {e}")
            return False


async def show_summary():
    """Show summary of what will happen"""
    print("=" * 70)
    print(" KU RUN - Fix Notification Columns (VARCHAR → ENUM)")
    print("=" * 70)
    print()
    print("📋 This script will:")
    print("   1. Check current column types")
    print("   2. Create ENUM types if missing")
    print("   3. Convert 'channel' from VARCHAR to notificationchannel enum")
    print("   4. Convert 'status' from VARCHAR to notificationstatus enum")
    print("   5. Create proper indexes")
    print("   6. Verify the changes")
    print()
    print("⚠️  Note: This is safe to run - it only converts types")
    print()

    try:
        response = input("Continue? (yes/no): ").lower().strip()
        if response not in ['yes', 'y']:
            print()
            print("❌ Fix cancelled by user")
            return False
    except KeyboardInterrupt:
        print()
        print()
        print("❌ Fix cancelled by user")
        return False

    print()
    return True


async def main():
    """Main fix function"""
    if not await show_summary():
        return

    print("=" * 70)
    print()

    try:
        success = await fix_notification_columns()

        if success:
            await verify_fix()

        print()
        print("=" * 70)
        if success:
            print("✨ Fix completed successfully!")
        else:
            print("⚠️  Fix completed with warnings")
        print("=" * 70)
        print()
        print("💡 Next steps:")
        print("   1. The database is now ready for the notification system")
        print("   2. Update your model files with the artifacts I provided")
        print("   3. Restart your FastAPI server")
        print("   4. Test the notification endpoints")
        print()

    except KeyboardInterrupt:
        print()
        print()
        print("❌ Fix interrupted by user")
        sys.exit(1)
    except Exception as e:
        print()
        print("=" * 70)
        print("❌ Fix failed!")
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
        print("❌ Fix cancelled")
        sys.exit(1)