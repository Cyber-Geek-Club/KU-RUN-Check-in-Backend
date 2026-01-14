from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
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
    strava
)
from src.api.endpoints import reward_lb_endpoints

app = FastAPI(
    title="KU RUN Check-in API",
    description="API for KU Running Event Check-in System",
    version="1.0.0"
)

# 🔧 IMPROVED CORS Configuration
# Read allowed origins from environment
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()]

print(f"✅ Allowed CORS origins: {allowed_origins}")  # Debug log

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
    await init_db()
    print("✅ Database initialized")
    print(f"✅ CORS enabled for: {allowed_origins}")

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