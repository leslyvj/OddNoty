---
name: OddNoty Development
description: Instructions for developing and extending the OddNoty platform
---

# OddNoty Development Skill

## Overview
OddNoty is a real-time Over/Under Goal Odds Alert Platform for football matches. It monitors live matches and generates alerts when specific Over/Under odds conditions are met.

## Tech Stack
- **Backend:** FastAPI (Python 3.11+)
- **Frontend:** Next.js 14 (TypeScript, App Router)
- **Worker:** Python async worker (asyncio + aiohttp)
- **Database:** PostgreSQL 15 with SQLAlchemy + Alembic
- **Cache:** Redis 7
- **Alerts:** Telegram Bot API
- **Deployment:** Docker + Docker Compose

## Key Conventions

### Backend
- Use async endpoints everywhere (`async def`)
- Models live in `backend/app/models/`
- Schemas in `backend/app/schemas/`  
- Routers in `backend/app/api/`
- Business logic in `backend/app/services/`
- Use Alembic for all migrations

### Worker
- 10-second polling loop
- Fetchers in `worker/fetcher/`
- Rule engine in `worker/engine/`
- Notifiers in `worker/notifier/`

### Frontend
- Use App Router (`src/app/`)
- Components in `src/components/`
- API helpers in `src/lib/api.ts`
- Dark theme, SaaS-style design

## Supported Markets
Only: Over/Under 0.5, 1.5, 2.5, 3.5

## Running Locally
```bash
# Full stack
docker-compose up --build

# Backend only
cd backend && uvicorn app.main:app --reload

# Worker only
cd worker && python main.py

# Frontend only
cd frontend && npm run dev
```
