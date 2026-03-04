"""Odds service — business logic for odds."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.odds import Odds


async def get_latest_odds(db: AsyncSession, match_id: str) -> list[Odds]:
    """Get the latest odds snapshot for a match (all markets)."""
    # Subquery approach: get the most recent timestamp per market/line
    result = await db.execute(
        select(Odds)
        .where(Odds.match_id == match_id)
        .order_by(desc(Odds.timestamp))
    )
    return list(result.scalars().all())


async def get_odds_history(
    db: AsyncSession,
    match_id: str,
    market: str | None = None,
    line: float | None = None,
) -> list[Odds]:
    """Get odds history for charting."""
    query = select(Odds).where(Odds.match_id == match_id)
    if market:
        query = query.where(Odds.market == market)
    if line:
        query = query.where(Odds.line == line)
    query = query.order_by(Odds.timestamp)
    result = await db.execute(query)
    return list(result.scalars().all())


async def store_odds_snapshot(db: AsyncSession, odds_data: dict) -> Odds:
    """Store a new odds snapshot."""
    odds = Odds(**odds_data)
    db.add(odds)
    await db.commit()
    await db.refresh(odds)
    return odds
