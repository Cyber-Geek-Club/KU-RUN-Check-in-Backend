from pydantic import BaseModel

try:
    from pydantic import ConfigDict
except ImportError:
    ConfigDict = None

class TaskBase(BaseModel):
    title: str
    description: str | None = None

class TaskCreate(TaskBase):
    pass

class TaskUpdate(TaskBase):
    completed: bool | None = None

class TaskShow(TaskBase):
    id:int

class TaskRead(TaskBase):
    id: int
    completed: bool

    if ConfigDict:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True
