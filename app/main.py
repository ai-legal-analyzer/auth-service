from fastapi import FastAPI
from app.routers import auth, permission

app = FastAPI()

app.include_router(auth.router)
app.include_router(permission.router)
