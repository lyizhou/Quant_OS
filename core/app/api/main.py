"""Quant_OS FastAPI Application - Main entry point for HTTP API."""

import os
import sys
from pathlib import Path

# Add paths for module imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "drivers"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.middleware import error_handler_middleware, limiter
from app.api.routes import (
    health_router,
    market_router,
    news_router,
    portfolio_router,
    sectors_router,
)
from app.common.logging import logger as app_logger
from app.data.db import initialize_db

# Create FastAPI app
app = FastAPI(
    title="Quant_OS API",
    description="AI-powered A-share portfolio management API for OpenClaw integration",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add error handler middleware
app.middleware("http")(error_handler_middleware)

# Include routers
app.include_router(health_router, prefix="/api", tags=["Health"])
app.include_router(portfolio_router, prefix="/api", tags=["Portfolio"])
app.include_router(market_router, prefix="/api", tags=["Market Data"])
app.include_router(news_router, prefix="/api", tags=["News"])
app.include_router(sectors_router, prefix="/api", tags=["Sectors"])


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("Starting Quant_OS API v2.0.0...")

    # Initialize database
    try:
        initialize_db()

        # Run migrations
        from app.data.db import get_db

        db = get_db()
        migrations_dir = Path(__file__).parent.parent / "data" / "migrations"
        if migrations_dir.exists():
            migration_files = sorted(migrations_dir.glob("*.sql"))
            for migration_file in migration_files:
                try:
                    db.execute_script(str(migration_file))
                    logger.info(f"✓ Ran migration: {migration_file.name}")
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        logger.warning(f"Migration warning: {migration_file.name}: {e}")

        logger.info("✓ Database initialized")
    except Exception as e:
        logger.error(f"✗ Failed to initialize database: {e}")
        raise

    # Check required environment variables
    required_vars = ["TUSHARE_TOKEN", "QUANT_OS_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.warning(f"⚠ Missing environment variables: {', '.join(missing_vars)}")

    logger.info("✓ Quant_OS API started successfully")
    logger.info(f"  - API Documentation: http://localhost:{os.getenv('QUANT_OS_API_PORT', 8000)}/docs")
    logger.info(f"  - Health Check: http://localhost:{os.getenv('QUANT_OS_API_PORT', 8000)}/api/health")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Quant_OS API...")


@app.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "name": "Quant_OS API",
        "version": "2.0.0",
        "description": "AI-powered A-share portfolio management API",
        "docs": "/docs",
        "health": "/api/health",
        "timestamp": datetime.now().isoformat(),
    }


def start():
    """Start the API server."""
    import uvicorn

    host = os.getenv("QUANT_OS_API_HOST", "0.0.0.0")
    port = int(os.getenv("QUANT_OS_API_PORT", 8000))

    logger.info(f"Starting Quant_OS API on {host}:{port}")

    uvicorn.run(
        "app.api.main:app",
        host=host,
        port=port,
        reload=False,  # Set to True for development
        log_level="info",
    )


if __name__ == "__main__":
    start()
