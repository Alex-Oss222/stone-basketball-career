"""Why season_totals.json drops appearances: show the raw rows of the dropped games."""
import sys, json
sys.path.insert(0, '.'); sys.path.insert(0, '/home/user/stone-basketball-career')
import indep
from pathlib import Path
from runtime.season_awards import identities
season = sys.argv[1]; who = sys.argv[2:]
rows = indep.results(season)
ids = identities(Path('/home/user/stone-basketball-career'), season)
for r, req, src, path in rows:
    for side in ('home', 'away'):
        for p in r['player_stats'][side]:
            if p['player_id'] in who or any(w in p['player_id'] for w in who):
                app = p.get('appeared', p['seconds'] > 0 or any(p[k] for k in indep.CNT))
                if app and (not p.get('minutes', 0) > 0 or not ids.get(p['player_id'], (None, None, None))[1]):
                    print(r['event_id'], r[side], p['player_id'], 'seconds', p['seconds'], 'minutes', p.get('minutes'), 'pts', p['pts'], 'fga', p['fga'], 'ids->', ids.get(p['player_id']))
