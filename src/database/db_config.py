from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError, ProgrammingError
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        # Import all models to ensure they're registered
        from src.models import (
            Base, User, Event, EventParticipation, EventHoliday,
            Reward, UserReward, PasswordResetLog, UploadedImage
        )
        try:
            await conn.run_sync(Base.metadata.create_all)
        except (IntegrityError, ProgrammingError) as e:
            # Ignore errors when ENUM types or tables already exist
            # This can happen with multiple workers starting simultaneously
            if "already exists" in str(e):
                pass
            else:
                raise

