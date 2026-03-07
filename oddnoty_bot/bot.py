import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

from oddnoty_bot.config import Config
from oddnoty_bot.onexbet_scraper import OneXBetScraper
from oddnoty_bot.odds_store import OddsStore
from oddnoty_bot.llm_analyst import LLMAnalyst
from oddnoty_bot.tracker import TrackerManager
from oddnoty_bot.input_parser import parse_track_command
from oddnoty_bot.match_resolver import find_match

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scraper = OneXBetScraper()
store = OddsStore()
analyst = LLMAnalyst()
trackers = TrackerManager()

async def poll_trackers(app):
    while True:
        poll_interval = getattr(Config, 'ONEXBET_POLL_INTERVAL', 120)
        await asyncio.sleep(poll_interval)
        all_tracks = trackers.get_all_trackers()
        if not all_tracks:
            continue
            
        # Refresh live matches cache to get current minute
        try:
            await scraper.get_live_matches()
        except Exception as e:
            logger.error(f"Failed to refresh live matches during poll: {e}")
            
        matches_to_fetch = set()
        user_tracks = []
        for uid, tlist in all_tracks.items():
            for t in tlist:
                if t.get('active'):
                    matches_to_fetch.add(t['match_id'])
                    user_tracks.append((uid, t))
                    
        for mid in matches_to_fetch:
            try:
                odds_data = await scraper.get_match_odds(mid)
                if odds_data:
                    store.snapshot(mid, odds_data)
            except Exception as e:
                logger.error(f"Error fetching odds for tracking {mid}: {e}")
                
        for uid, t in user_tracks:
            mid = t['match_id']
            market = t['market']
            outcome = t['outcome']
            movement = store.get_movement(mid)
            m_data = movement.get('markets', {}).get(market, {})
            if outcome:
                outcomes_to_check = [outcome]
            else:
                outcomes_to_check = list(m_data.keys())
            
            # Pull current minute from the live cache
            match_context = scraper.live_matches_cache.get(mid)
            if match_context:
                title = f"{match_context['home_team']} vs {match_context['away_team']}"
                minute = match_context.get('minute', '?')
                match_score = match_context.get('score', '?')
            else:
                title = mid
                minute = '?'
                match_score = '?'
                
            has_movement = False
            lines = []
            
            for oc in outcomes_to_check:
                o_data = m_data.get(oc)
                if not o_data:
                    continue
                    
                diff_val = o_data.get('diff', 0.0)
                current_odd = o_data['odd']
                
                try:
                    current_implied = float(str(o_data['implied_prob']).strip('%'))
                except:
                    current_implied = 0.0
                
                if diff_val != 0.0:
                    has_movement = True
                    prev_odd = round(current_odd - diff_val, 3)
                    prev_implied = round((1 / prev_odd) * 100, 1) if prev_odd > 0 else 0
                    lines.append(
                        f"{oc}: {prev_odd} → {current_odd}  {o_data['movement_icon']} ({diff_val:+.2f})  [{o_data['velocity_label']}]\n"
                        f"Implied: {prev_implied}% → {current_implied}%"
                    )
                else:
                    lines.append(
                        f"{oc}: {current_odd}  ─  [STABLE]\n"
                        f"Implied: {current_implied}%"
                    )
            
            if lines:
                header = f"📊 {title}\n⏱ {minute}' | Score: {match_score} | {market}"
                if has_movement:
                    rep = header + "\n" + "\n".join(lines)
                else:
                    rep = header + "\n" + "\n".join(lines) + "\n📡 No movement this cycle."
                    
                try:
                    await app.bot.send_message(chat_id=uid, text=rep)
                except Exception as e:
                    logger.error(f"Failed to send tracking update: {e}")

