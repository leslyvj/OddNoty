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
        "market_group": None,  # "Over/Under", "Team 1 Total", "Team 2 Total"
        "target_odd": None
    }
    
    # Extract Target Odd (e.g., "Target: 1.80" or "odd 1.8")
    m_target = re.search(r'\b(?:target|odd)\s*:?\s*(\d+\.\d+|\d+)\b', text)
    if m_target:
        intent["target_odd"] = float(m_target.group(1))
        # Remove target part from rest to avoid confusion with market line
        text = text[:m_target.start()] + text[m_target.end():]
    
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
        elif " vs " in text:
            teams_part = text
            rest = ""
        else:
            return None # Not a tracking or research command if no match

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
    team_ptrn = r'\b(?:team|side)\s*[_\-\s]?(1|2)\b'
    m_team = re.search(team_ptrn, rest)
    if m_team:
        intent["target_team"] = int(m_team.group(1))
    elif re.search(r'\b(home|host|hometeam|team_?1)\b', rest):
        intent["target_team"] = 1
    elif re.search(r'\b(away|guest|visitor|awayteam|team_?2)\b', rest):
        intent["target_team"] = 2
        
    # 3. Extract side
    if re.search(r'\bover\b', rest):
        intent["side"] = "Over"
    elif re.search(r'\bunder\b', rest):
        intent["side"] = "Under"
        
    # 4. Extract market_type
    found_market = False
    if re.search(r'\b(total|goals|over|under)\b', rest):
        intent["market_type"] = "over_under"
        found_market = True
    elif re.search(r'\b(hdp|handicap|ah)\b', rest):
        intent["market_type"] = "asian_handicap"
        found_market = True
    elif re.search(r'\b(btts|both teams)\b', rest):
        intent["market_type"] = "btts"
        found_market = True
        
    # 5. Extract market_line securely
    # Remove team designations so numbers like "1" in "Team 1" aren't caught as lines
    rest_clean = re.sub(team_ptrn, '', rest)
    rest_clean = re.sub(r'\b(home|host|hometeam|away|guest|visitor|awayteam|team_?[12])\b', '', rest_clean)
    
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

    # 7. LLM Fallback flag
    if not found_market:
        intent["market_unknown"] = True
        intent["raw_market_query"] = rest
    else:
        intent["market_unknown"] = False
        
    return intent
