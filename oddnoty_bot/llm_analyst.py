import logging
import httpx
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
