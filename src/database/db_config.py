from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
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
            Base, User, Event, EventParticipation, 
            Reward, UserReward, PasswordResetLog, UploadedImage
        )
        await conn.run_sync(Base.metadata.create_all)

