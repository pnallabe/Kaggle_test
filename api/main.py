"""
FastAPI main application for AI Data Analyst API
"""

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.auth import verify_jwt, get_current_user
from app.database import init_db, get_db
from app.routers import jobs, artifacts, connectors, schema, health, datasets, uploads

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    print("Starting AI Data Analyst API...")
    await init_db()
    yield
    # Shutdown
    print("Shutting down AI Data Analyst API...")

# Create FastAPI app
app = FastAPI(
    title="AI Data Analyst API",
    description="GCP-first conversational AI data analyst platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="", tags=["health"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])
app.include_router(artifacts.router, prefix="/api/v1/artifacts", tags=["artifacts"])
app.include_router(connectors.router, prefix="/api/v1/connectors", tags=["connectors"])
app.include_router(schema.router, prefix="/api/v1/projects", tags=["schema"])
app.include_router(datasets.router, prefix="/api/v1", tags=["datasets"])
app.include_router(uploads.router, prefix="/api/v1", tags=["uploads"])

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI Data Analyst API",
        "version": "1.0.0",
        "docs": "/docs",
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
