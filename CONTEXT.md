# 1xBet Live Betting Bot — Context & Architecture

---

## Project Goal

A Telegram bot that scrapes **live football matches and odds from 1xBet**, feeds the data to a **free-tier LLM**, and helps the user decide which market to bet on based on odds values, odds movement, implied probabilities, and market contradictions — all in real time.

---

## Current State

| Component | Status |
|---|---|
| 1xBet scraping | ✅ Working |
| Telegram bot | ✅ Working |
| Odds movement tracking | 🔲 To build |
| LLM analysis | 🔲 To build |
| Odds tracker / alerts | 🔲 To build |

---

## Free-Tier LLM Decision

| Provider | Model | Free Tier | Rate Limit | Verdict |
|---|---|---|---|---|
| **Groq** | `llama-3.1-8b-instant` | ✅ Yes | 30 req/min, 14,400/day | ✅ **Primary** — fastest free inference |
| **Google Gemini** | `gemini-1.5-flash` | ✅ Yes | 15 req/min, 1500/day | ✅ **Fallback** — better reasoning |
| Mistral | `open-mistral-7b` | ✅ Yes | 1 req/sec | Backup only |

**Decision: Groq primary, Gemini Flash fallback.**
- Groq: ~200 tokens/sec, no credit card, get key at `console.groq.com`
- Gemini Flash: stronger numerical reasoning, get key at `aistudio.google.com`
- If Groq returns 429 (rate limit), automatically retry with Gemini

---

## What 1xBet Scraping Gives Us

### Per Match (from live list)
```
match_id        — internal 1xBet ID, used for all subsequent calls
team1 / team2   — home and away team names
score           — current live score
minute          — match minute
league          — competition name
```

### Per Match (from detail endpoint)
```
OVER/UNDER MARKETS
  Over/Under 0.5  — odd for over, odd for under
  Over/Under 1.5
  Over/Under 2.5
  Over/Under 3.5

ASIAN HANDICAP
  Current handicap line (e.g. -0.75)
  Home odds / Away odds

BOTH TEAMS TO SCORE
  BTTS Yes / BTTS No odds

NEXT GOAL (if available)
  Home / Away / No goal odds

CORNERS (if available)
  Over/Under corners line + odds
```

### Derived (computed in Python)
```
implied_probability  = 1 / odd * 100  (for each selection)
movement             = current_odd - previous_odd  (stored every 2 mins)
movement_speed       = abs(movement) / time_elapsed  (fast move = sharp signal)
market_suspended     = bool  (True if odd = 0 or market missing mid-game)
```

---

## System Architecture

```
┌──────────────────────────────────────────────────┐
│              TELEGRAM BOT (bot.py)               │
│  /live  /odds <n>  /analyze <n>  /track  /help  │
└───────────────────┬──────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
┌───────────────┐      ┌─────────────────┐
│  1xBet        │      │  LLM Analyst    │
│  Scraper      │      │ (llm_analyst.py)│
│               │      │                 │
│ httpx REST    │      │ Groq API        │
│ live list     │      │ llama-3.1-8b    │
│ match detail  │      │                 │
│ odds parser   │      │ Gemini Flash    │
│               │      │ (fallback)      │
└──────┬────────┘      └─────────────────┘
       │
       ▼
┌──────────────────────────┐
│   Odds History Store     │
│   dict: match_id →       │
│   list of OddsSnapshot   │
│   (timestamp + all odds) │
│   kept in memory         │
│   max 30 snapshots/match │
└──────────────────────────┘
       │
       ▼
┌──────────────────────────┐
│   Tracker Engine         │
│   per-user trackers      │
│   polls every 2 mins     │
│   fires alert on target  │
└──────────────────────────┘
```

---

## File Structure

```
oddnoty_bot/
│
├── bot.py                  # Telegram entry point, all command handlers
├── config.py               # Env vars, API keys, poll intervals
├── onexbet_scraper.py      # 1xBet live list + odds fetcher + parser
├── odds_store.py           # In-memory odds history, movement calculation
├── llm_analyst.py          # Groq/Gemini calls + prompt templates
├── tracker.py              # Per-user odds trackers + alert engine
├── requirements.txt
└── CONTEXT.md              # This file
```

---

## Data Flow

