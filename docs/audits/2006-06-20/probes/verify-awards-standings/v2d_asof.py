import sys, json
sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
R = Path('/home/user/stone-basketball-career')
from runtime import league_cards, club_truth
from runtime.seasons import live_season_on
print('live_season_on 2004-10-01 =', live_season_on('2004-10-01', R))
reg = {p['name']: p for p in json.loads((R/'career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json').read_text())['players']}
for name in ['Dion Glover', 'Tyrone Hill', 'Donyell Marshall', 'Smush Parker', 'Chris Jefferies', 'Mikki Moore', 'Maciej Lampe']:
    p = reg[name]
    co = league_cards.club_on(p, '2004-10-01', root=R)
    try: ho = club_truth.holder(p.get('bbr_id'), name, '2004-10-01', R)
    except Exception as e: ho = ('ERR', str(e))
    co2 = league_cards.club_on(p, '2004-04-14', root=R)
    print(name, '| club_on 2004-10-01:', co['club'], '-', co['basis'], '| holder 2004-10-01:', ho[0], '| club_on 2004-04-14:', co2['club'], '-', co2['basis'])
