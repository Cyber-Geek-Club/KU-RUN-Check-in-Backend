"""
Migration Script: Fix Image URLs to Relative Paths
===================================================
แก้ไข URL รูปภาพในฐานข้อมูลจาก full URL (http://...) เป็น relative path (/api/uploads/...)

ปัญหา: URL รูปภาพเก่าถูกเก็บเป็น http://158.108.102.14:8001/api/uploads/...
แก้ไข: แปลงเป็น /api/uploads/... เพื่อหลีกเลี่ยง Mixed Content error

วิธีรัน:
    python -m src.migrate.migrate_fix_image_urls
"""

import asyncio
import re
from sqlalchemy import text
from src.database.db_config import engine


async def migrate_image_urls():
    """แก้ไข URL รูปภาพให้เป็น relative path"""
    
    print("=" * 60)
    print("🔧 Migration: Fix Image URLs to Relative Paths")
    print("=" * 60)
    
    async with engine.begin() as conn:
        try:
            # Pattern สำหรับจับ http:// หรือ https:// URL
            # เปลี่ยนจาก http://158.108.102.14:8001/api/uploads/... 
            # เป็น /api/uploads/...
            
            # ======================================================
            # 1. Fix events.banner_image_url
            # ======================================================
            print("\n📝 Step 1: Fixing events.banner_image_url...")
            
            # ดูข้อมูลก่อน update
            result = await conn.execute(text("""
                SELECT id, banner_image_url 
                FROM events 
                WHERE banner_image_url LIKE 'http%'
                LIMIT 5
            """))
            rows = result.fetchall()
            
            if rows:
                print(f"   Found {len(rows)} events with full URL (showing first 5):")
                for row in rows:
                    print(f"   - Event {row[0]}: {row[1][:80]}...")
                
                # Update - ใช้ regexp_replace สำหรับ PostgreSQL
                await conn.execute(text("""
                    UPDATE events 
                    SET banner_image_url = regexp_replace(
                        banner_image_url, 
                        '^https?://[^/]+', 
                        ''
                    )
                    WHERE banner_image_url ~ '^https?://'
                """))
                print("   ✅ events.banner_image_url updated")
            else:
                print("   ℹ️  No events with full URL found")
            
            # ======================================================
            # 2. Fix event_participations.proof_image_url
            # ======================================================
            print("\n📝 Step 2: Fixing event_participations.proof_image_url...")
            
            result = await conn.execute(text("""
                SELECT COUNT(*) 
                FROM event_participations 
                WHERE proof_image_url ~ '^https?://'
            """))
            count = result.scalar()
            
            if count > 0:
                print(f"   Found {count} participations with full URL")
                
                await conn.execute(text("""
                    UPDATE event_participations 
                    SET proof_image_url = regexp_replace(
                        proof_image_url, 
                        '^https?://[^/]+', 
                        ''
                    )
                    WHERE proof_image_url ~ '^https?://'
                """))
                print("   ✅ event_participations.proof_image_url updated")
            else:
                print("   ℹ️  No participations with full URL found")
            
            # ======================================================
            # 3. Fix rewards.badge_image_url
            # ======================================================
            print("\n📝 Step 3: Fixing rewards.badge_image_url...")
            
            result = await conn.execute(text("""
                SELECT COUNT(*) 
                FROM rewards 
                WHERE badge_image_url ~ '^https?://'
            """))
            count = result.scalar()
            
            if count > 0:
                print(f"   Found {count} rewards with full URL")
                
                await conn.execute(text("""
                    UPDATE rewards 
                    SET badge_image_url = regexp_replace(
                        badge_image_url, 
                        '^https?://[^/]+', 
                        ''
                    )
                    WHERE badge_image_url ~ '^https?://'
                """))
                print("   ✅ rewards.badge_image_url updated")
            else:
                print("   ℹ️  No rewards with full URL found")
            
            # ======================================================
            # 4. Fix uploaded_images.file_path (ถ้ามี)
            # ======================================================
            print("\n📝 Step 4: Fixing uploaded_images.file_path...")
            
            try:
                result = await conn.execute(text("""
                    SELECT COUNT(*) 
                    FROM uploaded_images 
                    WHERE file_path ~ '^https?://'
                """))
                count = result.scalar()
                
                if count > 0:
                    print(f"   Found {count} uploaded_images with full URL")
                    
                    await conn.execute(text("""
                        UPDATE uploaded_images 
                        SET file_path = regexp_replace(
                            file_path, 
                            '^https?://[^/]+', 
                            ''
                        )
                        WHERE file_path ~ '^https?://'
                    """))
                    print("   ✅ uploaded_images.file_path updated")
                else:
                    print("   ℹ️  No uploaded_images with full URL found")
            except Exception as e:
                print(f"   ⚠️  uploaded_images table might not exist: {e}")
            
            # ======================================================
            # Verification
            # ======================================================
            print("\n" + "=" * 60)
            print("✅ Migration completed! Verifying results...")
            print("=" * 60)
            
            # ตรวจสอบผลลัพธ์
            result = await conn.execute(text("""
                SELECT 'events' as table_name, COUNT(*) as count
                FROM events 
                WHERE banner_image_url ~ '^https?://'
                UNION ALL
                SELECT 'event_participations', COUNT(*)
                FROM event_participations 
                WHERE proof_image_url ~ '^https?://'
                UNION ALL
                SELECT 'rewards', COUNT(*)
                FROM rewards 
                WHERE badge_image_url ~ '^https?://'
            """))
            
            remaining = result.fetchall()
            all_clean = True
            
            for table_name, count in remaining:
                if count > 0:
                    print(f"   ⚠️  {table_name}: still has {count} full URLs")
                    all_clean = False
                else:
                    print(f"   ✅ {table_name}: all URLs are relative")
            
            if all_clean:
                print("\n🎉 All image URLs have been converted to relative paths!")
            else:
                print("\n⚠️  Some URLs might need manual review")
            
            # แสดงตัวอย่างผลลัพธ์
            print("\n📋 Sample results after migration:")
            result = await conn.execute(text("""
                SELECT id, banner_image_url 
                FROM events 
                WHERE banner_image_url IS NOT NULL 
                AND banner_image_url != ''
                LIMIT 3
            """))
            rows = result.fetchall()
            for row in rows:
                print(f"   Event {row[0]}: {row[1]}")
                
        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            raise


