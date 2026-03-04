# OddNoty — API Reference

Base URL: `http://localhost:8000`

## Matches

### `GET /api/matches`
List all live matches with current odds.

**Query Params:**
- `status` — Filter by status (`live`, `not_started`, `finished`)
- `league` — Filter by league name

**Response:** `200 OK`
```json
[
  {
    "match_id": "12345",
    "league": "Premier League",
    "home_team": "Chelsea",
    "away_team": "Arsenal",
    "home_score": 0,
    "away_score": 0,
    "match_minute": 62,
    "status": "live"
  }
]
```

### `GET /api/matches/{match_id}`
Get match details with full odds history.

---

## Odds

### `GET /api/odds/{match_id}`
Get current odds for a match.

**Query Params:**
- `market` — `over` or `under`
- `line` — `0.5`, `1.5`, `2.5`, `3.5`

### `GET /api/odds/{match_id}/history`
Get odds movement history for charting.

---

## Alerts

### `GET /api/alerts`
List triggered alerts for the authenticated user.

### `POST /api/alert-rules`
Create a new alert rule.

**Body:**
```json
{
  "name": "High odds late game",
  "conditions": {
    "market": "over",
    "line": 1.5,
    "odds_gte": 1.8,
    "minute_gte": 55,
    "score": "0-0",
    "league": "Premier League"
  }
}
```

### `GET /api/alert-rules`
List all alert rules for the user.

### `PUT /api/alert-rules/{rule_id}`
Update an alert rule.

### `DELETE /api/alert-rules/{rule_id}`
Delete an alert rule.

---

## Users

### `POST /api/users`
Register a new user.

### `GET /api/users/me`
Get current user profile.
