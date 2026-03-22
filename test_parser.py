from oddnoty_bot.input_parser import parse_track_command

# Test cases
cases = [
    "Necaxa vs Pumas : track team_2 total 0.5",
    "Necaxa Pumas team2 total 0.5",
    "necaxa vs pumas track over 1.5",
    "Necaxa vs Pumas : track btts",
    "Necaxa vs Pumas : track team_1 handicap"
]

for c in cases:
    print(f"Parsing: {c}")
    print(parse_track_command(c))
    print("-" * 50)
