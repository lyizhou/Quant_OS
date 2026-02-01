"""API Models - Pydantic models for request/response validation."""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


# Portfolio Models
class PortfolioItemCreate(BaseModel):
    """Request model for creating a portfolio item."""

    stock_code: str = Field(..., description="Stock code (e.g., 000001)")
    stock_name: str = Field(..., description="Stock name")
    quantity: int = Field(..., gt=0, description="Quantity of shares")
    cost_price: Decimal = Field(..., gt=0, description="Cost price per share")


class PortfolioItemUpdate(BaseModel):
    """Request model for updating a portfolio item."""

    quantity: Optional[int] = Field(None, gt=0, description="Quantity of shares")
    cost_price: Optional[Decimal] = Field(None, gt=0, description="Cost price per share")


class PortfolioItemResponse(BaseModel):
    """Response model for a portfolio item."""

    id: int
    stock_code: str
    stock_name: str
    quantity: int
    cost_price: Decimal
    current_price: Optional[Decimal] = None
    market_value: Optional[Decimal] = None
    profit_loss: Optional[Decimal] = None
    profit_loss_pct: Optional[Decimal] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class PortfolioSyncRequest(BaseModel):
    """Request model for syncing portfolio from image."""

    image_url: Optional[str] = Field(None, description="URL to portfolio screenshot")
    image_base64: Optional[str] = Field(None, description="Base64-encoded image data")


# Market Data Models
class StockQuoteResponse(BaseModel):
    """Response model for stock quote."""

    stock_code: str
    stock_name: str
    current_price: Decimal
    change: Decimal
    change_pct: Decimal
    open_price: Optional[Decimal] = None
    high_price: Optional[Decimal] = None
    low_price: Optional[Decimal] = None
    volume: Optional[int] = None
    turnover: Optional[Decimal] = None
    timestamp: datetime


class TechnicalAnalysisResponse(BaseModel):
    """Response model for technical analysis."""

    stock_code: str
    stock_name: str
    indicators: dict
    chart_url: Optional[str] = None


# News Models
class NewsItem(BaseModel):
    """News item model."""

    title: str
    url: str
    summary: str
    date: str
    source: str


class NewsResponse(BaseModel):
    """Response model for news search."""

    stock_code: str
    stock_name: str
    news: List[NewsItem]
    total: int


# Sector Models
class SectorCreate(BaseModel):
    """Request model for creating a sector."""

    name: str = Field(..., description="Sector name")
    description: Optional[str] = Field(None, description="Sector description")


class SectorResponse(BaseModel):
    """Response model for a sector."""

    id: int
    name: str
    description: Optional[str] = None
    stock_count: int = 0
    created_at: datetime


# Health Check Models
class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str
    version: str
    database: str
    timestamp: datetime
