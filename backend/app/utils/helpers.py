"""General helper utilities."""


def format_score(home_score: int, away_score: int) -> str:
    """Format score as 'H-A' string."""
    return f"{home_score}-{away_score}"


def calculate_odds_change_percent(old_odds: float, new_odds: float) -> float:
    """Calculate percentage change between two odds values."""
    if old_odds == 0:
        return 0.0
    return round(((new_odds - old_odds) / old_odds) * 100, 2)


SUPPORTED_MARKETS = [
    ("over", 0.5),
    ("over", 1.5),
    ("over", 2.5),
    ("over", 3.5),
    ("under", 0.5),
    ("under", 1.5),
    ("under", 2.5),
    ("under", 3.5),
]
