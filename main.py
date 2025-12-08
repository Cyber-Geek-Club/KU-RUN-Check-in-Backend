from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.endpoints import events, participations, rewards, users
from src.database.db_config import init_db

app = FastAPI(
    title="KU RUN Check-in API",
    description="API for KU Running Event Check-in System",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this in production
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