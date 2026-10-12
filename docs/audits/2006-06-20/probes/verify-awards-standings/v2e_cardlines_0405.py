import sys, json
sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
from collections import defaultdict, Counter
R = Path('/home/user/stone-basketball-career')
from runtime import write_back, league_cards
from runtime.player_stats import alias
tx = json.loads((R/league_cards.TRANSACTIONS).read_text())
for season, end in (('2003-04', '2004-06-30'), ('2004-05', '2005-06-30')):
    rows = write_back.closed_results(R, season=season, now=end)
    games = defaultdict(Counter)
    for row in rows:
        r = row['result']
        for side in ('home', 'away'):
            for p in r['player_stats'][side]:
                if p.get('minutes', 0) > 0:
                    games[alias(p['player_id'])][r[side]] += 1
    reg = json.loads((R/'career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json').read_text())['players']
    cl = json.loads((R/f'career/Dwyane_Wade/Stats_and_Awards/League/{season}/card_lines.json').read_text())['players']
    never = []; n = 0
    for pl in reg:
        line = cl.get(pl.get('bbr_id') or pl.get('registry_id'), {}).get('regular')
        g = games.get(alias(pl['name']))
        if not line or not g: continue
        n += 1
        codes = {league_cards._code(c, tx, {}) for c in g}
        if line[1] not in codes:
            never.append((pl['name'], line[1], dict(g)))
    print(season, 'rows', n, 'label never played for', len(never))
    for x in never[:25]: print('   ', x)
