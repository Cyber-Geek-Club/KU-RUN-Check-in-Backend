import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, DateTime, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime

# ==========================================
# 1. Database Setup (SQLite)
# ==========================================
SQLALCHEMY_DATABASE_URL = "sqlite:///./simple_checkin.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==========================================
# 2. Data Models
# ==========================================
class CheckInDB(Base):
    __tablename__ = "checkins"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    event_id = Column(Integer, nullable=False)
    checked_in_at = Column(DateTime, default=datetime.now)

    # Constraint: One user can check in only once per event
    __table_args__ = (
        UniqueConstraint('user_id', 'event_id', name='uq_user_event'),
    )

# Create tables
Base.metadata.create_all(bind=engine)

# ==========================================
# 3. Pydantic Schemas
# ==========================================
class CheckInRequest(BaseModel):
    user_id: int
    event_id: int

class CheckInResponse(BaseModel):
    id: int
    user_id: int
    event_id: int
    checked_in_at: datetime

    class Config:
        orm_mode = True

# ==========================================
# 4. API Logic
# ==========================================
app = FastAPI(title="Simple Check-in System")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/checkin", response_model=CheckInResponse)
def create_checkin(request: CheckInRequest, db: Session = Depends(get_db)):
    """
    Check-in a user to an event.
    Fails if the user has already checked in to this event.
    """
    # Check if exists
    existing = db.query(CheckInDB).filter(
        CheckInDB.user_id == request.user_id,
        CheckInDB.event_id == request.event_id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="User already checked in to this event")

    # Create new check-in
    new_checkin = CheckInDB(
        user_id=request.user_id,
        event_id=request.event_id,
        checked_in_at=datetime.now()
    )
    db.add(new_checkin)
    db.commit()
    db.refresh(new_checkin)
    
    return new_checkin

@app.get("/checkin/event/{event_id}", response_model=list[CheckInResponse])
def get_event_checkins(event_id: int, db: Session = Depends(get_db)):
    """Convert DB objects to Pydantic models list"""
    return db.query(CheckInDB).filter(CheckInDB.event_id == event_id).all()

@app.get("/checkin/user/{user_id}", response_model=list[CheckInResponse])
def get_user_checkins(user_id: int, db: Session = Depends(get_db)):
    """Get all check-in history for a user"""
    return db.query(CheckInDB).filter(CheckInDB.user_id == user_id).all()

if __name__ == "__main__":
    # Run with: python simple_checkin_server.py
    uvicorn.run(app, host="0.0.0.0", port=8000)
