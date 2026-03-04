"""Alert schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class AlertRuleConditions(BaseModel):
    market: str = "over"
    line: float = 2.5
    odds_gte: Optional[float] = None
    odds_lte: Optional[float] = None
    minute_gte: Optional[int] = None
    minute_lte: Optional[int] = None
    score: Optional[str] = None  # e.g. "0-0"
    league: Optional[str] = None


class AlertRuleCreate(BaseModel):
    name: str
    conditions: AlertRuleConditions


class AlertRuleResponse(BaseModel):
    rule_id: int
    user_id: int
    name: str
    conditions: dict
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AlertResponse(BaseModel):
    alert_id: int
    user_id: int
    match_id: str
    market: str
    condition: dict
    triggered_at: datetime

    class Config:
        from_attributes = True
