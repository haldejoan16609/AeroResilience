"""
AeroResilience — FastAPI Application
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.database import init_db
from app.routes import pages, api


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    await init_db()
    print("[OK] AeroResilience is running -- http://localhost:8000")
    yield


app = FastAPI(
    title="AeroResilience",
    description="AI for Clean Air & Climate Resilience",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(pages.router)
app.include_router(api.router)
