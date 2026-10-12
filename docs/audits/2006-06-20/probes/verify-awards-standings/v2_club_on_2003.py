import sys, json
sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
from collections import defaultdict, Counter
R = Path('/home/user/stone-basketball-career')
from runtime import write_back, league_cards, club_truth
from runtime.player_stats import alias
rows = write_back.closed_results(R, season='2003-04', now='2004-06-30')
print('closed regular results', len(rows))
games = defaultdict(list)   # name -> [(date, club)]
for row in rows:
    r = row['result']
    for side in ('home', 'away'):
        for p in r['player_stats'][side]:
            if p.get('minutes', 0) > 0:
                games[alias(p['player_id'])].append((r['game_date'], r[side]))
reg = json.loads((R/'career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json').read_text())['players']
print('registry', len(reg))
diff_on = 0; diff_holder = 0; never = []; tot = 0; examples = []
clublines = json.loads((R/'career/Dwyane_Wade/Stats_and_Awards/League/2003-04/card_lines.json').read_text())['players']
codes = {}
for pl in reg:
    g = games.get(alias(pl['name']))
    if not g: continue
    tot += 1
    last_date, last_club = g[-1]
    co = league_cards.club_on(pl, last_date, root=R)
    try:
        ho = club_truth.holder(pl.get('bbr_id'), pl['name'], last_date, R)
    except ValueError:
        ho = ('ERR', '')
    if co['club'] != last_club:
        diff_on += 1
        if len(examples) < 12: examples.append((pl['name'], last_date, last_club, co['club'], co['basis'], ho[0]))
    if ho[0] != last_club: diff_holder += 1
    if co['code']: codes[co['club']] = co['code']
    played = Counter(c for _, c in g)
    line = clublines.get(pl.get('bbr_id') or pl.get('registry_id'), {}).get('regular')
    if line and co['club'] not in played:
        never.append((pl['name'], line[1], dict(played)))
print('players with 2003-04 games', tot)
print('club_on(last game date) != last game club:', diff_on)
print('holder(last game date) != last game club:', diff_holder)
for e in examples: print(' ', e)
print('card_lines regular row label club (club_on at last game) never played for:', len(never))
# direct check of card_lines label vs clubs played
lab_never = []
code2club = {}
for pl in reg:
    g = games.get(alias(pl['name']))
    if not g: continue
    line = clublines.get(pl.get('bbr_id') or pl.get('registry_id'), {}).get('regular')
    if not line: continue
    lab_never.append((pl['name'], line[1], Counter(c for _, c in g)))
print('card_lines regular rows', len(lab_never))
import pickle; pickle.dump(lab_never, open('lab.pkl','wb'))
m = [x for x in lab_never if x[0]=='Donyell Marshall']; print(m)
