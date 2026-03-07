FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY worker/requirements.txt ./requirements_worker.txt
COPY scrapers/requirements.txt ./requirements_scrapers.txt

RUN pip install --no-cache-dir -r requirements_worker.txt
RUN pip install --no-cache-dir -r requirements_scrapers.txt

# Copy everything
COPY . .

# Set Python path
ENV PYTHONPATH=/app
ENV PYTHONIOENCODING=utf-8
ENV PORT=10000

# Entry point for the Cloud Bot
CMD ["python", "oddnoty_bot/bot.py"]