async def handle_freetext(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = getattr(update.message, 'text', '')
    if not text or text.startswith('/'): return
    
    intent = parse_track_command(text)
    if not intent:
        return # Ignore random chatter
        
    matches = list(scraper.live_matches_cache.values())
    if not matches:
        matches = await scraper.get_live_matches()
        
    match = find_match(intent['team1'], intent['team2'], matches)
    
    if not match:
        await update.message.reply_text(f"❌ Couldn't find a live match for {intent['team1']} vs {intent['team2']}.")
        return
        
    match_id = str(match['match_id'])
    home_team = match['home_team']
    away_team = match['away_team']
    
    odds_data = await scraper.get_match_odds(match_id)
    if not odds_data or not odds_data.get('markets'):
        await update.message.reply_text("❌ No odds currently available for this match.")
        return
        
    store.snapshot(match_id, odds_data)
    available_markets = list(odds_data.get('markets', {}).keys())
    
    # Use market_group from the intent (already derived by input_parser)
    market_group = intent.get('market_group')
    target_market_prefix = market_group
    
    if target_market_prefix and intent['market_line'] is not None:
        target_market_prefix += f" {intent['market_line']}"
            
    matched_market = None
    if target_market_prefix:
        for am in available_markets:
            if am == target_market_prefix or am.startswith(f"{target_market_prefix} "):
                matched_market = am
                break
                
    if not matched_market:
        # Filter suggestions to only show markets from the relevant group
        if market_group:
            relevant = [m for m in available_markets if m.startswith(market_group)]
        else:
            relevant = available_markets
        suggested = " / ".join(relevant[:6]) if relevant else " / ".join(available_markets[:5])
        if not suggested: suggested = "None available right now"
        await update.message.reply_text(
            f"Got {home_team} vs {away_team} but couldn't identify the market — did you mean: {suggested}?"
        )
        return
        
    market_odds = odds_data['markets'][matched_market]
    over_odd = market_odds.get('Over', market_odds.get('1', 'N/A'))
    under_odd = market_odds.get('Under', market_odds.get('2', 'N/A'))
    
    msg_text = f"Found: {home_team} vs {away_team} | Tracking {matched_market} | Over: {over_odd} | Under: {under_odd}"
    
    context.user_data['pending_tracker'] = {
        "match_id": match_id,
        "market": matched_market,
        "outcome": intent['side'] # can be None
    }
    
    keyboard = [
        [InlineKeyboardButton("✅ Confirm", callback_data="confirm_track"),
         InlineKeyboardButton("❌ Cancel", callback_data="cancel_track")]
    ]
    await update.message.reply_text(msg_text, reply_markup=InlineKeyboardMarkup(keyboard))

async def live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ Fetching live matches from 1xBet...")
    
    matches = await scraper.get_live_matches()
    
    if not matches:
        await msg.edit_text("❌ No live matches found at the moment.")
        return
        
    text = "⚽ **Live 1xBet Matches:**\n\n"
    keyboard = []
    
    for i, m in enumerate(matches[:15], 1):
        text += f"{i}. {m['home_team']} vs {m['away_team']} | {m['score']} | {m['minute']}' | {m['league']}\n"
        # store in context args for index mapping
        context.user_data[str(i)] = m['match_id']
        keyboard.append([InlineKeyboardButton(f"📊 Odds {i}", callback_data=f"odds_{i}")])
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    await msg.edit_text(text, reply_markup=reply_markup)

async def odds_command(update: Update, context: ContextTypes.DEFAULT_TYPE, match_id=None, msg_id=None):
    if not match_id:
        if not context.args:
            await update.message.reply_text("Usage: /odds <number>")
            return
        index = context.args[0]
        match_id = context.user_data.get(index)
        
    if not match_id:
        await update.message.reply_text("❌ Match not found. Run /live first.")
        return
        
    odds_data = await scraper.get_match_odds(match_id)
    store.snapshot(match_id, odds_data)
    
    movement = store.get_movement(match_id)
    
    text = f"📊 **Odds for Match {match_id}**\n\n"
    for market, outcomes in movement.get("markets", {}).items():
        text += f"*{market}*\n"
        for outcome, data in outcomes.items():
            icon = data['movement_icon']
            diff = f"{data['diff']:+0.2f}" if data['diff'] else ""
            text += f"  {outcome}: {data['odd']} {icon} {diff}\n"
            
    text += "\nWait 2 mins and request again to see movement arrows!"
    
    keyboard = [
        [InlineKeyboardButton("🤖 Analyze", callback_data=f"analyze_{match_id}")],
        [InlineKeyboardButton("🎯 Track an odd", callback_data=f"track_{match_id}")]
    ]
    
    if msg_id:
        await context.bot.edit_message_text(text, chat_id=update.effective_chat.id, message_id=msg_id, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        text_r = await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("odds_"):
        index = data.split("_")[1]
        match_id = context.user_data.get(index)
        await odds_command(update, context, match_id, query.message.id)
    elif data.startswith("analyze_"):
        match_id = data.split("_")[1]
        match_context = {"home_team": "Home", "away_team": "Away", "score": "?", "minute": "?"} 
        for m in scraper.live_matches_cache.values():
            if str(m.get("match_id")) == match_id:
                match_context = m
                break
                
        movement = store.get_movement(match_id)
        
        analysis = await analyst.analyze(match_context, movement, store)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=analysis)
    elif data == "confirm_track":
        t_args = context.user_data.get('pending_tracker')
        if t_args:
            trackers.add_tracker(update.effective_chat.id, t_args['match_id'], t_args['market'], t_args['outcome'])
            await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=query.message.id, text=f"✅ Now tracking {t_args['market']}!")
        else:
            await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=query.message.id, text="❌ Tracker session expired.")
    elif data == "cancel_track":
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=query.message.id, text="❌ Tracking cancelled.")
    elif data.startswith("stop_"):
        idx = int(data.split("_")[1])
        uid = update.effective_chat.id
        user_trackers = trackers.get_trackers(uid)
        if 0 <= idx < len(user_trackers):
            removed = user_trackers[idx]
            market_name = removed.get('market', '?')
            match_id = removed.get('match_id', '?')
            # Remove by index
            trackers.trackers[uid].pop(idx)
            # Get match name from cache
            mc = scraper.live_matches_cache.get(match_id)
            title = f"{mc['home_team']} vs {mc['away_team']}" if mc else match_id
            await context.bot.edit_message_text(chat_id=uid, message_id=query.message.id, text=f"🛑 Stopped tracking {market_name} on {title}.")
        else:
            await context.bot.edit_message_text(chat_id=uid, message_id=query.message.id, text="❌ Tracker not found.")
    elif data == "stopall":
        uid = update.effective_chat.id
        trackers.clear_all(uid)
        await context.bot.edit_message_text(chat_id=uid, message_id=query.message.id, text="🛑 All trackers stopped.")

