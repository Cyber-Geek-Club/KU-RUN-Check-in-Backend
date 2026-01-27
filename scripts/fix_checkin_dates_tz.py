
import asyncio
import sys
import os
from datetime import datetime
import pytz
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.append(os.getcwd())

from src.database.db_config import DATABASE_URL
from src.models.base import Base
from src.models.event_participation import EventParticipation, ParticipationStatus
from src.models.event import Event

# Configure DB
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

BANGKOK_TZ = pytz.timezone('Asia/Bangkok')

async def fix_checkin_dates():
    print("🚀 Starting Data Migration: Fix Check-in Dates (Timezone Mismatch)")
    
    async with AsyncSessionLocal() as db:
        try:
            # 1. Get all participations with checkin_date
            result = await db.execute(
                select(EventParticipation)
                .where(EventParticipation.checkin_date.isnot(None))
            )
            participations = result.scalars().all()
            
            print(f"📊 Found {len(participations)} participations to check.")
            
            fix_count = 0
            
            for p in participations:
                if not p.joined_at:
                    continue
                    
                # Calculate correct BKK date from joined_at
                joined_at_bkk = p.joined_at.astimezone(BANGKOK_TZ)
                correct_date = joined_at_bkk.date()
                
                # Check mismatch
                if p.checkin_date != correct_date:
                    print(f"   ⚠️ ID {p.id} (User {p.user_id}): stored {p.checkin_date} != real {correct_date} (Joined {joined_at_bkk})")
                    p.checkin_date = correct_date
                    fix_count += 1
            
            if fix_count > 0:
                print(f"✅ Fixing {fix_count} records...")
                await db.commit()
                print("✅ Migration completed successfully.")
            else:
                print("✨ No issues found. All dates are correct.")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            await db.rollback()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(fix_checkin_dates())
