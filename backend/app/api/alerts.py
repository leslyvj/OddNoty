"""Alerts API router."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.alert import AlertRuleCreate

router = APIRouter()


@router.get("/")
async def list_alerts(db: AsyncSession = Depends(get_db)):
    """List triggered alerts for the user."""
    # TODO: implement
    return []


@router.post("/rules")
async def create_alert_rule(rule: AlertRuleCreate, db: AsyncSession = Depends(get_db)):
    """Create a new alert rule."""
    # TODO: implement
    return {"message": "Rule created", "rule": rule.model_dump()}


@router.get("/rules")
async def list_alert_rules(db: AsyncSession = Depends(get_db)):
    """List all alert rules."""
    # TODO: implement
    return []


@router.put("/rules/{rule_id}")
async def update_alert_rule(rule_id: int, rule: AlertRuleCreate, db: AsyncSession = Depends(get_db)):
    """Update an alert rule."""
    # TODO: implement
    return {"message": "Rule updated", "rule_id": rule_id}


@router.delete("/rules/{rule_id}")
async def delete_alert_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an alert rule."""
    # TODO: implement
    return {"message": "Rule deleted", "rule_id": rule_id}
