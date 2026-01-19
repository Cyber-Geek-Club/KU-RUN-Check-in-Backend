"""
Clear Test Database
ล้างข้อมูลทั้งหมดในฐานข้อมูล Test

Usage:
    python clear_test_db.py
"""

import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

load_dotenv()

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")


async def clear_test_database():
    """ล้างข้อมูลทั้งหมดในฐานข้อมูล Test"""
    
    # Safety check
    if "test" not in TEST_DATABASE_URL.lower() and "kurun_test" not in TEST_DATABASE_URL.lower():
        print("❌ ERROR: DATABASE_URL ไม่ใช่ test database!")
        print(f"   Current URL: {TEST_DATABASE_URL}")
        print("   ต้องมีคำว่า 'test' หรือ 'kurun_test' ใน URL")
        return
    
    print("🧹 กำลังล้างข้อมูล Test Database...")
    print(f"   URL: {TEST_DATABASE_URL}")
    
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        # Disable foreign key checks
        await conn.execute(text("SET session_replication_role = 'replica';"))
        
        # Get all table names
        result = await conn.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        ))
        tables = [row[0] for row in result]
        
        print(f"   พบ {len(tables)} ตาราง")
        
        # Truncate all tables
        for table in tables:
            try:
                await conn.execute(text(f'TRUNCATE TABLE "{table}" CASCADE'))
                print(f"   ✓ ล้าง {table}")
            except Exception as e:
                print(f"   ⚠ ข้าม {table}: {e}")
        
        # Re-enable foreign key checks
        await conn.execute(text("SET session_replication_role = 'origin';"))
    
    await engine.dispose()
    
    print("✅ ล้างข้อมูล Test Database สำเร็จ!")
    print("   สามารถรัน pytest ได้เลย")


if __name__ == "__main__":
    asyncio.run(clear_test_database())
