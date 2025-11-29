from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.db_config import SessionLocal
from src.crud import task_crud
from src.schemas.task_schema import TaskCreate, TaskUpdate, TaskRead

router = APIRouter()

async def get_db():
    async with SessionLocal() as session:
        yield session

@router.get("/", response_model=list[TaskRead])
async def read_tasks(db: AsyncSession = Depends(get_db)):
    return await task_crud.get_tasks(db)

@router.post("/", response_model=TaskRead)
async def create_task(task: TaskCreate, db: AsyncSession = Depends(get_db)):
    return await task_crud.create_task(db, task)

@router.put("/{task_id}", response_model=TaskRead)
async def update_task(task_id: int, task: TaskUpdate, db: AsyncSession = Depends(get_db)):
    updated = await task_crud.update_task(db, task_id, task)
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")
    return updated
