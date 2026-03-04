# OddNoty — Product Specification

## Core Idea
Track football matches in real time and notify users when specific Over/Under odds conditions are met.

**Example Alert Condition:**
- Over 2.5 goals odds ≥ 2.0
- Match minute ≥ 60
- Score = 0-0

## Supported Markets

| Over | Under |
|------|-------|
| Over 0.5 | Under 0.5 |
| Over 1.5 | Under 1.5 |
| Over 2.5 | Under 2.5 |
| Over 3.5 | Under 3.5 |

## MVP Features
1. Live Match List
2. Over/Under odds monitoring
3. Custom alert rules
4. Odds movement tracking
5. Telegram alerts
6. Basic dashboard

## Alert Rule Engine
Users create rules with conditions on:
- Odds threshold (e.g., over_1_5_odds ≥ 1.8)
- Match minute (e.g., ≥ 55)
- Score condition (e.g., 0-0)
- League filter

## Dashboard
- Live matches table: League, Match, Minute, Score, Over 1.5/2.5/3.5 Odds
- Filters: League, Odds threshold, Minute range

## Match Details Page
- Live score + match timeline
- Odds vs Time chart

## Odds Movement Detection
- Trigger on ≥ 15% change (increase or drop)
- Example: Over 2.5 odds 1.85 → 2.20

## Performance Target
- 1000 concurrent matches
- 10 second refresh interval

## Data Pipeline (10s loop)
1. Fetch live matches → 2. Fetch odds → 3. Store snapshot → 4. Compare with previous → 5. Evaluate rules → 6. Trigger alerts

## Target Users
- Football bettors
- Trading syndicates
- Sports analysts
