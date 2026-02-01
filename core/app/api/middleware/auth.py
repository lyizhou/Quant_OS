"""Authentication Middleware - API key validation."""

import os
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from loguru import logger


async def auth_middleware(request: Request, call_next: Callable) -> Response:
    """Middleware to validate API key for protected endpoints.

    Args:
        request: FastAPI request
        call_next: Next middleware/handler

    Returns:
        Response from next handler or 401 error
    """
    # Skip auth for health check and docs
    if request.url.path in ["/api/health", "/docs", "/openapi.json", "/redoc"]:
        return await call_next(request)

    # Check for API key
    api_key = os.getenv("QUANT_OS_API_KEY")
    if not api_key:
        logger.error("QUANT_OS_API_KEY not configured")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "API key not configured on server"},
        )

    # Get Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Missing Authorization header"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate Bearer token
    if not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Invalid Authorization header format"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header[7:]  # Remove "Bearer " prefix
    if token != api_key:
        logger.warning(f"Invalid API key attempt from {request.client.host}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Invalid API key"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    # API key valid, proceed
    return await call_next(request)
