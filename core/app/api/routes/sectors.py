"""Sector Routes - Sector management."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from app.api.dependencies import get_database, verify_api_key
from app.api.models import SectorCreate, SectorResponse
from app.data.repositories.sector_repo import SectorRepository

router = APIRouter()


@router.get("/sectors", response_model=list[SectorResponse])
async def list_sectors(
    api_key: Annotated[str, Depends(verify_api_key)],
    db=Depends(get_database),
):
    """List all sectors.

    Returns:
        List of sectors
    """
    try:
        repo = SectorRepository(db)
        sectors = repo.get_all()

        return [
            SectorResponse(
                id=s["id"],
                name=s["name"],
                description=s.get("description"),
                stock_count=s.get("stock_count", 0),
                created_at=s["created_at"],
            )
            for s in sectors
        ]
    except Exception as e:
        logger.error(f"Failed to list sectors: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve sectors: {str(e)}",
        )


@router.post("/sectors", response_model=SectorResponse, status_code=status.HTTP_201_CREATED)
async def create_sector(
    sector: SectorCreate,
    api_key: Annotated[str, Depends(verify_api_key)],
    db=Depends(get_database),
):
    """Create a new sector.

    Args:
        sector: Sector to create

    Returns:
        Created sector
    """
    try:
        repo = SectorRepository(db)
        created = repo.create(name=sector.name, description=sector.description)

        return SectorResponse(
            id=created["id"],
            name=created["name"],
            description=created.get("description"),
            stock_count=0,
            created_at=created["created_at"],
        )
    except Exception as e:
        logger.error(f"Failed to create sector: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create sector: {str(e)}",
        )


@router.get("/sectors/{sector_id}/stocks")
async def get_sector_stocks(
    sector_id: int,
    api_key: Annotated[str, Depends(verify_api_key)],
    db=Depends(get_database),
):
    """Get stocks in a sector.

    Args:
        sector_id: Sector ID

    Returns:
        List of stocks in the sector
    """
    try:
        repo = SectorRepository(db)
        sector = repo.get_by_id(sector_id)

        if not sector:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sector {sector_id} not found",
            )

        stocks = repo.get_stocks_in_sector(sector_id)

        return {
            "sector_id": sector_id,
            "sector_name": sector["name"],
            "stocks": stocks,
            "total": len(stocks),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get stocks for sector {sector_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve sector stocks: {str(e)}",
        )
