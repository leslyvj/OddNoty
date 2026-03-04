import asyncio
import logging
import sys
import os

# Add worker directory to path to import config and notifier
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "worker")))

from config import WorkerSettings
from notifier.telegram import TelegramNotifier

logging.basicConfig(level=logging.INFO)

async def test_notification():
    settings = WorkerSettings()
    
    if not settings.TELEGRAM_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
        print("❌ Error: TELEGRAM_BOT_TOKEN not set in .env")
        return
        
    if not settings.TELEGRAM_CHAT_ID or settings.TELEGRAM_CHAT_ID == "your_telegram_chat_id_here":
        print("❌ Error: TELEGRAM_CHAT_ID not set in .env")
        return

    print(f"🚀 Sending test alert to Chat ID: {settings.TELEGRAM_CHAT_ID}...")
    
    notifier = TelegramNotifier(
        bot_token=settings.TELEGRAM_BOT_TOKEN,
        chat_id=settings.TELEGRAM_CHAT_ID,
    )
    
    test_alert = {
        "home_team": "OddNoty FC",
        "away_team": "Test United",
        "match_minute": 75,
        "score": "0-0",
        "market": "Over",
        "line": 0.5,
        "rule_name": "Initial Connection Test"
    }
    
    success = await notifier.send(test_alert)
    if success:
        print("✅ Success! Check your Telegram.")
    else:
        print("❌ Alert failed to send. Check your token and Chat ID.")

if __name__ == "__main__":
    asyncio.run(test_notification())
