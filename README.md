# OddNoty 🚨⚽

**Real-time Over/Under Goal Odds Alert Platform**

OddNoty monitors live football matches and generates alerts when specific Over/Under odds conditions are met — helping bettors, trading syndicates, and sports analysts spot profitable opportunities in real time.

---

## Tech Stack

| Layer      | Technology     |
|------------|----------------|
| Frontend   | Next.js (App Router, TypeScript) |
| Backend    | FastAPI (Python) |
| Worker     | Python async worker |
| Database   | PostgreSQL |
| Cache      | Redis |
| Alerts     | Telegram Bot |
| Deployment | Docker / Docker Compose |

## Supported Markets

| Over    | Under    |
|---------|----------|
| Over 0.5 | Under 0.5 |
| Over 1.5 | Under 1.5 |
| Over 2.5 | Under 2.5 |
| Over 3.5 | Under 3.5 |

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Node.js 18+ (for frontend dev)
- Python 3.11+ (for backend / worker dev)
- PostgreSQL 15+
- Redis 7+

### 1. Clone & Configure

```bash
git clone <repo-url> OddNoty
cd OddNoty
cp .env.example .env
# Edit .env with your API keys and database credentials
```

### 2. Run with Docker Compose

```bash
docker-compose up --build
```

| Service   | URL                        |
|-----------|----------------------------|
| Frontend  | http://localhost:3000       |
| Backend   | http://localhost:8000       |
| API Docs  | http://localhost:8000/docs  |

### 3. Local Development

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Worker:**
```bash
cd worker
pip install -r requirements.txt
python main.py
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Project Structure

```
OddNoty/
├── backend/          # FastAPI backend
├── frontend/         # Next.js frontend
├── worker/           # Async odds worker
├── docker/           # Dockerfiles
├── docs/             # Documentation
├── scripts/          # Utility scripts
├── docker-compose.yml
├── .env.example
└── README.md
```

## Data Pipeline (every 10 seconds)

1. Fetch live matches from API
2. Fetch current odds
3. Store odds snapshot in DB
4. Compare with previous odds
5. Evaluate alert rules
6. Trigger alerts (Telegram)

## License

MIT
