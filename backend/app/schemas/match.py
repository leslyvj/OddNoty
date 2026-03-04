"""Match schemas."""

from datetime import datetime
from pydantic import BaseModel


class MatchBase(BaseModel):
    match_id: str
    league: str
    home_team: str
    away_team: str
    start_time: datetime


class MatchResponse(MatchBase):
    home_score: int = 0
    away_score: int = 0
    match_minute: int = 0
    status: str = "not_started"

    class Config:
        from_attributes = True


class MatchListResponse(BaseModel):
    matches: list[MatchResponse]
    total: int
