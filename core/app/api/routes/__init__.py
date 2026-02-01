"""API Routes Package."""

from .health import router as health_router
from .market import router as market_router
from .news import router as news_router
from .portfolio import router as portfolio_router
from .sectors import router as sectors_router

__all__ = [
    "health_router",
    "portfolio_router",
    "market_router",
    "news_router",
    "sectors_router",
]
