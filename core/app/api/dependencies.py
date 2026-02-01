"""API Dependencies - Authentication, database connections, etc."""

import os
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.data.db import get_db

# Security scheme
security = HTTPBearer()


def verify_api_key(
    credentials: Annotated[HTTPAuthorizationCredentials, Security(security)]
) -> str:
    """Verify API key from Authorization header.

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        API key if valid

    Raises:
        HTTPException: If API key is invalid
    """
    api_key = os.getenv("QUANT_OS_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key not configured on server",
        )

    if credentials.credentials != api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return credentials.credentials


def get_database():
    """Get database connection.

    Yields:
        Database connection
    """
    return get_db()