### Startup
```
bot.py post_init()
  └── onexbet.start()
        └── fetch live match list → cache
        └── asyncio task: refresh live list every 2 mins
  └── tracker_manager.start()
        └── asyncio task: poll tracked odds every 2 mins
```

### /live Command
```
User: /live
  └── onexbet.get_live_matches()     ← cached list, instant
  └── Display numbered match list
        1. Team A vs Team B | 0-0 | 44' | Premier League
        2. Team C vs Team D | 1-0 | 67' | La Liga
        ...
  └── Inline buttons: [📊 1] [📊 2] [📊 3] ... per match
```

### /odds `<n>` Command
```
User: /odds 2   OR taps [📊 2]
  └── onexbet.get_match_odds(match_id)
        └── Fetch detail endpoint for that match
        └── Parse Over/Under, Asian HDP, BTTS, corners
        └── odds_store.snapshot(match_id, odds)   ← store for movement tracking
  └── Display odds table with movement arrows
        Over 0.5  →  1.35  (📉 was 1.42)
        Over 1.5  →  1.85  (📈 was 1.78)
        Over 2.5  →  2.60  (─ no change)
        ...
  └── Inline buttons: [🤖 Analyze] [🎯 Track an odd]
```

### /analyze `<n>` Command
```
User: /analyze 2   OR taps [🤖 Analyze]
  └── Build LLM payload:
        - match context (teams, score, minute, league)
        - all current odds
        - odds movement history (last 3 snapshots)
        - implied probabilities (computed)
        - any suspended markets (flagged)
  └── llm_analyst.analyze(payload)
        └── POST to Groq API
        └── Return market reading + bet recommendation
  └── Send analysis to user
  └── Button: [🎯 Track recommended odd]
```

### /track Flow
```
User taps [🎯 Track an odd]
  └── Bot shows available odds as buttons
  └── User selects odd (e.g. Over 1.5 currently at 1.85)
  └── Bot asks: "Alert me when it reaches?"
  └── User replies: 2.10
  └── Tracker set: poll every 2 mins, alert when Over 1.5 ≥ 2.10
```

---

## Odds History Store Design

Every time odds are fetched for a match, a snapshot is saved:

```python
OddsSnapshot:
  timestamp:   datetime
  match_id:    str
  odds:        dict   # market → label → float
               # e.g. {"Over/Under 1.5": {"Over": 1.85, "Under": 1.95}}
```

Movement is computed at display time:
```python
movement = current_snapshot.odds[market][label]
         - previous_snapshot.odds[market][label]

# Display:
# +0.15  →  📈 (odd drifting = market less confident = potential value)
# -0.23  →  📉 (odd shortening = money coming in = market conviction)
# 0.00   →  ─  (stable)
```

Max 30 snapshots per match kept in memory. Older ones dropped automatically.

---

## LLM Analysis — What It Reasons About

The LLM receives a structured JSON payload and reasons about:

### 1. Implied Probability Reading
Converts every odd to implied probability and flags when the market is pricing something above 70% confidence — that is where the bookmaker has conviction.

### 2. Market Contradiction Detection
If `Over 1.5` implies 65% chance of 2+ goals but `BTTS No` implies 55% chance of a clean sheet — these contradict. The LLM flags this as a potential mispricing in one of the two markets.

### 3. Odds Movement Interpretation
- Odd shortening fast (e.g. -0.30 in 4 mins with no goal) = sharp money signal
- Odd drifting (e.g. +0.20) = market pulling back = potential value on that selection
- Suspension mid-game = something happening on pitch (goal being reviewed, VAR)

### 4. Score + Minute Context
The LLM knows that market behavior patterns differ by game state:
- 0-0 at 70'+ → Over 0.5 getting expensive fast → window closing
- 1-0 at 60' → Asian handicap on losing team often drifts → potential value
- 2-0 scoreline → BTTS No shortening → logical but check if already fully priced in

### 5. Asian Handicap Line Movement
If the handicap shifts (e.g. from -0.5 to -0.75 for home team) it means the market has moved conviction toward the home team. LLM flags this as a directional signal.

### 6. Value Flag
LLM compares implied probability to rough statistical baselines:
- Over 0.5 implied at 55% but game is 0-0 at 75' → statistically should be 80%+ → value
- BTTS Yes implied at 40% but both teams averaging 2.3 goals per game → worth flagging

