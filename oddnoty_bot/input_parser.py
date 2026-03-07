import re
from typing import Any

def parse_track_command(text: str) -> dict[str, Any] | None:
    text = text.lower().strip()
    
    intent: dict[str, Any] = {
        "team1": "",
        "team2": "",
        "target_team": None,
        "market_type": None,
        "market_line": None,
        "side": None,
        "market_group": None  # "Over/Under", "Team 1 Total", "Team 2 Total"
    }
    
    # 1. Split teams from the rest of the intent
    if "track " in text:
        parts = re.split(r'\s*:?\s*track\s+', text, 1)
        if len(parts) == 2 and parts[0]:
            teams_part = parts[0]
            rest = parts[1]
        else:
            return None
    else:
        # Fallback: find first occurrence of market keywords
        m_kw = re.search(r'\b(team_?[12]|total|goals|over|under|hdp|handicap|ah|btts|both teams)\b', text)
        if m_kw:
            teams_part = text[:m_kw.start()].strip()
            rest = text[m_kw.start():].strip()
        else:
            return None # Not a tracking command if no keywords found

    teams_part = teams_part.replace(' :', '').strip()
    
    if " vs " in teams_part:
        t1, t2 = teams_part.split(" vs ", 1)
        intent["team1"] = t1.strip()
        intent["team2"] = t2.strip()
    else:
        # Split by space
        words = teams_part.split()
        if len(words) >= 2:
            intent["team1"] = words[0]
            intent["team2"] = words[-1] # Approximate two teams without explicit separator
        elif len(words) == 1:
            intent["team1"] = words[0]
            intent["team2"] = ""
        else:
            return None
            
    if not intent["team1"]:
        return None

    # 2. Extract target_team
    m_team = re.search(r'\bteam_?(1|2)\b', rest)
    if m_team:
        intent["target_team"] = int(m_team.group(1))
        
    # 3. Extract side
    if re.search(r'\bover\b', rest):
        intent["side"] = "Over"
    elif re.search(r'\bunder\b', rest):
        intent["side"] = "Under"
        
    # 4. Extract market_type
    if re.search(r'\b(total|goals|over|under)\b', rest):
        intent["market_type"] = "over_under"
    elif re.search(r'\b(hdp|handicap|ah)\b', rest):
        intent["market_type"] = "asian_handicap"
    elif re.search(r'\b(btts|both teams)\b', rest):
        intent["market_type"] = "btts"
        
    # 5. Extract market_line securely
    rest_clean = re.sub(r'\bteam_?[12]\b', '', rest)
    m_line = re.search(r'\b(\d+\.\d+|\d+)\b', rest_clean)
    if m_line:
        intent["market_line"] = float(m_line.group(1))
    
    # 6. Derive market_group based on target_team
    if intent["market_type"] == "over_under":
        if intent["target_team"] == 1:
            intent["market_group"] = "Team 1 Total"
        elif intent["target_team"] == 2:
            intent["market_group"] = "Team 2 Total"
        else:
            intent["market_group"] = "Over/Under"
    elif intent["market_type"] == "btts":
        intent["market_group"] = "BTTS"
    elif intent["market_type"] == "asian_handicap":
        intent["market_group"] = "Handicap"
        
    return intent
