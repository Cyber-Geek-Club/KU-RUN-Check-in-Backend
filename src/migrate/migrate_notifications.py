"""
Database Migration Script: Create Notifications Table
Run this file: python migrate_notifications.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from src.database.db_config import engine


async def migrate_notifications():
    """Create notifications table"""
    print("🔄 Starting migration: Create notifications table...")
    print()

    async with engine.begin() as conn:
        try:
            # Create notifications table
            print("📝 Creating notifications table...")
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    type VARCHAR(50) NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    message TEXT NOT NULL,
                    event_id INTEGER REFERENCES events(id) ON DELETE CASCADE,
                    participation_id INTEGER REFERENCES event_participations(id) ON DELETE CASCADE,
                    reward_id INTEGER REFERENCES rewards(id) ON DELETE SET NULL,
                    is_read BOOLEAN DEFAULT FALSE,
                    read_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """))
            print("   ✅ Table created")
            print()

            # Create indexes
            print("📝 Creating indexes...")
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
                CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(is_read);
                CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at);
                CREATE INDEX IF NOT EXISTS idx_notifications_user_unread ON notifications(user_id, is_read) 
                WHERE is_read = FALSE;
            """))
            print("   ✅ Indexes created")
            print()

            # Add notifications relationship to users table
            print("📝 Verifying user relationship...")
            result = await conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'id';
            """))
            if result.fetchone():
                print("   ✅ User table verified")
            print()

            print("🎉 Migration completed successfully!")

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            raise


async def verify_table():
    """Verify notifications table exists"""
    print("🔍 Verifying notifications table...")
    print()

    async with engine.begin() as conn:
        try:
            result = await conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'notifications'
                ORDER BY ordinal_position;
            """))

            columns = result.fetchall()
            if columns:
                print("📊 Table Structure:")
                for col in columns:
                    print(f"   - {col[0]}: {col[1]}")
                print()
                print("✅ Table verified successfully!")
                return True
            else:
                print("❌ Table not found")
                return False

        except Exception as e:
            print(f"❌ Verification failed: {e}")
            return False


async def main():
    """Main migration function"""
    print("=" * 70)
    print(" KU RUN - Notification System Migration")
    print("=" * 70)
    print()

    try:
        await migrate_notifications()
        await verify_table()

        print()
        print("=" * 70)
        print("✨ Setup Complete!")
        print("=" * 70)
        print()
        print("💡 Next steps:")
        print("   1. Update src/models/__init__.py")
        print("   2. Create notification CRUD file")
        print("   3. Create notification schemas")
        print("   4. Create notification endpoints")
        print("   5. Restart your server")
        print()

    except Exception as e:
        print()
        print("=" * 70)
        print("❌ Migration failed!")
        print("=" * 70)
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())