async def list_trackers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_chat.id
    user_trackers = trackers.get_trackers(uid)
    active = [t for t in user_trackers if t.get('active')]
    
    if not active:
        await update.message.reply_text("📭 No active trackers. Type a match name to start tracking!")
        return
    
    text = "📋 **Your Active Trackers:**\n\n"
    keyboard = []
    for i, t in enumerate(active):
        mc = scraper.live_matches_cache.get(t['match_id'])
        title = f"{mc['home_team']} vs {mc['away_team']}" if mc else t['match_id']
        outcome_str = f" ({t['outcome']})" if t.get('outcome') else ""
        text += f"{i+1}. {title} — {t['market']}{outcome_str}\n"
        keyboard.append([InlineKeyboardButton(f"❌ Stop #{i+1}", callback_data=f"stop_{i}")])
    
    keyboard.append([InlineKeyboardButton("🛑 Stop All", callback_data="stopall")])
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def stopall_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_chat.id
    trackers.clear_all(uid)
    await update.message.reply_text("🛑 All trackers stopped. You can start new ones anytime!")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to the 1xBet Live Bot!\n\n"
        "Commands:\n"
        "/live — Browse live matches\n"
        "/trackers — View & stop active trackers\n"
        "/stopall — Stop all trackers\n\n"
        "Or just type:\n"
        "Bucheon vs Daejeon : track total 0.5"
    )

import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        active = sum(len(v) for v in trackers.get_all_trackers().values())
        self.wfile.write(f"OddNoty Bot alive | {active} active trackers".encode())
    def log_message(self, format, *args):
        pass  # Suppress request logs

def start_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info(f"Health server on port {port}")
    server.serve_forever()

def main():
    if not Config.TELEGRAM_BOT_TOKEN:
        logger.error("No TELEGRAM_BOT_TOKEN")
        return
    
    # Start health check server for Render
    threading.Thread(target=start_health_server, daemon=True).start()

    async def post_init(application):
        """Called after the Application has been initialized — safe to create tasks here."""
        asyncio.create_task(poll_trackers(application))
        
    app = ApplicationBuilder().token(Config.TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("live", live))
    app.add_handler(CommandHandler("odds", odds_command))
    app.add_handler(CommandHandler("trackers", list_trackers))
    app.add_handler(CommandHandler("stopall", stopall_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_freetext))
    
    logger.info("Bot starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
