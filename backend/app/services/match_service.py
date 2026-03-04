"""Match service — business logic for matches."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.match import Match


async def get_live_matches(db: AsyncSession) -> list[Match]:
    """Get all currently live matches."""
    result = await db.execute(select(Match).where(Match.status == "live"))
    return list(result.scalars().all())


async def get_match_by_id(db: AsyncSession, match_id: str) -> Match | None:
    """Get a single match by ID."""
    result = await db.execute(select(Match).where(Match.match_id == match_id))
    return result.scalar_one_or_none()


async def upsert_match(db: AsyncSession, match_data: dict) -> Match:
    """Insert or update a match record."""
    existing = await get_match_by_id(db, match_data["match_id"])
    if existing:
        for key, value in match_data.items():
            setattr(existing, key, value)
    else:
        existing = Match(**match_data)
        db.add(existing)
    await db.commit()
    await db.refresh(existing)
    return existing
