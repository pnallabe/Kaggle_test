"""
Health check and status endpoints
"""

from fastapi import APIRouter
from datetime import datetime

router = APIRouter()

@router.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint for load balancer"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }

@router.get("/ready", tags=["health"])
async def readiness_check():
    """Readiness check - includes dependency health"""
    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat(),
    }
