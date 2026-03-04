---
description: How to run the full OddNoty stack locally with Docker Compose
---

# Run Full Stack

// turbo-all

1. Copy environment template:
```bash
cp .env.example .env
```

2. Edit `.env` with your API keys and credentials.

3. Start all services:
```bash
docker-compose up --build
```

4. Access the services:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

5. Stop all services:
```bash
docker-compose down
```
