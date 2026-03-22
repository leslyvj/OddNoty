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

from aiohttp import web
import os

scraper = OneXBetScraper()
sofa = SofaScoreScraper()
analyst = LLMAnalyst()
store = ResearchStore()

async def health_check(request):
    return web.Response(text="OK")

async def run_research(match_id, home, away, update_or_query):
    """Helper to run/refresh research and send/update messages."""
    is_callback = isinstance(update_or_query, CallbackQueryHandler) # Not quite right, check type
    
    # We use context and update differently depending on if it's a message or callback
    if hasattr(update_or_query, 'message'):
        # It's an Update
        update = update_or_query
        target_msg = await update.message.reply_text(f"🔍 Refreshing research for **{home} vs {away}**...", parse_mode="Markdown")
    else:
        # It's a CallbackQuery
        query = update_or_query
        await query.answer("Refreshing stats...")
        target_msg = await query.message.reply_text(f"🔄 **Updating stats for {home} vs {away}...**", parse_mode="Markdown")

    try:
        sofa_id = await sofa.search_match(home, away)
        sofa_data = {}
        if sofa_id:
            sofa_data = await sofa.get_match_details(sofa_id)
            store.save_raw_data(match_id, "sofascore", sofa_data)
            
        matches = await scraper.get_live_matches()
        xb_match = find_match(home, away, matches)
        xb_data = {}
        if xb_match:
            xb_data = await scraper.get_match_odds(str(xb_match['match_id']))
            store.save_raw_data(match_id, "onexbet", xb_data)
            
        raw_combined = {"sofascore": sofa_data, "onexbet": xb_data}
        report = await analyst.generate_research_report(f"{home} vs {away}", raw_combined)
        store.save_report(match_id, report)
        
        # Success! Prepare UI
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Refresh Stats", callback_data=f"refresh:{match_id}")]
        ])
        
        await target_msg.delete()
        
        if len(report) > 4000:
            chunks = [report[i:i+4000] for i in range(0, len(report), 4000)]
            for i, chunk in enumerate(chunks):
                # Only add keyboard to the last chunk
                reply_markup = keyboard if i == len(chunks) - 1 else None
                if hasattr(update_or_query, 'message'):
                    await update_or_query.message.reply_text(chunk, parse_mode="Markdown", reply_markup=reply_markup)
                else:
                    await update_or_query.message.reply_text(chunk, parse_mode="Markdown", reply_markup=reply_markup)
        else:
            if hasattr(update_or_query, 'message'):
                await update_or_query.message.reply_text(report, parse_mode="Markdown", reply_markup=keyboard)
            else:
                await update_or_query.message.reply_text(report, parse_mode="Markdown", reply_markup=keyboard)
                
    except Exception as e:
        logger.error(f"Refresh error: {e}")
        await target_msg.edit_text(f"❌ Refresh failed: {str(e)}")

async def handle_freetext(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = getattr(update.message, 'text', '')
    if not text or text.startswith('/'): return
    
    intent = parse_track_command(text)
    if not intent:
        return
        
    home, away = intent['team1'], intent['team2']
    match_id = store.save_match(home, away)
    
    await run_research(match_id, home, away, update)

async def refresh_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    if not data.startswith("refresh:"): return
    
    match_id = data.split(":", 1)[1]
    match = store.get_match(match_id)
    if not match:
        await query.answer("Match data not found in database.", show_alert=True)
        return
        
    await run_research(match_id, match['home_team'], match['away_team'], query)

async def research_refresh_loop():
    while True:
        await asyncio.sleep(600)
        logger.info("Background research refresh triggered...")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🧠 **OddNoty Deep Research Bot**\n\n"
        "Just type a match name (e.g., `Arsenal vs Manchester City`) "
        "and I will generate a comprehensive pre-match research report with betting recommendations.\n\n"
        "Refresh the stats anytime using the button below the report!\n\n"
        "Priority data: **SofaScore**\n"
        "Odds & Markets: **1xBet**",
        parse_mode="Markdown"
    )

async def run_health_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Health check server started on port {port}")

def main():
    if not Config.TELEGRAM_BOT_TOKEN:
        logger.error("No TELEGRAM_BOT_TOKEN")
        return
    
    async def post_init(application):
        await application.bot.delete_webhook(drop_pending_updates=True)
        asyncio.create_task(research_refresh_loop())
        asyncio.create_task(run_health_server())
        
    app = ApplicationBuilder().token(Config.TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(refresh_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_freetext))
    
    logger.info("Deep Research Bot starting...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
