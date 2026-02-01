"""News Routes - Stock news search."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger

from app.api.dependencies import verify_api_key
from app.api.models import NewsItem, NewsResponse
from app.drivers.cn_market_driver.driver import CNMarketDriver
from app.services.news_search import get_news_search_service

router = APIRouter()


@router.get("/news", response_model=NewsResponse)
async def search_stock_news(
    code: Annotated[str, Query(description="Stock code (e.g., 000001)")],
    days: Annotated[int, Query(description="Search last N days", ge=1, le=30)] = 7,
    max_results: Annotated[int, Query(description="Max results", ge=1, le=20)] = 5,
    api_key: Annotated[str, Depends(verify_api_key)],
):
    """Search news for a stock.

    Args:
        code: Stock code
        days: Search last N days
        max_results: Maximum number of results

    Returns:
        News articles related to the stock
    """
    try:
        driver = CNMarketDriver()
        stock_info = driver.get_stock_info(code)

        if not stock_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock {code} not found",
            )

        news_service = get_news_search_service()
        news_list = news_service.search_stock_news(
            stock_name=stock_info["name"],
            stock_code=code,
            days=days,
            max_results=max_results,
        )

        return NewsResponse(
            stock_code=code,
            stock_name=stock_info["name"],
            news=[
                NewsItem(
                    title=n["title"],
                    url=n["url"],
                    summary=n["summary"],
                    date=n["date"],
                    source=n["source"],
                )
                for n in news_list
            ],
            total=len(news_list),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to search news for {code}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search news: {str(e)}",
        )
