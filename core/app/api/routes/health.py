"""Health Check Route - API health status."""

from datetime import datetime

from fastapi import APIRouter
from loguru import logger

from app.api.models import HealthResponse
from app.data.db import get_db

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint.

    Returns:
        Health status information
    """
    try:
        # Test database connection
        db = get_db()
        db.execute("SELECT 1").fetchone()
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = f"error: {str(e)}"

    return HealthResponse(
        status="healthy",
        version="2.0.0",
        database=db_status,
        timestamp=datetime.now(),
    )
