"""Error Handler Middleware - Consistent error responses."""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from loguru import logger


async def error_handler_middleware(request: Request, call_next):
    """Middleware to handle errors consistently.

    Args:
        request: FastAPI request
        call_next: Next middleware/handler

    Returns:
        Response with error details if exception occurs
    """
    try:
        return await call_next(request)
    except Exception as e:
        logger.error(f"Unhandled error in {request.url.path}: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error",
                "error": str(e),
                "path": str(request.url.path),
            },
        )
