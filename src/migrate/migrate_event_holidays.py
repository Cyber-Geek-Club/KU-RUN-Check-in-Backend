# src/migrate/migrate_event_holidays.py
"""
Migration script สำหรับสร้างตาราง event_holidays
เพื่อเก็บข้อมูลวันหยุดของกิจกรรมหลายวัน
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text
from src.database.db_config import engine


async def migrate():
    """สร้างตาราง event_holidays"""
    
    async with engine.begin() as conn:
        # Check if table exists
        result = await conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'event_holidays'
            );
        """))
        exists = result.scalar()
        
        if exists:
            print("✅ Table 'event_holidays' already exists")
            return
        
        # Create table
        await conn.execute(text("""
            CREATE TABLE event_holidays (
                id SERIAL PRIMARY KEY,
                event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
                holiday_date DATE NOT NULL,
                holiday_name VARCHAR(255),
                description TEXT,
                created_by INTEGER REFERENCES users(id),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                
                -- Unique constraint: ห้ามมีวันหยุดซ้ำกันในกิจกรรมเดียวกัน
                UNIQUE(event_id, holiday_date)
            );
        """))
        print("✅ Created table 'event_holidays'")
        
        # Create indexes
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_event_holidays_event_id 
            ON event_holidays(event_id);
        """))
        print("✅ Created index on 'event_id'")
        
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_event_holidays_holiday_date 
            ON event_holidays(holiday_date);
        """))
        print("✅ Created index on 'holiday_date'")
        
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_event_holidays_event_date 
            ON event_holidays(event_id, holiday_date);
        """))
        print("✅ Created composite index on 'event_id, holiday_date'")
        
        print("\n🎉 Migration completed successfully!")
        print("📝 Use case: กิจกรรมหลายวันที่มีวันหยุดระหว่างกิจกรรม")
        print("   - ตัวอย่าง: กิจกรรม 30 วัน แต่หยุดทุกวันเสาร์-อาทิตย์")
        print("   - ตัวอย่าง: กิจกรรมมกราคม-มีนาคม แต่หยุดช่วงสงกรานต์")


async def rollback():
    """ลบตาราง event_holidays (ใช้ตอน rollback)"""
    
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS event_holidays CASCADE;"))
        print("✅ Dropped table 'event_holidays'")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        asyncio.run(rollback())
    else:
        asyncio.run(migrate())
