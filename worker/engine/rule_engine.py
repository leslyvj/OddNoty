"""Alert Rule Engine.

Evaluates user-defined alert rules against current match + odds data.

A rule condition looks like:
{
    "market": "over",
    "line": 1.5,
    "odds_gte": 1.8,
    "minute_gte": 55,
    "score": "0-0",
    "league": "Premier League"
}
"""

import logging

logger = logging.getLogger("oddnoty.engine")


class RuleEngine:
    """Evaluate alert rules against live match data."""

    def __init__(self):
        # TODO: load rules from DB
        self.rules: list[dict] = []

    async def evaluate_all(self, matches: list[dict]) -> list[dict]:
        """Evaluate all active rules against current matches.

        Returns a list of triggered alert payloads.
        """
        triggered = []
        for match in matches:
            for rule in self.rules:
                if self._matches_rule(match, rule):
                    triggered.append(self._build_alert(match, rule))
        return triggered

    def _matches_rule(self, match: dict, rule: dict) -> bool:
        """Check if a single match satisfies a rule's conditions."""
        conditions = rule.get("conditions", {})

        # Check league filter
        league_filter = conditions.get("league")
        if league_filter and match.get("league") != league_filter:
            return False

        # Check minute condition
        minute_gte = conditions.get("minute_gte")
        if minute_gte and match.get("match_minute", 0) < minute_gte:
            return False

        minute_lte = conditions.get("minute_lte")
        if minute_lte and match.get("match_minute", 0) > minute_lte:
            return False

        # Check score condition
        score_filter = conditions.get("score")
        if score_filter:
            current_score = f"{match.get('home_score', 0)}-{match.get('away_score', 0)}"
            if current_score != score_filter:
                return False

        # Check odds threshold
        # TODO: look up current odds for the specified market/line
        # odds_gte = conditions.get("odds_gte")
        # odds_lte = conditions.get("odds_lte")

        return True

    def _build_alert(self, match: dict, rule: dict) -> dict:
        """Build an alert payload for notification."""
        conditions = rule.get("conditions", {})
        return {
            "match_id": match.get("match_id"),
            "home_team": match.get("home_team"),
            "away_team": match.get("away_team"),
            "match_minute": match.get("match_minute"),
            "score": f"{match.get('home_score', 0)}-{match.get('away_score', 0)}",
            "market": conditions.get("market", "over"),
            "line": conditions.get("line", 2.5),
            "rule_name": rule.get("name", "Unnamed Rule"),
        }
