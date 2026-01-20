from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
from src.database.db_config import init_db
from fastapi.staticfiles import StaticFiles
from src.api.endpoints import (
    events, 
    participations, 
    rewards, 
    users, 
    images, 
    notifications,
    event_holidays,
    reward_lb_endpoints,
    strava,
    participant_snapshots
)
from src.services.scheduler_service import start_scheduler, shutdown_scheduler
from fastapi.middleware.gzip import GZipMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="KU RUN Check-in API",
    description="API for KU Running Event Check-in System",
    version="1.0.0"
)

# 🔧 IMPROVED CORS Configuration
# Read allowed origins from environment
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()]

print(f"[OK] Allowed CORS origins: {allowed_origins}")  # Debug log

app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=5)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ✅ Specific origins instead of ["*"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # 🆕 Add this
)

# Initialize database connection
@app.on_event("startup")
async def on_startup():
    logger.info("[OK] Starting KU RUN Check-in API...")
    await init_db()
    logger.info("[OK] Database initialized")
    
    # Start scheduler for auto-unlock/lock
    start_scheduler()
    logger.info("[OK] Scheduler started")


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("[STOP] Shutting down KU RUN Check-in API...")
    shutdown_scheduler()
    logger.info("[STOP] Scheduler stopped")

# Health check
@app.get("/api")
async def root():
    return {"message": "KU RUN Check-in API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Include routers

app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(events.router, prefix="/api/events", tags=["Events"])
app.include_router(event_holidays.router, prefix="/api", tags=["Event Holidays"])
app.include_router(participations.router, prefix="/api/participations", tags=["Participations"])
app.include_router(participant_snapshots.router, prefix="/api", tags=["Participant Snapshots"])
app.include_router(rewards.router, prefix="/api/rewards", tags=["Rewards"])
app.include_router(images.router, prefix="/api/images", tags=["Images"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(
    reward_lb_endpoints.router, 
    prefix="/api/reward-leaderboards", 
    tags=["Reward Leaderboards"]
)
app.include_router(strava.router, prefix="/api/strava", tags=["Strava"])

# Mount static files
app.mount("/api/uploads", StaticFiles(directory="uploads"), name="uploads")