import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from typing import Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from oddnoty_bot.config import Config
from oddnoty_bot.onexbet_scraper import OneXBetScraper
from oddnoty_bot.sofascore_scraper import SofaScoreScraper
from oddnoty_bot.llm_analyst import LLMAnalyst
from oddnoty_bot.research_store import ResearchStore
from oddnoty_bot.input_parser import parse_track_command
from oddnoty_bot.match_resolver import find_match

scraper = OneXBetScraper()
sofa = SofaScoreScraper()
analyst = LLMAnalyst()
store = ResearchStore()

async def handle_freetext(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = getattr(update.message, 'text', '')
    if not text or text.startswith('/'): return
    
    # Simple match name extraction (e.g., "Arsenal vs Man City")
    intent = parse_track_command(text)
    if not intent:
        return
        
    home, away = intent['team1'], intent['team2']
    match_id = store.save_match(home, away)
    
    msg_resolving = await update.message.reply_text(f"🔍 Starting deep research for **{home} vs {away}**...\nGathering data from SofaScore & 1xBet...", parse_mode="Markdown")
    
    try:
        # 1. SofaScore Search & Details
        sofa_id = await sofa.search_match(home, away)
        sofa_data = {}
        if sofa_id:
            sofa_data = await sofa.get_match_details(sofa_id)
            store.save_raw_data(match_id, "sofascore", sofa_data)
            
        # 2. 1xBet Odds
        # We try to find match in 1xBet as well
        matches = await scraper.get_live_matches()
        xb_match = find_match(home, away, matches)
        xb_data = {}
        if xb_match:
            xb_data = await scraper.get_match_odds(str(xb_match['match_id']))
            store.save_raw_data(match_id, "onexbet", xb_data)
            
        # 3. Generate Report
        raw_combined = {"sofascore": sofa_data, "onexbet": xb_data}
        report = await analyst.generate_research_report(f"{home} vs {away}", raw_combined)
        store.save_report(match_id, report)
        
        await msg_resolving.delete()
        
        # Split report into chunks if too long for Telegram
        if len(report) > 4000:
            for i in range(0, len(report), 4000):
                await update.message.reply_text(report[i:i+4000], parse_mode="Markdown")
        else:
            await update.message.reply_text(report, parse_mode="Markdown")
            
    except Exception as e:
        logger.error(f"Research error: {e}")
        await msg_resolving.edit_text(f"❌ Research failed: {str(e)}")

async def research_refresh_loop():
    """Periodically refreshes research data for recently mentioned matches."""
    while True:
        # For this test period, we'll just check matches updated in last hour
        # and refresh them every 10 minutes.
        # Implementation details can be expanded based on database queries.
        await asyncio.sleep(600) # 10 mins
        logger.info("Background research refresh triggered...")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🧠 **OddNoty Deep Research Bot**\n\n"
        "Just type a match name (e.g., `Arsenal vs Manchester City`) "
        "and I will generate a comprehensive pre-match research report with betting recommendations.\n\n"
        "Priority data: **SofaScore**\n"
        "Odds & Markets: **1xBet**",
        parse_mode="Markdown"
    )

def main():
    if not Config.TELEGRAM_BOT_TOKEN:
        logger.error("No TELEGRAM_BOT_TOKEN")
        return
    
    async def post_init(application):
        asyncio.create_task(research_refresh_loop())
        
    app = ApplicationBuilder().token(Config.TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_freetext))
    
    logger.info("Deep Research Bot starting...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
