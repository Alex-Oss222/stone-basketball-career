import sys, json
sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
R = Path('/home/user/stone-basketball-career')
from runtime import league_cards, club_truth
reg = {p['name']: p for p in json.loads((R/'career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json').read_text())['players']}
for name in ['Donyell Marshall', 'Tyrone Hill', 'Dion Glover']:
    p = reg[name]
    for d in ['2003-11-15', '2003-12-21', '2004-04-14']:
        co = league_cards.club_on(p, d, root=R)
        try: ho = club_truth.holder(p.get('bbr_id'), name, d, R)[0]
        except ValueError as e: ho = f'ERR {e}'
        st = league_cards._real_stint_club(p, d, R)
        print(name, d, 'club_on', co['club'], '| holder', ho, '| real stint', st)
