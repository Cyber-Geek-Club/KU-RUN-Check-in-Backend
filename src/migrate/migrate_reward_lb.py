"""
Database Migration: Create Reward Leaderboard System
Run: python src/migrate/migrate_reward_leaderboard.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from src.database.db_config import engine


async def migrate_reward_leaderboard():
    """Create reward leaderboard configuration and entry tables"""
    print("🔄 Creating Reward Leaderboard System...")
    print()

    async with engine.begin() as conn:
        try:
            # ===== 1. Create leaderboard_configs table =====
            print("📝 Step 1: Creating reward_leaderboard_configs table...")
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS reward_leaderboard_configs (
                    id SERIAL PRIMARY KEY,
                    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
                    
                    -- Basic info
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    
                    -- Requirements
                    required_completions INTEGER DEFAULT 30 NOT NULL,
                    max_reward_recipients INTEGER DEFAULT 200 NOT NULL,
                    
                    -- Reward tiers (JSON format)
                    reward_tiers JSONB NOT NULL DEFAULT '[]'::jsonb,
                    
                    -- Status and timeline
                    is_active BOOLEAN DEFAULT TRUE NOT NULL,
                    starts_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    ends_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    finalized_at TIMESTAMP WITH TIME ZONE,
                    
                    -- Metadata
                    created_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    
                    CONSTRAINT unique_event_leaderboard UNIQUE(event_id)
                );
            """))
            print("   ✅ reward_leaderboard_configs created")
            print()

            # ===== 2. Create leaderboard_entries table =====
            print("📝 Step 2: Creating reward_leaderboard_entries table...")
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS reward_leaderboard_entries (
                    id SERIAL PRIMARY KEY,
                    config_id INTEGER NOT NULL REFERENCES reward_leaderboard_configs(id) ON DELETE CASCADE,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    
                    -- Completion tracking
                    total_completions INTEGER DEFAULT 0 NOT NULL,
                    completed_event_participations JSONB NOT NULL DEFAULT '[]'::jsonb,
                    
                    -- Ranking
                    rank INTEGER,
                    qualified_at TIMESTAMP WITH TIME ZONE,
                    
                    -- Reward
                    reward_id INTEGER REFERENCES rewards(id) ON DELETE SET NULL,
                    reward_tier INTEGER,
                    rewarded_at TIMESTAMP WITH TIME ZONE,
                    
                    -- Metadata
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    
                    CONSTRAINT unique_user_per_config UNIQUE(config_id, user_id)
                );
            """))
            print("   ✅ reward_leaderboard_entries created")
            print()

            # ===== 3. Create indexes =====
            print("📝 Step 3: Creating indexes...")
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_lb_config_event ON reward_leaderboard_configs(event_id);
                CREATE INDEX IF NOT EXISTS idx_lb_config_active ON reward_leaderboard_configs(is_active);
                CREATE INDEX IF NOT EXISTS idx_lb_config_dates ON reward_leaderboard_configs(starts_at, ends_at);
                
                CREATE INDEX IF NOT EXISTS idx_lb_entry_config ON reward_leaderboard_entries(config_id);
                CREATE INDEX IF NOT EXISTS idx_lb_entry_user ON reward_leaderboard_entries(user_id);
                CREATE INDEX IF NOT EXISTS idx_lb_entry_rank ON reward_leaderboard_entries(rank) WHERE rank IS NOT NULL;
                CREATE INDEX IF NOT EXISTS idx_lb_entry_qualified ON reward_leaderboard_entries(qualified_at) WHERE qualified_at IS NOT NULL;
            """))
            print("   ✅ Indexes created")
            print()

            print("🎉 Migration completed successfully!")
            return True

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            return False


async def verify_tables():
    """Verify tables were created"""
    print()
    print("🔍 Verifying tables...")
    print()

    async with engine.begin() as conn:
        try:
            # Check both tables
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name IN ('reward_leaderboard_configs', 'reward_leaderboard_entries')
                ORDER BY table_name;
            """))
            
            tables = [row[0] for row in result.fetchall()]
            
            if len(tables) == 2:
                print("📊 Tables Created:")
                for table in tables:
                    print(f"   ✅ {table}")
                print()
                print("✅ Verification successful!")
                return True
            else:
                print("❌ Some tables missing")
                return False

        except Exception as e:
            print(f"❌ Verification failed: {e}")
            return False


async def show_summary():
    """Show migration summary"""
    print("=" * 70)
    print(" KU RUN - Reward Leaderboard System Migration")
    print("=" * 70)
    print()
    print("📋 This script will create:")
    print("   1. reward_leaderboard_configs - Configure leaderboard for events")
    print("   2. reward_leaderboard_entries - Track user progress and rankings")
    print()
    print("💡 Features:")
    print("   - Dynamic reward tiers (unlimited)")
    print("   - Configurable required completions (e.g., 30 runs)")
    print("   - Max reward recipients limit (e.g., 200 people)")
    print("   - Automatic ranking based on completion time")
    print("   - JSON-based flexible reward structure")
    print()

    try:
        response = input("Continue? (yes/no): ").lower().strip()
        if response not in ['yes', 'y']:
            print()
            print("❌ Migration cancelled")
            return False
    except KeyboardInterrupt:
        print()
        print()
        print("❌ Migration cancelled")
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
        success = await migrate_reward_leaderboard()

        if success:
            await verify_tables()

        print()
        print("=" * 70)
        if success:
            print("✨ Migration completed!")
        else:
            print("⚠️  Migration failed")
        print("=" * 70)
        print()
        print("💡 Next steps:")
        print("   1. Update models (reward_lb.py already created)")
        print("   2. Create schemas (reward_leaderboard_schema.py)")
        print("   3. Create CRUD operations")
        print("   4. Create API endpoints")
        print("   5. Restart server")
        print()

    except KeyboardInterrupt:
        print()
        print()
        print("❌ Migration interrupted")
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
