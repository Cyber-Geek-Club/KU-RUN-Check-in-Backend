from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from src.database.db_config import init_db
from fastapi.staticfiles import StaticFiles
# รวม import ไว้ที่เดียว และเรียกใช้ images (ต้องตรวจสอบชื่อไฟล์ปลายทางให้ตรงกัน)
from src.api.endpoints import events, participations, rewards, users, images

app = FastAPI(
    title="KU RUN Check-in API",
    description="API for KU Running Event Check-in System",
    version="1.0.0"
)

# Read allowed origins
_allowed = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")
allowed_origins = [o.strip() for o in _allowed.split(",") if o.strip()]

# Important: Do NOT use ["*"] when allow_credentials=True.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # <-- แก้ไข: ใช้ List ที่กำหนดไว้ ห้ามใช้ ["*"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database connection
@app.on_event("startup")
async def on_startup():
    await init_db()

# Health check
@app.get("/")
async def root():
    return {"message": "KU RUN Check-in API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Include routers
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(events.router, prefix="/api/events", tags=["Events"])
app.include_router(participations.router, prefix="/api/participations", tags=["Participations"])
app.include_router(rewards.router, prefix="/api/rewards", tags=["Rewards"])

# Mount static files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Add images router
app.include_router(images.router, prefix="/api/images", tags=["Images"])