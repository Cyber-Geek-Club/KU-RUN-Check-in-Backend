"""
Database Migration: Add Participant Snapshots Tables
Run: python -m src.migrate.migrate_participant_snapshots
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from src.database.db_config import engine


async def migrate_participant_snapshots():
    print("=" * 70)
    print(" KU RUN - Add Participant Snapshots Tables")
    print("=" * 70)
    print()

    async with engine.connect() as conn:
        trans = await conn.begin()
        try:
            # ===== 1. สร้างตาราง participant_snapshots =====
            print("📝 Step 1: Creating participant_snapshots table...")
            
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS participant_snapshots (
                    id SERIAL PRIMARY KEY,
                    snapshot_id VARCHAR(36) UNIQUE NOT NULL,
                    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
                    snapshot_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    entry_count INTEGER DEFAULT 0,
                    created_by INTEGER REFERENCES users(id),
                    description VARCHAR(500),
                    
                    CONSTRAINT fk_snapshot_event FOREIGN KEY (event_id) 
                        REFERENCES events(id) ON DELETE CASCADE,
                    CONSTRAINT fk_snapshot_creator FOREIGN KEY (created_by) 
                        REFERENCES users(id) ON DELETE SET NULL
                );
            """))
            
            # สร้าง indexes
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_participant_snapshots_snapshot_id 
                ON participant_snapshots(snapshot_id);
            """))
            
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_participant_snapshots_event_id 
                ON participant_snapshots(event_id);
            """))
            
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_participant_snapshots_snapshot_time 
                ON participant_snapshots(snapshot_time DESC);
            """))
            
            print("   ✅ participant_snapshots table created")
            
            # ===== 2. สร้างตาราง participant_snapshot_entries =====
            print("📝 Step 2: Creating participant_snapshot_entries table...")
            
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS participant_snapshot_entries (
                    id SERIAL PRIMARY KEY,
                    entry_id VARCHAR(36) UNIQUE NOT NULL,
                    snapshot_id INTEGER NOT NULL REFERENCES participant_snapshots(id) ON DELETE CASCADE,
                    participation_id INTEGER,
                    user_id INTEGER NOT NULL,
                    user_name VARCHAR(255) NOT NULL,
                    user_email VARCHAR(255),
                    action VARCHAR(50) NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    joined_at TIMESTAMP WITH TIME ZONE,
                    checked_in_at TIMESTAMP WITH TIME ZONE,
                    completed_at TIMESTAMP WITH TIME ZONE,
                    metadata JSONB,
                    
                    CONSTRAINT fk_entry_snapshot FOREIGN KEY (snapshot_id) 
                        REFERENCES participant_snapshots(id) ON DELETE CASCADE
                );
            """))
            
            # สร้าง indexes
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_participant_snapshot_entries_entry_id 
                ON participant_snapshot_entries(entry_id);
            """))
            
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_participant_snapshot_entries_snapshot_id 
                ON participant_snapshot_entries(snapshot_id);
            """))
            
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_participant_snapshot_entries_user_id 
                ON participant_snapshot_entries(user_id);
            """))
            
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_participant_snapshot_entries_created_at 
                ON participant_snapshot_entries(created_at DESC);
            """))
            
            print("   ✅ participant_snapshot_entries table created")
            
            # ===== 3. Commit =====
            await trans.commit()
            print()
            print("=" * 70)
            print("✅ Migration completed successfully!")
            print("=" * 70)
            return True
            
        except Exception as e:
            await trans.rollback()
            print()
            print("=" * 70)
            print(f"❌ Migration failed: {str(e)}")
            print("=" * 70)
            return False


async def verify_migration():
    print()
    print("🔍 Verifying migration...")
    async with engine.connect() as conn:
        try:
            # ตรวจสอบ tables
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name IN ('participant_snapshots', 'participant_snapshot_entries')
                ORDER BY table_name;
            """))
            tables = result.fetchall()
            
            print(f"   📊 Tables found: {[t[0] for t in tables]}")
            
            # ตรวจสอบ columns ของ participant_snapshots
            result = await conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'participant_snapshots'
                ORDER BY ordinal_position;
            """))
            columns = result.fetchall()
            print(f"   📋 participant_snapshots columns: {len(columns)}")
            
            # ตรวจสอบ columns ของ participant_snapshot_entries
            result = await conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'participant_snapshot_entries'
                ORDER BY ordinal_position;
            """))
            columns = result.fetchall()
            print(f"   📋 participant_snapshot_entries columns: {len(columns)}")
            
            print("✅ Verification finished!")
            return True
        except Exception as e:
            print(f"❌ Verification failed: {e}")
            return False


async def main():
    print()
    try:
        if await migrate_participant_snapshots():
            await verify_migration()
    except KeyboardInterrupt:
        print("\n❌ Migration cancelled")


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
