import logging
import httpx
import json
from typing import Dict, Any, List
from oddnoty_bot.config import Config

logger = logging.getLogger(__name__)

class LLMAnalyst:
    def __init__(self):
        self.groq_api_key = Config.GROQ_API_KEY
        self.gemini_api_key = Config.GEMINI_API_KEY
        
    async def _call_llm(self, prompt: str, temperature: float = 0.2) -> str:
        """Helper to call Groq or Gemini based on availability."""
        if self.groq_api_key:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {self.groq_api_key}", "Content-Type": "application/json"}
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature
            }
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    if resp.status_code == 200:
                        return resp.json()["choices"][0]["message"]["content"]
                    else:
                        logger.error(f"Groq API error: {resp.status_code} - {resp.text}")
            except Exception as e:
                logger.error(f"Error calling Groq: {e}")

        if self.gemini_api_key:
            # Fallback to Gemini if Groq fails or is not available
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_api_key}"
            payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": temperature}}
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                    else:
                        logger.error(f"Gemini API error: {resp.status_code} - {resp.text}")
            except Exception as e:
                logger.error(f"Error calling Gemini: {e}")

        return "❌ LLM Service unavailable. Please check API keys."

    async def generate_research_report(self, match_name: str, raw_data: Dict[str, Any]) -> str:
        """Generates a deep pre-match research report using multi-source data."""
        system_prompt = f"""You are a professional betting analyst and sports data scientist. 
Do a deep pre-match research report for the football match [{match_name}]. 
Use ONLY the provided data and your internal high-quality knowledge base to synthesize a professional-grade report.

🎯 RESEARCH GOAL:
Provide a comprehensive, data-driven analysis that identifies value in betting markets (Team Totals, Asian Handicaps, Match Totals, etc.). The report must be structured PRECISELY as follows:

# {match_name} – Pre‑Match Research Report

## Executive summary
(A punchy 3-paragraph summary of the match, the key analytical gap between the teams, and the primary betting conclusion based on underlying data vs market prices.)

## A. Match context
(League position, importance of points for both sides, presence of derbies or rivalries, and environmental context.)

## B. Latest team news
(Injuries, suspensions, expected lineups, and the tactical impact of missing players. Use the 'lineups' data from SofaScore.)

## C. Team form and scoring profile
(Detailed breakdown of scored/conceded averages, home/away splits, scoring floor/ceiling, and frequency of BTTS/Over 2.5.)

## D. Tactical and style analysis
(A breakdown of how each team plays, their shot quality, defensive structure, and how these styles clash.)

## E. Market analysis
(Comparison of 1xBet odds with statistical probabilities. Discuss 1X2, Totals, and Asian Handicaps. Note any potential 'trap' lines or mispricings.)

## F. Historical matchup analysis
(Head-to-head history, specific trends at the home venue, and historical goal distributions between these sides.)

## G. Advanced indicators
(xG, xGA, shot quality, pass accuracy, play concentration, and any other relevant advanced metrics from the provided SofaScore stats.)

## H. Weather, pitch, and external conditions
(Impact of local conditions, stadium specifics, and any scheduling/travel factors.)

## I. Betting output – actionable angles
### 1) Best Team Total Over/Under lean
### 2) Best Asian Handicap lean
### 3) Confidence levels
### 4) What would invalidate these picks
### 5) Best line/price ranges to target
### 6) Final ranking of top 3 angles

## Limitations and missing data
(Note any data points that are estimated or where more info would be needed for a perfect assessment.)

---

👉 ANALYTICAL GUIDELINES:
- Be highly specific. Don't say "good form"; say "Orenburg defends better at home (1.09 conceded) while Spartak concede more away (1.80)".
- Use the provided JSON data (SofaScore statistics, 1xBet odds) to back every claim.
- Identify the 'Market consensus' from the 1xBet odds and compare it to the 'Statistical reality' from SofaScore.
- Tone: Professional, slightly technical, objective, and sharp.
"""

        # Truncate raw data if too large
        context_data = json.dumps(raw_data, indent=2)[:15000]
        
        prompt = f"Data acquired from SofaScore and 1xBet:\n\n{context_data}\n\nPlease generate the report now."
        
        return await self._call_llm(system_prompt + prompt)

    async def resolve_market(self, user_input: str, available_markets: List[str]) -> str:
        """Maps a user's natural language market request to the exact available market key."""
        prompt = f"""You are a sports betting expert. A user wants to track a specific market on 1xBet.
User Input: "{user_input}"
Available Markets: {available_markets}

Identify which available market best matches the user's request. 
Return ONLY the exact string of the market name from the list. If no match is even remotely close, return "UNKNOWN".

Answer:"""
        result = await self._call_llm(prompt, temperature=0.0)
        return result.strip().strip('"')

    async def parse_track_intent(self, user_text: str, available_markets: List[str]) -> Dict[str, Any]:
        """Uses LLM to extract structured tracking intent from free-text."""
        import json
        prompt = f"""You are a sports betting expert. A user wants to track a 1xBet market.
User Message: "{user_text}"
Available Markets: {available_markets}

Extract:
1. matched_market: Exact market name from the list (e.g., "Team 1 Total 1.5"). Return "UNKNOWN" if no match.
2. outcome: "Over" or "Under" or null.
3. target_odd: Float or null.

Return ONLY valid JSON.
JSON:"""
        result = await self._call_llm(prompt, temperature=0.0)
        try:
            # Basic cleanup for JSON
            cleaned = result.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[-1].split("```")[0].strip()
            return json.loads(cleaned)
        except Exception as e:
            logger.error(f"Failed to parse LLM intent JSON: {e} | Raw: {result}")
            return {"matched_market": "UNKNOWN", "outcome": None, "target_odd": None}

    async def summarize_hourly_movements(self, match_title: str, trajectory_data: Dict[str, List[Dict[str, Any]]]) -> str:
        """Generates a summary of all odd movements for a match over the last hour."""
        if not trajectory_data:
            return f"📊 **Hourly Summary for {match_title}**: No significant movements detected in the last hour."

        traj_str = ""
        for market, points in trajectory_data.items():
            traj_str += f"\nMarket: {market}\n"
            for pt in points:
                traj_str += f"  - T-{pt['mins_ago']}m: Odd {pt['odd']} ({pt['implied']})\n"

        prompt = f"""You are a professional betting analyst. Provide a brief, punchy summary of the odds movements for "{match_title}" over the last hour.
Focus on:
1. Significant drifts or crashes.
2. What this implies about the game (e.g., pressure rising, teams playing defensive).
3. Use friendly, understandable language.

Data:
{traj_str}

Summary:"""
        return await self._call_llm(prompt, temperature=0.7)

    async def analyze_raise(self, market: str, outcome: str, current_odd: float, diff_val: float, trajectory: list) -> str:
        """Analyses a specific raise in odds."""
        if not trajectory or len(trajectory) < 2:
            return "🤖 LLM Note: Movement detected."
            
        first_pt = trajectory[-1]
        time_span_mins = first_pt['mins_ago']
        start_odd = first_pt['odd']
        
        prompt = f"""Briefly explain this odds movement:
Market: {market} {outcome}
Move: {start_odd} -> {current_odd} (+{diff_val})
Timeframe: {time_span_mins} minutes

Keep it under 2 sentences. Sound like a sharp bookmaker.
Answer:"""
        return await self._call_llm(prompt, temperature=0.5)

    async def analyze(self, match_context: Dict[str, Any], odds_movement: Dict[str, Any], odds_store=None) -> str:
        """Full match analysis prompt (as previously defined but now live)."""
        team_h = match_context.get('home_team', 'Home')
        team_a = match_context.get('away_team', 'Away')
        score = match_context.get('score', '0-0')
        minute = match_context.get('minute', 0)
        match_id = str(match_context.get('match_id', ''))
        
        try:
            home_goals, away_goals = map(int, str(score).split('-'))
        except:
            home_goals, away_goals = 0, 0
            
        total_goals = home_goals + away_goals
        minute_num = int(minute) if str(minute).isdigit() else 0
        mins_remaining = max(90 - minute_num, 0)
        
        odds_str = ""
        filtered_markets = {}
        for market, outcomes in odds_movement.get('markets', {}).items():
            # Filter settled
            try:
                line_val = float(market.split()[-1])
                if total_goals > line_val: continue
            except: pass
                
            filtered_markets[market] = outcomes
            odds_str += f"\nMarket: {market}\n"
            for outcome, data in outcomes.items():
                odds_str += f"  - {outcome}: {data.get('odd')} (Implied: {data.get('implied_prob')}) | Velocity: {data.get('velocity_label')} | Diff: {data.get('diff', 0)}\n"
                
        trajectory_str = ""
        if odds_store and match_id:
            # Add trajectory for moving markets
            pass # (Simplified for this update)

        prompt = f"""Analyze this live game: {team_h} vs {team_a}
Score: {score} at {minute}'
Remaining: ~{mins_remaining} mins

Odds Data:
{odds_str}

Identify the best value trade based on movement velocity and game state. Use a professional yet accessible tone.
Recommendation:"""
        
        return await self._call_llm(prompt)