---

## LLM Prompt Strategy

```
System prompt:
  "You are a professional football live betting analyst.
   You receive live 1xBet odds data with movement history.
   Your job is to identify value, spot market contradictions,
   and interpret odds movement as sharp money signals.
   Always give a specific bet recommendation with a 🟢/🟡/🔴 signal.
   Temperature: 0.3 — factual, consistent, no hallucination."

User prompt contains:
  - Match: teams, score, minute, league
  - Odds table: all markets + current odds
  - Movement: last 3 snapshots with timestamps
  - Implied probabilities: computed per selection
  - Suspended markets: flagged with timestamp
  - Derived: fastest-moving odd in last 5 mins
```

---

## Telegram Bot Commands

| Command | Description |
|---|---|
| `/live` | Numbered list of all live 1xBet matches |
| `/odds <n>` | Full odds table for match n with movement arrows |
| `/analyze <n>` | LLM market analysis for match n |
| `/track` | Set an odds tracker (alert when target reached) |
| `/trackers` | List your active trackers |
| `/cancel` | Cancel a tracker |
| `/help` | Command list |

---

## Inline Button Flow

```
/live
  → Numbered match list
  → Buttons: [📊 1] [📊 2] [📊 3] ...

Tap [📊 2]
  → Full odds table with movement arrows
  → Buttons: [🤖 Analyze] [🎯 Track an odd]

Tap [🤖 Analyze]
  → LLM market reading + recommended bet
  → Button: [🎯 Track recommended odd]

Tap [🎯 Track an odd]
  → Bot shows odds as buttons
  → User picks one
  → User sets target value
  → Tracker confirmed ✅
  → Alert fires when target hit
```

---

## Rate Limiting & Protection

### LLM side
- `/analyze` has **30s per-user cooldown**
- If Groq returns 429 → auto-retry with Gemini Flash
- Token budget per call: ~400 input + 800 output (well within free limits)

### 1xBet side
- Live list refresh: every **2 minutes**
- Odds fetch: on-demand per user request + every 2 mins for tracked matches
- Add random jitter of ±15s to all poll intervals to avoid pattern detection
- Rotate User-Agent headers on each request
- If 403 returned: back off 60s, log warning, try again

### Telegram side
- Auto-split messages at 4000 chars
- Max 5 active trackers per user

---

## Environment Variables

```bash
TELEGRAM_BOT_TOKEN=xxx        # from @BotFather
GROQ_API_KEY=xxx              # from console.groq.com (free, no card)
GEMINI_API_KEY=xxx            # from aistudio.google.com (free)
ONEXBET_POLL_INTERVAL=120     # seconds between live list refreshes
```

---

## Setup Checklist

```
1. pip install python-telegram-bot httpx
2. Get Groq API key  → console.groq.com → "Create API Key"
3. Get Gemini key    → aistudio.google.com → "Get API key"
4. Set env vars in .env or shell
5. Confirm 1xBet scraper returns live matches: run onexbet_scraper.py standalone
6. Check odds parser output — verify Over/Under and Asian HDP fields populate
7. Run bot, use /live, confirm numbered match list appears
8. Use /odds 1, confirm odds table with movement arrows appears
9. Use /analyze 1, confirm LLM response is coherent
10. Set a tracker, wait for poll cycle, confirm alert fires
```

---

## Known Risks

| Risk | Impact | Mitigation |
|---|---|---|
| 1xBet API endpoint changes | Scraper returns empty | Log raw response on failure; keep parser decoupled |
| 1xBet 403 / Cloudflare block | All scraping fails | Add jitter, rotate User-Agent, back-off on 403 |
| Groq rate limit hit | Analysis fails | Auto-fallback to Gemini Flash |
| LLM reasoning error | Bad bet advice | Low temperature (0.3), pass hard numbers not descriptions |
| Odds store memory growth | RAM usage over hours | Cap at 30 snapshots per match, purge expired matches |
| Tracker misses target | User does not get alert | Poll every 2 mins max; log every poll result |

---

## What Is NOT in Scope (Yet)

- SQLite persistence for trackers across restarts
- Multi-user admin controls
- Historical odds database
- Automated bet placement (out of scope entirely)