"""Odds model."""

from datetime import datetime
from sqlalchemy import String, Integer, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Odds(Base):
    __tablename__ = "odds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[str] = mapped_column(String, ForeignKey("matches.match_id"), nullable=False)
    market: Mapped[str] = mapped_column(String, nullable=False)  # "over" | "under"
    line: Mapped[float] = mapped_column(Numeric(3, 1), nullable=False)  # 0.5, 1.5, 2.5, 3.5
    bookmaker: Mapped[str] = mapped_column(String, nullable=False)
    odds: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Odds {self.market} {self.line} @ {self.odds}>"
