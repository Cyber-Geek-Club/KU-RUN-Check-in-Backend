from fastapi import FastAPI
from src.api.endpoints import tasks
from src.database.db_config import init_db

app = FastAPI(title="My API Project")

# Initialize database connection
@app.on_event("startup")
async def on_startup():
    await init_db()

# Include endpoints
app.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])
