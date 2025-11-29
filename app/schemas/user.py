from pydantic import BaseModel

class UserBase(BaseModel):
    email: str
    name: str

class UserCreate(UserBase):
    pass

class UserRead(UserBase):
    id: int

    class Config:
        orm_mode = True
