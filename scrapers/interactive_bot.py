import asyncio
import logging
import os
import re
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

from scrapers.bookmakers.onexbet import OneXBetScraper
from worker.notifier.telegram import TelegramNotifier

# Load environment variables
load_dotenv()

# Logging to both console and file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot_activity.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DynamicBot")

# Global track tasks: { (match_name, team_num, line): task_object }
active_tracks = {}

class OddTrackerEngine:
    def __init__(self, bot_token, chat_id):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.notifier = TelegramNotifier(bot_token, chat_id)
        self.scraper = OneXBetScraper(headless=True)

    async def monitor(self, match_name, team_num, line):
        """Monitors a specific market and sends updates to Telegram."""
        last_odd = None
        key = (match_name.lower(), team_num, line)
        
        logger.info(f"Started monitoring: {match_name} | Team {team_num} Total {line}")
        
        while key in active_tracks:
            try:
                timestamp = datetime.now().strftime("%H:%M:%S")
                async with self.scraper:
                    # 1. Find Match
                    matches = await self.scraper.fetch_live_odds(sport_id=1)
                    match_info = next((m for m in matches if match_name.lower() in f"{m['home_team']} vs {m['away_team']}".lower()), None)
                    
                    if not match_info:
                        logger.warning(f"Match {match_name} not found in live feed.")
                        # After 30 mins of match not found, we might want to stop, but for now just keep waiting
                    else:
                        # 2. Fetch Deep Markets
                        game_id = match_info['match_id']
                        details = await self.scraper.fetch_game_details(game_id)
                        
                        # 3. Find Individual Total (IT1=Team1, IT2=Team2)
                        # Mirror IDs: IT1_OVER=(G=2, T=11/13), IT2_OVER=(G=62, T=11/13)
                        target_group = 2 if team_num == 1 else 62
                        current_odd = None
                        
                        for group in details.get("GE", []):
                            if group.get("G") == target_group:
                                for market in group.get("E", []):
                                    for event in market:
                                        if event.get("T") in [11, 13] and event.get("P") == line:
                                            current_odd = event.get("C")
                                            break
                                    if current_odd: break
                            if current_odd: break
                        
                        if current_odd:
                            if current_odd != last_odd:
                                icon = "🚀" if (last_odd and current_odd > last_odd) else "🎯"
                                alert = {
                                    "home_team": match_info['home_team'],
                                    "away_team": match_info['away_team'],
                                    "match_minute": match_info.get("match_minute", timestamp),
                                    "score": match_info['score'],
                                    "market": f"Team {team_num} Total Over {line}",
                                    "line": f"Odd Updated: {current_odd}",
                                    "rule_name": f"Dynamic Tracker {icon}"
                                }
                                await self.notifier.send(alert)
                                last_odd = current_odd
            except Exception as e:
                logger.error(f"Engine Error: {str(e)}")
            
            await asyncio.sleep(60) # 1 minute

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    # Expected: "Qarabag vs Shamakhi : track team_2 total 1.5"
    pattern = r"(.+?)\s?:\s?track team_([12]) total ([\d\.]+)"
    match = re.search(pattern, text, re.IGNORECASE)
    
    if match:
        match_name = match.group(1).strip()
        team_num = int(match.group(2))
        line = float(match.group(3))
        
        key = (match_name.lower(), team_num, line)
        if key in active_tracks:
            await update.message.reply_text(f"⚠️ Already tracking {match_name} Team {team_num} Over {line}")
            return

        await update.message.reply_text(f"✅ OK! I am now tracking {match_name} for Team {team_num} Total Over {line} every 5 minutes.")
        
        # Start background task
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        engine = OddTrackerEngine(bot_token, chat_id)
        
        task = asyncio.create_task(engine.monitor(match_name, team_num, line))
        active_tracks[key] = task
    else:
        await update.message.reply_text("I didn't quite get that. Use format:\nMatch Name : track team_2 total 1.5")

if __name__ == "__main__":
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        print("Set TELEGRAM_BOT_TOKEN in .env")
        exit(1)
        
    app = ApplicationBuilder().token(bot_token).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("🤖 Telegram OddNoty Bot is listening for commands...")
    app.run_polling()
