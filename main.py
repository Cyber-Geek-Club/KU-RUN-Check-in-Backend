from fastapi import FastAPI
from app.api import routes_user
from app.core.database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(routes_user.router)
