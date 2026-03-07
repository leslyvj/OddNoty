import logging
from typing import Dict, Any
from oddnoty_bot.config import Config

logger = logging.getLogger(__name__)

class LLMAnalyst:
    def __init__(self):
        self.groq_api_key = Config.GROQ_API_KEY
        self.gemini_api_key = Config.GEMINI_API_KEY
        
        if not self.groq_api_key and not self.gemini_api_key:
            return "❌ LLM keys not configured. Check config."
            
    async def analyze_raise(self, market: str, outcome: str, current_odd: float, diff_val: float, trajectory: list) -> str:
        """Generates a brief LLM note on how long it took an odd to reach its current raised level."""
        if not trajectory or len(trajectory) < 2:
            return "🤖 LLM Note: Not enough historical trajectory to measure the time span of this raise."
            
        # The trajectory is sorted latest to oldest by mins_ago
        # e.g., [{'mins_ago': 0.0, 'odd': 1.8}, {'mins_ago': 0.5, 'odd': 1.7}, ...]
        first_pt = trajectory[-1]
        last_pt = trajectory[0]
        
        time_span_mins = first_pt['mins_ago'] - last_pt['mins_ago']
        if time_span_mins <= 0:
            time_span_mins = 0.5 # fallback assumption of 1 polling cycle
            
        start_odd = first_pt['odd']
        
        # Assess speed of the odd growth
        speed = diff_val / time_span_mins
        if speed > 0.15:
            pace = "extremely rapidly (sharp money movement)"
        elif speed > 0.05:
            pace = "steadily"
        else:
            pace = "slowly over time"
            
        return f"🤖 **LLM Note**: Odd climbed from **{start_odd} to {current_odd}**. It took approx **{time_span_mins:.1f} mins** to reach this level, moving {pace}."

    async def analyze(self, match_context: Dict[str, Any], odds_movement: Dict[str, Any], odds_store=None) -> str:
        team_h = match_context.get('home_team', 'Home')
        team_a = match_context.get('away_team', 'Away')
        score = match_context.get('score', '0-0')
        minute = match_context.get('minute', 0)
        match_id = str(match_context.get('match_id', ''))
        
        # Calculate Game State
        try:
            home_goals, away_goals = map(int, str(score).split('-'))
        except:
            home_goals, away_goals = 0, 0
            
        total_goals = home_goals + away_goals
        minute_num = int(minute) if str(minute).isdigit() else 0
        mins_remaining = max(90 - minute_num, 0)
        
        # Specific states based on total goals and time
        if total_goals == 0 and minute_num >= 65:
            state = "GOALLESS_LATE_GAME"
            urgency = "HIGH"
        elif total_goals == 0 and minute_num >= 45:
            state = "GOALLESS_SECOND_HALF"
            urgency = "ELEVATED"
        elif home_goals == away_goals:
            state = "DRAW_LATE_GAME" if minute_num >= 70 else "DRAW"
            urgency = "HIGH" if minute_num >= 70 else "NORMAL"
        else:
            state = "LEAD_LATE_GAME" if minute_num >= 70 else "LEAD"
            urgency = "HIGH" if minute_num >= 70 and abs(home_goals - away_goals) == 1 else "NORMAL"
            
        game_state = {
            "score_home": home_goals,
            "score_away": away_goals,
            "minute": minute_num,
            "goals_scored": total_goals,
            "minutes_remaining": mins_remaining,
            "state": state,
            "urgency": urgency
        }
        
        # Format the data for the prompt
        odds_str = ""
        filtered_markets = {}
        for market, outcomes in odds_movement.get('markets', {}).items():
            try:
                line_val = float(market.split()[-1])
                if total_goals > line_val:
                    continue  # Market is settled
            except:
                pass
                
            filtered_markets[market] = outcomes
            odds_str += f"\nMarket: {market}\n"
            for outcome, data in outcomes.items():
                odds_str += f"  - {outcome}: {data.get('odd')} (Implied: {data.get('implied_prob')}) | Velocity: {data.get('velocity_label')} | Diff: {data.get('diff', 0)} {data.get('movement_icon')}\n"
                
        # Build trajectory strings for markets with movement
        trajectory_str = ""
        if odds_store and match_id:
            for market, outcomes in filtered_markets.items():
                for outcome, data in outcomes.items():
                    if data.get('diff', 0) != 0:
                        traj = odds_store.get_trajectory(match_id, market, outcome, n=6)
                        if len(traj) >= 2:
                            trajectory_str += f"\nTrajectory: {market} {outcome}\n"
                            for pt in traj:
                                trajectory_str += f"  T-{pt['mins_ago']}min: {pt['odd']} ({pt['implied']})\n"
                
        # The new prompt
        prompt = f"""You are a live football betting analyst. For each match you receive:
- Game state (score, minute, urgency label)
- Odds table with implied probabilities already calculated
- Movement data with velocity labels
- Trajectory data showing historical snapshots

When evaluating movement signals, follow this logic:

Step 1 — Filter settled markets
  Remove any Over/Under line where goals_scored already exceeds the line.
  These markets are closed and irrelevant.

Step 2 — Cross-reference Under crashes with Over value
  If Under X.X is crashing (📉 FAST MOVE), the real trade is Over X.X.
  Report the Over odd, not the Under movement.

Step 2B — Trajectory Analysis
  You will receive up to 6 historical snapshots for markets that moved.
  Calculate total_move = first_odd - last_odd
  Calculate time_span = first_mins_ago (in minutes)
  Report as: "Moved X.XX in Y minutes"
  
  Classify trajectory:
    - Consistent direction entire window = TREND (strongest signal)
    - Accelerating (moves getting bigger each step) = ACCELERATION (sharpest signal)
    - Reversal in last snapshot = PULLBACK (potential entry point)
    - Random up/down = NOISE (no signal)

Step 3 — Sanity check remaining goals needed
  goals_needed = target_line - goals_scored
  if mins_remaining > 0 and goals_needed / mins_remaining > 0.10: mark as UNLIKELY, do not recommend.
  Also validate goals_needed > mins_remaining * 0.08: if so, flag as UNLIKELY.

Step 4 — Pick the single highest-confidence trade
  The best trade is where: movement aligns + implied prob is between 55-80%
  + goals_needed is physically realistic + trajectory confirms direction.

Rules:
- Never say "wait and see" — always give a concrete position.
- Never say "the fastest moving line" — always name the exact market, the exact current odd, and the exact entry condition.
- Always reference specific odd values and implied probabilities.
- Your final recommendation must contain: market name, current odd, implied probability, and the entry condition. No generic statements.
- Before recommending any Over market, validate goals_needed and minutes_remaining. If unrealistic, DO NOT recommend it.
- If movement is ─ on all markets, say "no signal detected" and explain why.
- Temperature: 0.2 — factual, no creativity.

--- MATCH DATA ---
Teams: {team_h} vs {team_a}
State: {game_state['state']}, Urgency: {game_state['urgency']}
{game_state['goals_scored']} goals scored, ~{game_state['minutes_remaining']} mins left.
Score: {score} at {minute}'

--- ODDS DATA ---
{odds_str}

--- TRAJECTORY DATA ---
{trajectory_str if trajectory_str else "No trajectory available yet (first snapshot)."}
"""
        
        # Stub the LLM response for local testing purposes to demonstrate the new logic
        # In the full impl, this would POST `prompt` to Groq
        mock_response = f"🤖 **Value Analysis for {team_h} vs {team_a}**\n\n"
        mock_response += f"**1. Game State:** This is a {state} with {urgency} urgency. With ~{mins_remaining} minutes left and {total_goals} goals already scored, the dynamic is critical.\n"
        
        has_fast_moving = False
        fast_markets = []
        target_market = ""
        target_odd = ""
        target_implied = ""
        
        for market, outcomes in filtered_markets.items():
             for outcome, data in outcomes.items():
                 if 'FAST MOVE' in data.get('velocity_label', ''):
                     fast_markets.append(f"{market} {outcome} ({data.get('movement_icon')})")
                     has_fast_moving = True
                     
                     # Check if it's an Under crashing
                     if outcome == "Under" and "📉" in data.get('movement_icon', ''):
                         over_data = outcomes.get("Over", {})
                         if over_data:
                             target_market = f"{market} Over"
                             target_odd = over_data.get('odd')
                             target_implied = over_data.get('implied_prob')
                     elif not target_market:
                         target_market = f"{market} {outcome}"
                         target_odd = data.get('odd')
                         target_implied = data.get('implied_prob')

        # Build trajectory summary for mock response
        traj_summary = ""
        if trajectory_str:
            traj_summary = "\n**2B. Trajectory:** "
            # Simple classification from the trajectory data
            for market, outcomes in filtered_markets.items():
                for outcome, data in outcomes.items():
                    if data.get('diff', 0) != 0 and odds_store and match_id:
                        traj = odds_store.get_trajectory(match_id, market, outcome, n=6)
                        if len(traj) >= 3:
                            first_odd = traj[0]['odd']
                            last_odd = traj[-1]['odd']
                            total_move = round(first_odd - last_odd, 3)
                            time_span = traj[0]['mins_ago']
                            
                            # Check if all moves are in same direction
                            diffs = [traj[i]['odd'] - traj[i+1]['odd'] for i in range(len(traj)-1)]
                            all_down = all(d > 0 for d in diffs)
                            all_up = all(d < 0 for d in diffs)
                            
                            if all_down or all_up:
                                direction = "shortening" if all_down else "drifting"
                                # Check acceleration
                                abs_diffs = [abs(d) for d in diffs]
                                accelerating = all(abs_diffs[i] <= abs_diffs[i+1] for i in range(len(abs_diffs)-1)) if len(abs_diffs) > 1 else False
                                label = "TREND + ACCELERATION" if accelerating else "TREND"
                                traj_summary += f"{market} {outcome} moved {abs(total_move):.3f} in {time_span:.0f} mins ({direction}). Pattern: {label}.\n"
                            else:
                                traj_summary += f"{market} {outcome} moved {abs(total_move):.3f} in {time_span:.0f} mins. Pattern: NOISE.\n"
                            break  # Only report the first meaningful trajectory
                if traj_summary != "\n**2B. Trajectory:** ":
                    break
                     
        if has_fast_moving:
            mock_response += f"**2. Market Reaction:** Panic detected in {', '.join(fast_markets)}. The velocity indicates sharp money or a rapid algorithmic adjustment.\n"
            if traj_summary:
                mock_response += traj_summary
            mock_response += "**3. Contradictions:** [Simulated] No obvious contradictions in the active totals.\n"
            mock_response += f"**4. Strategy:** Fast movement on the Under provides an opening for the Over.\n"
            mock_response += f"🟢 **Signal:** {target_market} is at {target_odd} ({target_implied} implied). Sharp money crashed the Under recently. If {target_market} holds above 1.65, this is the entry window.\n"
        else:
            mock_response += "**2. Market Reaction:** No signal detected. All lines trace `─` (stable). Velocity is STABLE.\n"
            if traj_summary:
                mock_response += traj_summary
            mock_response += "**3. Contradictions:** None visible on static lines.\n"
            mock_response += "**4. Strategy:** No statistical edges found on a stable board.\n"
            mock_response += "🔴 **Signal:** No action recommended until movement begins.\n"
            
        return mock_response
