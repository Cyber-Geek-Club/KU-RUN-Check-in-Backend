"""
Database Migration Script: Add sent notification tracking columns
Save as: migrate_notification_sent.py
Run: python migrate_notification_sent.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from src.database.db_config import engine


async def migrate_notification_sent():
    """Add sent notification tracking columns"""
    print("🔄 Starting migration: Add sent notification tracking...")
    print()

    async with engine.begin() as conn:
        try:
            # Check existing columns
            print("📝 Checking existing columns...")
            result = await conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'notifications' 
                AND column_name IN ('channel', 'status', 'is_sent', 'sent_at', 'send_attempts', 'last_error');
            """))
            existing_columns = [row[0] for row in result.fetchall()]

            # 1. Add channel enum type
            if 'channel' not in existing_columns:
                print("📝 Creating notification channel enum type...")
                await conn.execute(text("""
                    DO $$ BEGIN
                        CREATE TYPE notificationchannel AS ENUM ('in_app', 'email', 'push', 'sms');
                    EXCEPTION
                        WHEN duplicate_object THEN null;
                    END $$;
                """))
                print("   ✅ Enum type created")

            # 2. Add status enum type
            if 'status' not in existing_columns:
                print("📝 Creating notification status enum type...")
                await conn.execute(text("""
                    DO $$ BEGIN
                        CREATE TYPE notificationstatus AS ENUM ('pending', 'sent', 'failed', 'read');
                    EXCEPTION
                        WHEN duplicate_object THEN null;
                    END $$;
                """))
                print("   ✅ Enum type created")

            # 3. Add channel column
            if 'channel' not in existing_columns:
                print("📝 Adding channel column...")
                await conn.execute(text("""
                    ALTER TABLE notifications 
                    ADD COLUMN channel notificationchannel DEFAULT 'in_app' NOT NULL;
                """))
                print("   ✅ channel column added")
            else:
                print("   ℹ️  channel already exists")

            # 4. Add status column
            if 'status' not in existing_columns:
                print("📝 Adding status column...")
                await conn.execute(text("""
                    ALTER TABLE notifications 
                    ADD COLUMN status notificationstatus DEFAULT 'pending' NOT NULL;
                """))
                print("   ✅ status column added")

                # Update existing records based on is_read
                print("📝 Updating existing notification statuses...")
                await conn.execute(text("""
                    UPDATE notifications 
                    SET status = CASE 
                        WHEN is_read = true THEN 'read'::notificationstatus
                        ELSE 'sent'::notificationstatus
                    END;
                """))
                print("   ✅ Statuses updated")
            else:
                print("   ℹ️  status already exists")

            # 5. Add is_sent column
            if 'is_sent' not in existing_columns:
                print("📝 Adding is_sent column...")
                await conn.execute(text("""
                    ALTER TABLE notifications 
                    ADD COLUMN is_sent BOOLEAN DEFAULT false;
                """))
                print("   ✅ is_sent column added")

                # Set existing notifications as sent
                print("📝 Marking existing notifications as sent...")
                await conn.execute(text("""
                    UPDATE notifications SET is_sent = true;
                """))
                print("   ✅ Existing notifications marked as sent")
            else:
                print("   ℹ️  is_sent already exists")

            # 6. Add sent_at column
            if 'sent_at' not in existing_columns:
                print("📝 Adding sent_at column...")
                await conn.execute(text("""
                    ALTER TABLE notifications 
                    ADD COLUMN sent_at TIMESTAMP WITH TIME ZONE;
                """))
                print("   ✅ sent_at column added")

                # Set sent_at to created_at for existing notifications
                print("📝 Setting sent_at for existing notifications...")
                await conn.execute(text("""
                    UPDATE notifications SET sent_at = created_at WHERE is_sent = true;
                """))
                print("   ✅ sent_at timestamps set")
            else:
                print("   ℹ️  sent_at already exists")

            # 7. Add send_attempts column
            if 'send_attempts' not in existing_columns:
                print("📝 Adding send_attempts column...")
                await conn.execute(text("""
                    ALTER TABLE notifications 
                    ADD COLUMN send_attempts INTEGER DEFAULT 0;
                """))
                print("   ✅ send_attempts column added")
            else:
                print("   ℹ️  send_attempts already exists")

            # 8. Add last_error column
            if 'last_error' not in existing_columns:
                print("📝 Adding last_error column...")
                await conn.execute(text("""
                    ALTER TABLE notifications 
                    ADD COLUMN last_error TEXT;
                """))
                print("   ✅ last_error column added")
            else:
                print("   ℹ️  last_error already exists")

            # 9. Create index for unsent notifications
            print("📝 Creating index for pending notifications...")
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_notifications_status 
                ON notifications(status) 
                WHERE status = 'pending';
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


async def verify_columns():
    """Verify that columns were added"""
    print()
    print("🔍 Verifying columns...")
    print()

    async with engine.begin() as conn:
        try:
            result = await conn.execute(text("""
                SELECT column_name, data_type, is_nullable
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
                    print(f"{col[0]:<20} {col[1]:<30} {col[2]}")
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
    print(" KU RUN - Add Sent Notification Tracking Migration")
    print("=" * 70)
    print()
    print("📋 This script will:")
    print("   1. Create notification channel enum (in_app, email, push, sms)")
    print("   2. Create notification status enum (pending, sent, failed, read)")
    print("   3. Add 'channel' column - which channel to use")
    print("   4. Add 'status' column - current delivery status")
    print("   5. Add 'is_sent' column - boolean flag for sent")
    print("   6. Add 'sent_at' column - timestamp when sent")
    print("   7. Add 'send_attempts' column - retry counter")
    print("   8. Add 'last_error' column - error message if failed")
    print("   9. Create index for pending notifications")
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
        success = await migrate_notification_sent()

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
        print("   1. Update notification model in src/models/notification.py")
        print("   2. Update notification schemas")
        print("   3. Update notification CRUD functions")
        print("   4. Create notification service for sending")
        print("   5. Restart your FastAPI server")
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