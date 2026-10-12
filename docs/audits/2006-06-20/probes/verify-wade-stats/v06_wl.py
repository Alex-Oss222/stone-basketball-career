import sys, json; sys.path.insert(0, '.')
from wade_games import wade_rows
for note, f, res, row in wade_rows('2003-04', '05_Preseason'):
    side = 'home' if res['home'] == f['player_team'] else 'away'
    other = 'away' if side == 'home' else 'home'
    sc = res['final_score']
    lab = f"{'W' if sc[side] > sc[other] else 'L'} {sc[side]}-{sc[other]}"
    print(note.name, f['player_team'], side, f['venue'], f['result'], 'computed', lab, 'match', lab == f['result'], 'wade row', bool(row))
