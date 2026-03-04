#!/usr/bin/env bash
# Setup script for OddNoty development environment
echo "🚨 Setting up OddNoty..."

# Copy env template
if [ ! -f .env ]; then
  cp .env.example .env
  echo "✅ Created .env from template"
else
  echo "⚠️  .env already exists, skipping"
fi

# Backend
echo "📦 Installing backend dependencies..."
cd backend && pip install -r requirements.txt && cd ..

# Worker
echo "📦 Installing worker dependencies..."
cd worker && pip install -r requirements.txt && cd ..

# Frontend
echo "📦 Installing frontend dependencies..."
cd frontend && npm install && cd ..

echo ""
echo "✅ Setup complete! Run 'docker-compose up --build' to start."
