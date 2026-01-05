"""
Database Migration Script: Add CASCADE DELETE to polymorphic user tables
Save this file as: src/migrate_polymorphic_cascade.py
Run: python src/migrate_polymorphic_cascade.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from src.database.db_config import engine


async def migrate_polymorphic_cascade():
    """
    Add CASCADE DELETE to all polymorphic user tables
    (students, officers, staffs, organizers)
    """
    print("🔄 Starting migration: Add CASCADE DELETE for polymorphic tables...")
    print()

    async with engine.begin() as conn:
        try:
            # ===== 1. students table =====
            print("📝 Step 1: Updating students.id foreign key...")

            # Check if table exists
            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'students'
                );
            """))

            if result.scalar():
                # Drop old constraint
                await conn.execute(text("""
                    ALTER TABLE students 
                    DROP CONSTRAINT IF EXISTS students_id_fkey;
                """))
                print("   ✅ Old constraint dropped")

                # Add new constraint with CASCADE
                await conn.execute(text("""
                    ALTER TABLE students 
                    ADD CONSTRAINT students_id_fkey 
                    FOREIGN KEY (id) 
                    REFERENCES users(id) 
                    ON DELETE CASCADE;
                """))
                print("   ✅ New constraint added with CASCADE DELETE")
            else:
                print("   ℹ️  Table 'students' doesn't exist, skipping...")
            print()

            # ===== 2. officers table =====
            print("📝 Step 2: Updating officers.id foreign key...")

            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'officers'
                );
            """))

            if result.scalar():
                await conn.execute(text("""
                    ALTER TABLE officers 
                    DROP CONSTRAINT IF EXISTS officers_id_fkey;
                """))
                print("   ✅ Old constraint dropped")

                await conn.execute(text("""
                    ALTER TABLE officers 
                    ADD CONSTRAINT officers_id_fkey 
                    FOREIGN KEY (id) 
                    REFERENCES users(id) 
                    ON DELETE CASCADE;
                """))
                print("   ✅ New constraint added with CASCADE DELETE")
            else:
                print("   ℹ️  Table 'officers' doesn't exist, skipping...")
            print()

            # ===== 3. staffs table =====
            print("📝 Step 3: Updating staffs.id foreign key...")

            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'staffs'
                );
            """))

            if result.scalar():
                await conn.execute(text("""
                    ALTER TABLE staffs 
                    DROP CONSTRAINT IF EXISTS staffs_id_fkey;
                """))
                print("   ✅ Old constraint dropped")

                await conn.execute(text("""
                    ALTER TABLE staffs 
                    ADD CONSTRAINT staffs_id_fkey 
                    FOREIGN KEY (id) 
                    REFERENCES users(id) 
                    ON DELETE CASCADE;
                """))
                print("   ✅ New constraint added with CASCADE DELETE")
            else:
                print("   ℹ️  Table 'staffs' doesn't exist, skipping...")
            print()

            # ===== 4. organizers table =====
            print("📝 Step 4: Updating organizers.id foreign key...")

            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'organizers'
                );
            """))

            if result.scalar():
                await conn.execute(text("""
                    ALTER TABLE organizers 
                    DROP CONSTRAINT IF EXISTS organizers_id_fkey;
                """))
                print("   ✅ Old constraint dropped")

                await conn.execute(text("""
                    ALTER TABLE organizers 
                    ADD CONSTRAINT organizers_id_fkey 
                    FOREIGN KEY (id) 
                    REFERENCES users(id) 
                    ON DELETE CASCADE;
                """))
                print("   ✅ New constraint added with CASCADE DELETE")
            else:
                print("   ℹ️  Table 'organizers' doesn't exist, skipping...")
            print()

            print("🎉 Migration completed successfully!")
            return True

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            return False


async def verify_constraints():
    """Verify all polymorphic table constraints"""
    print()
    print("🔍 Verifying polymorphic table constraints...")
    print()

    async with engine.begin() as conn:
        try:
            # Check all inheritance tables
            tables = ['students', 'officers', 'staffs', 'organizers']

            print("📊 Polymorphic Table Constraints:")
            print()
            print(f"{'Table':<20} {'Delete Rule':<15} {'Status'}")
            print("-" * 50)

            for table_name in tables:
                # Check if table exists
                result = await conn.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = '{table_name}'
                    );
                """))

                if not result.scalar():
                    print(f"{table_name:<20} {'N/A':<15} ⚠️  Table doesn't exist")
                    continue

                # Get delete rule
                result = await conn.execute(text(f"""
                    SELECT rc.delete_rule
                    FROM information_schema.table_constraints AS tc
                    JOIN information_schema.referential_constraints AS rc
                        ON rc.constraint_name = tc.constraint_name
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                        AND tc.table_name = '{table_name}'
                        AND tc.constraint_name LIKE '%_id_fkey';
                """))

                row = result.fetchone()
                if row:
                    delete_rule = row[0]
                    if delete_rule == 'CASCADE':
                        status = "✅ Correct"
                    else:
                        status = f"⚠️  {delete_rule}"
                    print(f"{table_name:<20} {delete_rule:<15} {status}")
                else:
                    print(f"{table_name:<20} {'UNKNOWN':<15} ❌ No constraint found")

            print()
            print("✅ Verification complete!")
            return True

        except Exception as e:
            print(f"❌ Verification failed: {e}")
            return False


async def show_summary():
    """Show summary of what will happen"""
    print("=" * 70)
    print(" KU RUN - Polymorphic Tables CASCADE DELETE Migration")
    print("=" * 70)
    print()
    print("📋 This script will update CASCADE DELETE for inheritance tables:")
    print()
    print("   Tables to update:")
    print("   - students.id → users(id)")
    print("   - officers.id → users(id)")
    print("   - staffs.id → users(id)")
    print("   - organizers.id → users(id)")
    print()
    print("   Effect: When a user is deleted from 'users' table,")
    print("   the corresponding record in the inheritance table")
    print("   will also be deleted automatically.")
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
        success = await migrate_polymorphic_cascade()

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
        print("   2. Try deleting a user of any role:")
        print("      - DELETE /api/users/{user_id}")
        print("   3. The user and their role-specific data will be deleted")
        print()
        print("📝 Example:")
        print("   Delete Officer (id=27):")
        print("   - Record in 'users' table → DELETED")
        print("   - Record in 'officers' table → DELETED (CASCADE)")
        print("   - Participations → DELETED (CASCADE)")
        print("   - Notifications → DELETED (CASCADE)")
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