async def dry_run():
    """แสดงข้อมูลที่จะถูก update โดยไม่ทำการ update จริง"""
    
    print("=" * 60)
    print("🔍 DRY RUN: Preview Image URLs to be Fixed")
    print("=" * 60)
    
    async with engine.connect() as conn:
        # Events
        result = await conn.execute(text("""
            SELECT id, banner_image_url 
            FROM events 
            WHERE banner_image_url ~ '^https?://'
        """))
        rows = result.fetchall()
        print(f"\n📌 events.banner_image_url: {len(rows)} rows to update")
        for row in rows[:5]:
            old_url = row[1]
            new_url = re.sub(r'^https?://[^/]+', '', old_url)
            print(f"   Event {row[0]}:")
            print(f"     Before: {old_url}")
            print(f"     After:  {new_url}")
        
        # Participations
        result = await conn.execute(text("""
            SELECT id, proof_image_url 
            FROM event_participations 
            WHERE proof_image_url ~ '^https?://'
            LIMIT 5
        """))
        rows = result.fetchall()
        count_result = await conn.execute(text("""
            SELECT COUNT(*) FROM event_participations 
            WHERE proof_image_url ~ '^https?://'
        """))
        total = count_result.scalar()
        print(f"\n📌 event_participations.proof_image_url: {total} rows to update")
        for row in rows:
            old_url = row[1]
            new_url = re.sub(r'^https?://[^/]+', '', old_url)
            print(f"   Participation {row[0]}:")
            print(f"     Before: {old_url}")
            print(f"     After:  {new_url}")
        
        # Rewards
        result = await conn.execute(text("""
            SELECT id, badge_image_url 
            FROM rewards 
            WHERE badge_image_url ~ '^https?://'
        """))
        rows = result.fetchall()
        print(f"\n📌 rewards.badge_image_url: {len(rows)} rows to update")
        for row in rows:
            old_url = row[1]
            new_url = re.sub(r'^https?://[^/]+', '', old_url)
            print(f"   Reward {row[0]}:")
            print(f"     Before: {old_url}")
            print(f"     After:  {new_url}")


if __name__ == "__main__":
    import sys
    
    print("\n🚀 Image URL Migration Tool")
    print("-" * 40)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--dry-run":
        print("Running in DRY RUN mode (no changes will be made)\n")
        asyncio.run(dry_run())
    else:
        print("Running MIGRATION (changes will be committed)\n")
        print("⚠️  To preview changes first, run with --dry-run flag")
        print("-" * 40)
        asyncio.run(migrate_image_urls())
