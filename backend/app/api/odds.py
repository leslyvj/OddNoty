"""Odds API router."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

router = APIRouter()


@router.get("/{match_id}")
async def get_odds(
    match_id: str,
    market: str | None = Query(None, description="over or under"),
    line: float | None = Query(None, description="0.5, 1.5, 2.5, 3.5"),
    db: AsyncSession = Depends(get_db),
):
    """Get current odds for a match."""
    # TODO: implement
    return []


@router.get("/{match_id}/history")
async def get_odds_history(
    match_id: str,
    market: str | None = Query(None),
    line: float | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get odds movement history for charting."""
    # TODO: implement
    return {"match_id": match_id, "history": []}
