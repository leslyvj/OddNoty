"""Tests for the rule engine."""

import pytest
from engine.rule_engine import RuleEngine


class TestRuleEngine:
    def test_matches_rule_league_filter(self):
        engine = RuleEngine()
        match = {"league": "Premier League", "match_minute": 60, "home_score": 0, "away_score": 0}
        rule = {"conditions": {"league": "La Liga"}}
        assert engine._matches_rule(match, rule) is False

    def test_matches_rule_minute_gte(self):
        engine = RuleEngine()
        match = {"league": "Premier League", "match_minute": 30, "home_score": 0, "away_score": 0}
        rule = {"conditions": {"minute_gte": 55}}
        assert engine._matches_rule(match, rule) is False

    def test_matches_rule_score_filter(self):
        engine = RuleEngine()
        match = {"league": "Premier League", "match_minute": 60, "home_score": 1, "away_score": 0}
        rule = {"conditions": {"score": "0-0"}}
        assert engine._matches_rule(match, rule) is False

    def test_matches_rule_passing(self):
        engine = RuleEngine()
        match = {"league": "Premier League", "match_minute": 60, "home_score": 0, "away_score": 0}
        rule = {"conditions": {"league": "Premier League", "minute_gte": 55, "score": "0-0"}}
        assert engine._matches_rule(match, rule) is True
