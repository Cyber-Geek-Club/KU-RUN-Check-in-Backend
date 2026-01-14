# src/migrate/migrate_uploaded_images.py
"""
Migration script สำหรับสร้างตาราง uploaded_images
เพื่อเก็บข้อมูลรูปภาพที่อัพโหลดทั้งหมดในฐานข้อมูล
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text
from src.database.db_config import engine


async def migrate():
    """สร้างตาราง uploaded_images"""
    
    async with engine.begin() as conn:
        # Check if table exists
        result = await conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'uploaded_images'
            );
        """))
        exists = result.scalar()
        
        if exists:
            print("✅ Table 'uploaded_images' already exists")
            return
        
        # Create table
        await conn.execute(text("""
            CREATE TABLE uploaded_images (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(255) NOT NULL,
                original_filename VARCHAR(255),
                file_path TEXT NOT NULL UNIQUE,
                file_size BIGINT,
                mime_type VARCHAR(100),
                category VARCHAR(50) NOT NULL,
                image_hash VARCHAR(64),
                uploaded_by INTEGER REFERENCES users(id),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """))
        print("✅ Created table 'uploaded_images'")
        
        # Create indexes
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_uploaded_images_category 
            ON uploaded_images(category);
        """))
        print("✅ Created index on 'category'")
        
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_uploaded_images_image_hash 
            ON uploaded_images(image_hash);
        """))
        print("✅ Created index on 'image_hash'")
        
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_uploaded_images_uploaded_by 
            ON uploaded_images(uploaded_by);
        """))
        print("✅ Created index on 'uploaded_by'")
        
        print("\n🎉 Migration completed successfully!")


async def rollback():
    """ลบตาราง uploaded_images (ใช้ตอน rollback)"""
    
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS uploaded_images CASCADE;"))
        print("✅ Dropped table 'uploaded_images'")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        asyncio.run(rollback())
    else:
        asyncio.run(migrate())
