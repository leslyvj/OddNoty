"""Odds schemas."""

from datetime import datetime
from pydantic import BaseModel


class OddsResponse(BaseModel):
    id: int
    match_id: str
    market: str
    line: float
    bookmaker: str
    odds: float
    timestamp: datetime

    class Config:
        from_attributes = True


class OddsHistoryResponse(BaseModel):
    match_id: str
    market: str
    line: float
    history: list[OddsResponse]
