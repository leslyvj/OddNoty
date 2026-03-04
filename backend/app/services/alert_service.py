"""Alert service — business logic for alerts and alert rules."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.alert import Alert, AlertRule


async def get_active_rules(db: AsyncSession) -> list[AlertRule]:
    """Get all active alert rules."""
    result = await db.execute(select(AlertRule).where(AlertRule.is_active == True))
    return list(result.scalars().all())


async def get_user_rules(db: AsyncSession, user_id: int) -> list[AlertRule]:
    """Get alert rules for a specific user."""
    result = await db.execute(select(AlertRule).where(AlertRule.user_id == user_id))
    return list(result.scalars().all())


async def create_rule(db: AsyncSession, user_id: int, name: str, conditions: dict) -> AlertRule:
    """Create a new alert rule."""
    rule = AlertRule(user_id=user_id, name=name, conditions=conditions)
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


async def create_alert(db: AsyncSession, alert_data: dict) -> Alert:
    """Record a triggered alert."""
    alert = Alert(**alert_data)
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


async def get_user_alerts(db: AsyncSession, user_id: int) -> list[Alert]:
    """Get triggered alerts for a user."""
    result = await db.execute(
        select(Alert).where(Alert.user_id == user_id).order_by(Alert.triggered_at.desc())
    )
    return list(result.scalars().all())
