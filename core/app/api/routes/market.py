"""Market Data Routes - Stock quotes and technical analysis."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger

from app.api.dependencies import verify_api_key
from app.api.models import StockQuoteResponse, TechnicalAnalysisResponse
from app.drivers.cn_market_driver.driver import CNMarketDriver
from app.drivers.cn_market_driver.technical_analysis import TechnicalAnalysis

router = APIRouter()


@router.get("/market/quote", response_model=StockQuoteResponse)
async def get_stock_quote(
    code: Annotated[str, Query(description="Stock code (e.g., 000001)")],
    api_key: Annotated[str, Depends(verify_api_key)],
):
    """Get real-time stock quote.

    Args:
        code: Stock code

    Returns:
        Stock quote with current price and change
    """
    try:
        driver = CNMarketDriver()
        quote = driver.get_realtime_quote(code)

        if not quote:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock {code} not found",
            )

        return StockQuoteResponse(
            stock_code=quote["stock_code"],
            stock_name=quote["stock_name"],
            current_price=quote["current_price"],
            change=quote["change"],
            change_pct=quote["change_pct"],
            open_price=quote.get("open_price"),
            high_price=quote.get("high_price"),
            low_price=quote.get("low_price"),
            volume=quote.get("volume"),
            turnover=quote.get("turnover"),
            timestamp=quote["timestamp"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get quote for {code}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve quote: {str(e)}",
        )


@router.get("/market/technical", response_model=TechnicalAnalysisResponse)
async def get_technical_analysis(
    code: Annotated[str, Query(description="Stock code (e.g., 000001)")],
    api_key: Annotated[str, Depends(verify_api_key)],
):
    """Get technical analysis for a stock.

    Args:
        code: Stock code

    Returns:
        Technical indicators and analysis
    """
    try:
        driver = CNMarketDriver()
        ta = TechnicalAnalysis(driver)

        # Get stock info
        stock_info = driver.get_stock_info(code)
        if not stock_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock {code} not found",
            )

        # Get technical indicators
        indicators = ta.calculate_indicators(code, days=60)

        return TechnicalAnalysisResponse(
            stock_code=code,
            stock_name=stock_info["name"],
            indicators=indicators,
            chart_url=None,  # TODO: Generate chart
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get technical analysis for {code}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve technical analysis: {str(e)}",
        )


@router.get("/market/summary")
async def get_market_summary(
    api_key: Annotated[str, Depends(verify_api_key)],
):
    """Get daily market summary.

    Returns:
        Market summary with key statistics
    """
    try:
        # TODO: Implement market summary logic
        return {
            "status": "not_implemented",
            "message": "Market summary feature coming soon",
        }
    except Exception as e:
        logger.error(f"Failed to get market summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve market summary: {str(e)}",
        )
