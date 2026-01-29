"""
Main FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api.routes import audio, analysis
from app.db.database import engine, Base
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup: create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown: cleanup if needed
    await engine.dispose()


app = FastAPI(
    title="Edinorok Voice Analysis API",
    description="AI-powered vocal analysis system for vocalists",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(audio.router, prefix="/api/v1", tags=["audio"])
app.include_router(analysis.router, prefix="/api/v1", tags=["analysis"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}
