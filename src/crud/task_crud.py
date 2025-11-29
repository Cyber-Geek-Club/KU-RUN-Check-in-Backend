from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.task import Task
from src.schemas.task_schema import TaskCreate, TaskUpdate

async def get_tasks(db: AsyncSession):
    result = await db.execute(select(Task))
    return result.scalars().all()

async def create_task(db: AsyncSession, task: TaskCreate):
    new_task = Task(**task.dict())
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    return new_task

async def update_task(db: AsyncSession, task_id: int, task_data: TaskUpdate):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        return None
    for key, value in task_data.dict(exclude_unset=True).items():
        setattr(task, key, value)
    await db.commit()
    await db.refresh(task)
    return task
