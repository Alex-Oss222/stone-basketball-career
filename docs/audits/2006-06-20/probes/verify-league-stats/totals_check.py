"""Independent check of League/<season>/season_totals.json against the closed regular-season results.
Reads Miami Game_N.result.json files (regular season, game_type regular) and the league slate results directly."""
import json, sys, glob
from collections import defaultdict
ROOT = '/home/user/stone-basketball-career'
SEASON = sys.argv[1]
END = {'2003-04': '2004-04-14', '2004-05': '2005-04-20', '2005-06': '2006-04-19'}[SEASON]
files = glob.glob(f'{ROOT}/career/Dwyane_Wade/{SEASON}/**/Game_*.result.json', recursive=True)
files += glob.glob(f'{ROOT}/career/Dwyane_Wade/Stats_and_Awards/League/{SEASON}/Games/*.result.json')
seen = {}
rows = []
for f in files:
    r = json.load(open(f))
    if r.get('game_type') != 'regular' or not r.get('terminated') or r['game_date'] > END:
        continue
    if r['event_id'] in seen:
        print('DUP', r['event_id'], f, seen[r['event_id']]); continue
    seen[r['event_id']] = f
    rows.append(r)
print('games', len(rows))
COUNTS = ['fgm','fga','tpm','tpa','ftm','fta','orb','drb','ast','stl','blk','tov','pf','pts']
indep = defaultdict(lambda: defaultdict(float))
gen = defaultdict(lambda: defaultdict(float))
for r in rows:
    for side in ('home','away'):
        for p in r['player_stats'][side]:
            pid = p['player_id']
            app = p.get('appeared', (p.get('seconds') or 0) > 0 or any(p.get(k) for k in COUNTS))
            if app:
                t = indep[pid]; t['games'] += 1
                for k in COUNTS: t[k] += p.get(k) or 0
            if p.get('minutes', 0) > 0:
                t = gen[pid]; t['games'] += 1
                for k in COUNTS: t[k] += p.get(k) or 0
tot_path = f'{ROOT}/career/Dwyane_Wade/Stats_and_Awards/League/{SEASON}/season_totals.json'
try:
    stored = json.load(open(tot_path))['records']
except FileNotFoundError:
    stored = None
diff_gen = [(n, indep[n]['games'], gen[n]['games']) for n in indep if indep[n]['games'] != gen.get(n, {}).get('games', 0)]
print('rule difference (appearance vs minutes>0):', len(diff_gen))
for d in sorted(diff_gen): print('  ', d, 'pts', indep[d[0]]['pts'], gen[d[0]]['pts'] if d[0] in gen else 0)
if stored is not None:
    by_name = {}
    for rec in stored:
        by_name.setdefault(rec['player_name'], []).append(rec)
    print('stored records', len(stored), 'indep players', len(indep))
    mism = []
    for n, t in indep.items():
        recs = by_name.get(n)
        if not recs:
            mism.append((n, 'MISSING', int(t['games']), int(t['pts']))); continue
        s = recs[0]['totals']
        if int(s['games']) != int(t['games']) or int(s.get('points', s.get('pts', -1))) != int(t['pts']):
            mism.append((n, recs[0]['bbr_id'], 'stored G', s['games'], 'indep G', int(t['games']), 'stored PTS', s.get('points', s.get('pts')), 'indep PTS', int(t['pts'])))
    print('mismatches vs stored:', len(mism))
    for m in sorted(mism, key=str): print('  ', m)
    extra = [n for n in by_name if n not in indep]
    print('stored names not in results', extra[:20])
