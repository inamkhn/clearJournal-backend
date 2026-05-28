from fastapi import FastAPI
from app.api.v1.router import api_router
from app.core.middleware import setup_middleware
from app.core.config import settings

app = FastAPI(
    title="ClearJournal API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

setup_middleware(app)
app.include_router(api_router, prefix="/api/v1")
