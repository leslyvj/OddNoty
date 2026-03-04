"""Matches API router."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

router = APIRouter()


@router.get("/")
async def list_matches(
    status: str | None = Query(None, description="Filter by status: live, not_started, finished"),
    league: str | None = Query(None, description="Filter by league name"),
    db: AsyncSession = Depends(get_db),
):
    """List all matches with optional filters."""
    # TODO: implement query logic
    return []


@router.get("/{match_id}")
async def get_match(match_id: str, db: AsyncSession = Depends(get_db)):
    """Get match details by ID."""
    # TODO: implement
    return {"match_id": match_id}
