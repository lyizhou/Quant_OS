"""Portfolio Routes - Portfolio management endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from app.api.dependencies import get_database, verify_api_key
from app.api.models import (
    PortfolioItemCreate,
    PortfolioItemResponse,
    PortfolioItemUpdate,
    PortfolioSyncRequest,
)
from app.data.repositories.user_portfolio_repo import UserPortfolioRepository
from app.drivers.cn_market_driver.driver import CNMarketDriver
from app.usecases.portfolio_management import PortfolioManagement

router = APIRouter()


@router.get("/portfolio", response_model=list[PortfolioItemResponse])
async def list_portfolio(
    api_key: Annotated[str, Depends(verify_api_key)],
    db=Depends(get_database),
):
    """List all portfolio positions.

    Returns:
        List of portfolio items with current prices and P&L
    """
    try:
        repo = UserPortfolioRepository(db)
        driver = CNMarketDriver()
        pm = PortfolioManagement(repo, driver)

        positions = pm.get_all_positions()

        return [
            PortfolioItemResponse(
                id=p["id"],
                stock_code=p["stock_code"],
                stock_name=p["stock_name"],
                quantity=p["quantity"],
                cost_price=p["cost_price"],
                current_price=p.get("current_price"),
                market_value=p.get("market_value"),
                profit_loss=p.get("profit_loss"),
                profit_loss_pct=p.get("profit_loss_pct"),
                created_at=p["created_at"],
                updated_at=p.get("updated_at"),
            )
            for p in positions
        ]
    except Exception as e:
        logger.error(f"Failed to list portfolio: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve portfolio: {str(e)}",
        )


@router.post("/portfolio", response_model=PortfolioItemResponse, status_code=status.HTTP_201_CREATED)
async def add_portfolio_item(
    item: PortfolioItemCreate,
    api_key: Annotated[str, Depends(verify_api_key)],
    db=Depends(get_database),
):
    """Add a new portfolio position.

    Args:
        item: Portfolio item to add

    Returns:
        Created portfolio item
    """
    try:
        repo = UserPortfolioRepository(db)
        driver = CNMarketDriver()
        pm = PortfolioManagement(repo, driver)

        position = pm.add_position(
            stock_code=item.stock_code,
            stock_name=item.stock_name,
            quantity=item.quantity,
            cost_price=float(item.cost_price),
        )

        return PortfolioItemResponse(
            id=position["id"],
            stock_code=position["stock_code"],
            stock_name=position["stock_name"],
            quantity=position["quantity"],
            cost_price=position["cost_price"],
            current_price=position.get("current_price"),
            market_value=position.get("market_value"),
            profit_loss=position.get("profit_loss"),
            profit_loss_pct=position.get("profit_loss_pct"),
            created_at=position["created_at"],
            updated_at=position.get("updated_at"),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to add portfolio item: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add portfolio item: {str(e)}",
        )


@router.put("/portfolio/{item_id}", response_model=PortfolioItemResponse)
async def update_portfolio_item(
    item_id: int,
    item: PortfolioItemUpdate,
    api_key: Annotated[str, Depends(verify_api_key)],
    db=Depends(get_database),
):
    """Update a portfolio position.

    Args:
        item_id: Portfolio item ID
        item: Updated portfolio data

    Returns:
        Updated portfolio item
    """
    try:
        repo = UserPortfolioRepository(db)
        driver = CNMarketDriver()
        pm = PortfolioManagement(repo, driver)

        # Get existing position
        existing = repo.get_by_id(item_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Portfolio item {item_id} not found",
            )

        # Update fields
        if item.quantity is not None:
            existing["quantity"] = item.quantity
        if item.cost_price is not None:
            existing["cost_price"] = float(item.cost_price)

        # Update in database
        repo.update(item_id, existing)

        # Get updated position with current price
        position = pm.get_position_by_id(item_id)

        return PortfolioItemResponse(
            id=position["id"],
            stock_code=position["stock_code"],
            stock_name=position["stock_name"],
            quantity=position["quantity"],
            cost_price=position["cost_price"],
            current_price=position.get("current_price"),
            market_value=position.get("market_value"),
            profit_loss=position.get("profit_loss"),
            profit_loss_pct=position.get("profit_loss_pct"),
            created_at=position["created_at"],
            updated_at=position.get("updated_at"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update portfolio item: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update portfolio item: {str(e)}",
        )


@router.delete("/portfolio/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio_item(
    item_id: int,
    api_key: Annotated[str, Depends(verify_api_key)],
    db=Depends(get_database),
):
    """Delete a portfolio position.

    Args:
        item_id: Portfolio item ID
    """
    try:
        repo = UserPortfolioRepository(db)
        pm = PortfolioManagement(repo, None)

        success = pm.delete_position(item_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Portfolio item {item_id} not found",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete portfolio item: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete portfolio item: {str(e)}",
        )


@router.post("/portfolio/sync")
async def sync_portfolio_from_image(
    request: PortfolioSyncRequest,
    api_key: Annotated[str, Depends(verify_api_key)],
    db=Depends(get_database),
):
    """Sync portfolio from screenshot using AI vision.

    Args:
        request: Image URL or base64 data

    Returns:
        Sync results
    """
    try:
        from app.usecases.portfolio_image_sync import PortfolioImageSync

        repo = UserPortfolioRepository(db)
        driver = CNMarketDriver()
        sync = PortfolioImageSync(repo, driver)

        # TODO: Implement image sync logic
        # This requires handling image upload/download and AI vision processing

        return {
            "status": "not_implemented",
            "message": "Image sync feature coming soon",
        }
    except Exception as e:
        logger.error(f"Failed to sync portfolio from image: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync portfolio: {str(e)}",
        )
