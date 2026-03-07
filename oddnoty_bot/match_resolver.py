from rapidfuzz import fuzz

def find_match(team1: str, team2: str, live_matches: list) -> dict | None:
    best_match = None
    best_score = 0
    search_str = f"{team1} {team2}".lower()
    
    for match in live_matches:
        match_str = f"{match['home_team']} {match['away_team']}".lower()
        score = fuzz.token_set_ratio(search_str, match_str)
        if score > best_score:
            best_score = score
            best_match = match
            
    if best_score < 65 or not best_match:
        return None
        
    return {
        "match_id": best_match["match_id"],
        "home_team": best_match["home_team"],
        "away_team": best_match["away_team"],
        "score": best_score
    }
