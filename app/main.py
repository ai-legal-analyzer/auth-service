from fastapi import FastAPI
from app.routers import auth, permission
from app.backend.db import init_db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.include_router(auth.router)
app.include_router(permission.router)


@app.on_event("startup")
async def on_startup():
    logger.info("Initializing database...")
    try:
        await init_db()
        logger.info("Database initialized successfully!")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
