# CLAUDE.md — OddNoty

## Project Context
OddNoty is a real-time Over/Under Goal Odds Alert Platform. It is a data analytics tool — NOT a betting platform.

## Architecture
- **backend/** — FastAPI REST API (Python, async, SQLAlchemy, Alembic)
- **worker/** — Async odds ingestion worker (10s loop, fetches matches + odds, evaluates alert rules, triggers notifications)
- **frontend/** — Next.js dashboard (TypeScript, App Router, dark SaaS theme)
- **docker/** — Dockerfiles for each service
- **docker-compose.yml** — Orchestrates postgres, redis, backend, worker, frontend

## Key Rules
1. Only support Over/Under markets: 0.5, 1.5, 2.5, 3.5 (both Over and Under)
2. No betting functionality — analytics only
3. All backend endpoints must be async
4. Worker interval: 10 seconds
5. Odds movement threshold: 15% for generating movement alerts
6. Alert delivery: Telegram (primary), Email (optional)
7. Dark theme, table-first UI design

## Database Tables
- `matches` — match_id, league, home_team, away_team, start_time, status
- `odds` — match_id, market, line, bookmaker, odds, timestamp
- `alerts` — alert_id, user_id, match_id, market, condition, triggered_at
- `users` — user_id, email, telegram_id

## Data Sources (pick one)
- Sportmonks Football API
- TheOddsAPI

## Environment Variables
See `.env.example` for all required config.
